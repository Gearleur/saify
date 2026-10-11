"""Rapprochement PMS ↔ conservateurs à la maille (fonds, ISIN, conservateur). Déterministe, sans LLM.

L'orchestration seule, en étapes nommées : paramétrage, date d'arrêté, lecture des 4 sources, puis
(si rien ne bloque) informations de orsay.db, contrôles, comparaison, complétion et tri des suspens.
"""

import csv
from datetime import date
from pathlib import Path

from middle_office.domain.formats import date_fr
from middle_office.domain.reconciliation.breaks import PRIORITIES, Result
from middle_office.domain.reconciliation.checks import flag_positions, overdue_settlements
from middle_office.domain.reconciliation.comparison import (
    compare,
    custodians_by_security,
    merge_dep,
)
from middle_office.domain.reconciliation.db_context import complete, read_db_context
from middle_office.domain.reconciliation.sources import (
    FORMAT_ERRORS,
    Anomaly,
    ClientConfig,
    Position,
    anomaly,
    pms_dates,
    read_client_config,
    read_custodian_a,
    read_custodian_b,
    read_custodian_c,
    read_pms,
)

READERS = {
    "PMS": ("positions_internes", read_pms),
    "A": ("depositaire_A", read_custodian_a),
    "B": ("depositaire_B", read_custodian_b),
    "C": ("depositaire_C", read_custodian_c),
}


def source_of_file(name: str) -> str | None:
    """PMS, A, B ou C d'après le début du nom, sans tenir compte de la casse ; None si inconnu.

    Seule règle de reconnaissance des fichiers (dépôt, exemple, CLI) : le front applique la même.
    """
    db_path = Path(name).name.lower()
    return next(
        (src for src, (prefix, _) in READERS.items() if db_path.startswith(prefix.lower())), None
    )


def _refusal(file: str, rule: str, reason: str, raw: str = "") -> Anomaly:
    return anomaly(file, 0, "BLOQUANT", rule, raw, "", reason)


def _error(e: Exception) -> str:
    return f"{type(e).__name__} : {e}"


def _upload_date(
    files: dict[str, bytes], expected_date: date | None
) -> tuple[date | None, Anomaly | None]:
    """Date d'arrêté du PMS (source de référence) : une seule date, et l'attendue si elle est fixée."""
    names = [n for n in files if source_of_file(n) == "PMS"]
    if len(names) != 1:
        return None, None  # FICHIER_MANQUANT ou FICHIERS_MULTIPLES, tracés par la boucle de lecture
    try:
        dates = pms_dates(files[names[0]])
        read_date = date.fromisoformat(dates.pop()) if len(dates) == 1 else None
    except (ValueError, KeyError, csv.Error):
        dates, read_date = set(), None
    if read_date is None:
        multiple = f"plusieurs dates d'arrêté dans le PMS ({', '.join(sorted(dates))})"
        return None, _refusal(
            names[0], "DATE_ARRETE", multiple if dates else "date d'arrêté du PMS illisible"
        )
    if expected_date is not None and read_date != expected_date:
        reason = f"fichiers arrêtés au {date_fr(read_date)}, attendu le {date_fr(expected_date)}"
        return None, _refusal(names[0], "DATE_ARRETE", reason, read_date.isoformat())
    return read_date, None


def _read_source(
    source: str, files: dict[str, bytes], config: ClientConfig, as_of_date: date | None
) -> tuple[list[Position], list[Anomaly]]:
    """Positions et journal d'une source ; un fichier absent, en double ou illisible est refusé, pas deviné."""
    prefix, reader = READERS[source]
    names = [n for n in files if source_of_file(n) == source]
    if not names:
        return [], [_refusal(prefix, "FICHIER_MANQUANT", f"fichier {source} absent")]
    if len(names) > 1:
        reason = f"{len(names)} fichiers {source} : lequel est le bon ?"
        return [], [_refusal(prefix, "FICHIERS_MULTIPLES", reason, ", ".join(names))]
    try:
        reading = reader(names[0], files[names[0]], config, as_of_date)
    except FORMAT_ERRORS as e:
        return [], [_refusal(names[0], "FORMAT_ILLISIBLE", _error(e))]
    # Un lecteur qui a déjà bloqué a dit pourquoi : « 0 position » en plus serait du bruit.
    if not reading.positions and not any(a.level == "BLOQUANT" for a in reading.cleaning_log):
        reading.block("AUCUNE_LIGNE", 0, "", "0 position lue")
    return reading.positions, reading.cleaning_log


def reconcile(
    files: dict[str, bytes],
    client_config: Path,
    db_path: Path | None,
    expected_date: date | None = None,
) -> Result:
    """`fichiers` : nom de fichier -> contenu brut, un fichier par source (PMS, A, B, C).

    Une seule anomalie BLOQUANT suffit à refuser le rapprochement : un rapprochement partiel
    rendrait des faux négatifs invisibles. orsay.db est facultative : elle informe, elle ne décide pas.
    La date d'arrêté est lue dans le PMS ; les conservateurs doivent porter la même. `date_attendue`
    (en production : J-1 ouvré) refuse en plus des fichiers périmés.
    """
    result = Result()
    try:
        config = read_client_config(client_config)
    except (
        *FORMAT_ERRORS,
        OSError,
    ) as e:  # sans paramétrage fiable, aucun fonds n'est identifiable
        result.cleaning_log.append(_refusal(Path(client_config).name, "PARAMETRAGE", _error(e)))
        result.status = "BLOQUE"
        return result

    as_of_date, refusal = _upload_date(files, expected_date)
    result.as_of_date = as_of_date
    result.cleaning_log += [refusal] if refusal else []
    pms, custodian_positions = [], []
    for source in READERS:
        positions, cleaning_log = _read_source(source, files, config, as_of_date)
        result.cleaning_log += cleaning_log
        (pms if source == "PMS" else custodian_positions).extend(positions)
    if any(a.level == "BLOQUANT" for a in result.cleaning_log):
        result.status = "BLOQUE"
        return result
    assert as_of_date is not None  # sans blocage, le PMS était présent, seul, et d'une seule date

    db_info = read_db_context(db_path, result.cleaning_log)
    result.cleaning_log += flag_positions(pms + custodian_positions, db_info) + overdue_settlements(
        db_info, as_of_date
    )
    result.breaks = merge_dep(compare(pms, custodian_positions))
    complete(
        result.breaks,
        config,
        db_info,
        as_of_date,
        custodians_by_security(pms + custodian_positions),
    )
    result.breaks.sort(key=lambda s: (PRIORITIES.index(s.priority), s.entity, s.type, s.isin))
    return result


def reconcile_folder(folder: Path) -> Result:
    files = {
        f.name: f.read_bytes()
        for f in sorted(folder.iterdir())
        if f.is_file() and source_of_file(f.name)
    }
    return reconcile(files, folder / "parametrage.xlsx", folder / "orsay.db")
