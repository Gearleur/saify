"""Origine d'un suspens : le pont avec le besoin 1 (suspens du dernier rapprochement exploitable,
ses lignes sources et les mouvements du titre).
"""

from datetime import date
from decimal import Decimal
from pathlib import Path

from middle_office.domain.formats import date_fr, format_quantity
from middle_office.domain.management_db import decimal, read_only_connection
from middle_office.domain.questions.models import (
    Answer,
    Figure,
    ReconciliationContext,
    SourceRow,
)

SQL_SECURITY_MOVEMENTS = """
SELECT id, portefeuille, date_operation, date_denouement, sens, quantite, statut
FROM mouvements
WHERE isin = :isin
ORDER BY id
""".strip()
MOVEMENT_COLUMNS = (
    "id",
    "portefeuille",
    "date_operation",
    "date_denouement",
    "sens",
    "quantite",
    "statut",
)


def _no_reconciliation(context: ReconciliationContext | None) -> str:
    if context is not None and context.newer_blocked:
        return (
            f"Le dernier rapprochement ({context.newer_blocked}) est bloqué et aucun "
            "rapprochement exploitable n'existe : corrigez les fichiers, puis relancez."
        )
    return "Aucun rapprochement disponible : lancez d'abord le rapprochement du jour."


def _qty(value: str | None) -> str:
    return "absent" if value is None else format_quantity(Decimal(value))


def _sentence(s: dict, reference: str) -> str:
    sentence = (
        f"Suspens {s['type']} ({s['break_type_label']}) sur {s['security_name']} ({s['fund'] or s['entity']}, "
        f"conservateur {s['custodian']}) dans {reference} : PMS {_qty(s['pms_qty'])}, "
        f"conservateur {_qty(s['custodian_qty'])}, écart {_qty(s['difference'])}. Action attendue : {s['action']}."
    )
    return sentence + (f" Piste : {s['lead']}." if s["lead"] else "")


def _movement_source(line: tuple) -> SourceRow:
    values = dict(zip(MOVEMENT_COLUMNS, line, strict=True))
    values["quantite"] = decimal(values["quantite"])
    return SourceRow("mouvements", {key: str(v) for key, v in values.items()})


def break_origin(db_path: Path, isin: str, context: ReconciliationContext | None) -> Answer:
    """Pont avec le besoin 1 : le suspens du dernier rapprochement exploitable, ses lignes sources
    et les mouvements du titre. Un rapprochement plus récent mais bloqué est toujours signalé."""
    params: dict[str, str | None] = {"isin": isin}
    if context is None or context.id is None:
        reason = _no_reconciliation(context)
        return Answer(reason, [], SQL_SECURITY_MOVEMENTS, params, [], confidence="basse")

    day = date_fr(date.fromisoformat(context.as_of_date)) if context.as_of_date else "date inconnue"
    reference = f"le rapprochement {context.id} (arrêté du {day})"
    warnings = []
    if context.newer_blocked:
        warnings.append(
            f"Le rapprochement le plus récent ({context.newer_blocked}) est bloqué : cette réponse "
            f"vient de {reference}, le dernier exploitable. Elle peut ne plus être à jour."
        )
    confidence = "basse" if context.newer_blocked else "haute"
    found = [s for s in context.breaks if s["isin"] == isin]
    if not found:
        sentence = f"Aucun suspens sur {isin} dans {reference}."
        return Answer(
            sentence,
            [],
            SQL_SECURITY_MOVEMENTS,
            params,
            [],
            confidence=confidence,
            warnings=warnings,
        )

    fund = {s["fund"] for s in found}
    with read_only_connection(db_path) as db:
        movements = [m for m in db.execute(SQL_SECURITY_MOVEMENTS, params) if m[1] in fund]
    sources = [
        SourceRow(ref, {"isin": isin, "suspens": s["id"]}) for s in found for ref in s["sources"]
    ]
    sources += [_movement_source(m) for m in movements]
    figures = [
        Figure(
            f"Écart {s['type']} ({s['custodian']})", Decimal(s["difference"]), "titres ou nominal"
        )
        for s in found
    ]
    warnings += [g["message"] for s in found for g in s["flags"]]
    sentences = " ".join(_sentence(s, reference) for s in found)
    return Answer(sentences, figures, SQL_SECURITY_MOVEMENTS, params, sources, confidence, warnings)
