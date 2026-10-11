"""Rapprochement PMS ↔ conservateurs à la maille (fonds, ISIN, conservateur). Déterministe, sans LLM.

L'orchestration seule, en étapes nommées : paramétrage, date d'arrêté, lecture des 4 sources, puis
(si rien ne bloque) informations de orsay.db, contrôles, comparaison, complétion et tri des suspens.
"""

import csv
from datetime import date
from pathlib import Path

from middle_office.domaine.formats import date_fr
from middle_office.domaine.rapprochement.comparaison import (
    comparer,
    conservateurs_par_titre,
    fusionner_dep,
)
from middle_office.domaine.rapprochement.controles import denouements_depasses, signaler_positions
from middle_office.domaine.rapprochement.informations import completer, lire_base
from middle_office.domaine.rapprochement.sources import (
    ERREURS_DE_FORMAT,
    Anomalie,
    Parametrage,
    Position,
    anomalie,
    dates_pms,
    lire_depositaire_a,
    lire_depositaire_b,
    lire_depositaire_c,
    lire_parametrage,
    lire_pms,
)
from middle_office.domaine.rapprochement.suspens import PRIORITES, Resultat

LECTEURS = {
    "PMS": ("positions_internes", lire_pms),
    "A": ("depositaire_A", lire_depositaire_a),
    "B": ("depositaire_B", lire_depositaire_b),
    "C": ("depositaire_C", lire_depositaire_c),
}


def source_du_fichier(nom: str) -> str | None:
    """PMS, A, B ou C d'après le début du nom, sans tenir compte de la casse ; None si inconnu.

    Seule règle de reconnaissance des fichiers (dépôt, exemple, CLI) : le front applique la même.
    """
    base = Path(nom).name.lower()
    return next(
        (src for src, (prefixe, _) in LECTEURS.items() if base.startswith(prefixe.lower())), None
    )


def _refus(fichier: str, regle: str, motif: str, brut: str = "") -> Anomalie:
    return anomalie(fichier, 0, "BLOQUANT", regle, brut, "", motif)


def _erreur(e: Exception) -> str:
    return f"{type(e).__name__} : {e}"


def _date_du_depot(
    fichiers: dict[str, bytes], date_attendue: date | None
) -> tuple[date | None, Anomalie | None]:
    """Date d'arrêté du PMS (source de référence) : une seule date, et l'attendue si elle est fixée."""
    noms = [n for n in fichiers if source_du_fichier(n) == "PMS"]
    if len(noms) != 1:
        return None, None  # FICHIER_MANQUANT ou FICHIERS_MULTIPLES, tracés par la boucle de lecture
    try:
        dates = dates_pms(fichiers[noms[0]])
        lue = date.fromisoformat(dates.pop()) if len(dates) == 1 else None
    except (ValueError, KeyError, csv.Error):
        dates, lue = set(), None
    if lue is None:
        multiples = f"plusieurs dates d'arrêté dans le PMS ({', '.join(sorted(dates))})"
        return None, _refus(
            noms[0], "DATE_ARRETE", multiples if dates else "date d'arrêté du PMS illisible"
        )
    if date_attendue is not None and lue != date_attendue:
        motif = f"fichiers arrêtés au {date_fr(lue)}, attendu le {date_fr(date_attendue)}"
        return None, _refus(noms[0], "DATE_ARRETE", motif, lue.isoformat())
    return lue, None


def _lire_source(
    source: str, fichiers: dict[str, bytes], param: Parametrage, date_arrete: date | None
) -> tuple[list[Position], list[Anomalie]]:
    """Positions et journal d'une source ; un fichier absent, en double ou illisible est refusé, pas deviné."""
    prefixe, lecteur = LECTEURS[source]
    noms = [n for n in fichiers if source_du_fichier(n) == source]
    if not noms:
        return [], [_refus(prefixe, "FICHIER_MANQUANT", f"fichier {source} absent")]
    if len(noms) > 1:
        motif = f"{len(noms)} fichiers {source} : lequel est le bon ?"
        return [], [_refus(prefixe, "FICHIERS_MULTIPLES", motif, ", ".join(noms))]
    try:
        lecture = lecteur(noms[0], fichiers[noms[0]], param, date_arrete)
    except ERREURS_DE_FORMAT as e:
        return [], [_refus(noms[0], "FORMAT_ILLISIBLE", _erreur(e))]
    # Un lecteur qui a déjà bloqué a dit pourquoi : « 0 position » en plus serait du bruit.
    if not lecture.positions and not any(a.niveau == "BLOQUANT" for a in lecture.journal):
        lecture.bloquer("AUCUNE_LIGNE", 0, "", "0 position lue")
    return lecture.positions, lecture.journal


def rapprocher(
    fichiers: dict[str, bytes],
    parametrage: Path,
    db_path: Path | None,
    date_attendue: date | None = None,
) -> Resultat:
    """`fichiers` : nom de fichier -> contenu brut, un fichier par source (PMS, A, B, C).

    Une seule anomalie BLOQUANT suffit à refuser le rapprochement : un rapprochement partiel
    rendrait des faux négatifs invisibles. orsay.db est facultative : elle informe, elle ne décide pas.
    La date d'arrêté est lue dans le PMS ; les conservateurs doivent porter la même. `date_attendue`
    (en production : J-1 ouvré) refuse en plus des fichiers périmés.
    """
    resultat = Resultat()
    try:
        param = lire_parametrage(parametrage)
    except (
        *ERREURS_DE_FORMAT,
        OSError,
    ) as e:  # sans paramétrage fiable, aucun fonds n'est identifiable
        resultat.journal.append(_refus(Path(parametrage).name, "PARAMETRAGE", _erreur(e)))
        resultat.statut = "BLOQUE"
        return resultat

    date_arrete, refus = _date_du_depot(fichiers, date_attendue)
    resultat.date_arrete = date_arrete
    resultat.journal += [refus] if refus else []
    pms, dep = [], []
    for source in LECTEURS:
        positions, journal = _lire_source(source, fichiers, param, date_arrete)
        resultat.journal += journal
        (pms if source == "PMS" else dep).extend(positions)
    if any(a.niveau == "BLOQUANT" for a in resultat.journal):
        resultat.statut = "BLOQUE"
        return resultat
    assert date_arrete is not None  # sans blocage, le PMS était présent, seul, et d'une seule date

    base = lire_base(db_path, resultat.journal)
    resultat.journal += signaler_positions(pms + dep, base) + denouements_depasses(
        base, date_arrete
    )
    resultat.suspens = fusionner_dep(comparer(pms, dep))
    completer(resultat.suspens, param, base, date_arrete, conservateurs_par_titre(pms + dep))
    resultat.suspens.sort(key=lambda s: (PRIORITES.index(s.priorite), s.entite, s.type, s.isin))
    return resultat


def rapprocher_dossier(dossier: Path) -> Resultat:
    fichiers = {
        f.name: f.read_bytes()
        for f in sorted(dossier.iterdir())
        if f.is_file() and source_du_fichier(f.name)
    }
    return rapprocher(fichiers, dossier / "parametrage.xlsx", dossier / "orsay.db")
