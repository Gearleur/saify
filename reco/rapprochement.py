"""Rapprochement PMS ↔ conservateurs à la maille (fonds, ISIN, conservateur). Déterministe, sans LLM."""

import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from reco.sources import (
    Anomalie,
    Lecture,
    Position,
    lire_depositaire_a,
    lire_depositaire_b,
    lire_depositaire_c,
    lire_parametrage,
    lire_pms,
)

LECTEURS = {
    "PMS": ("positions_internes", lire_pms),
    "A": ("depositaire_A", lire_depositaire_a),
    "B": ("depositaire_B", lire_depositaire_b),
    "C": ("depositaire_C", lire_depositaire_c),
}


@dataclass
class Suspens:
    fonds: str
    isin: str
    conservateur: str  # A, B, C, ou « A→B » pour un DEP
    type: str  # QTE, ABS_DEP, ABS_INT, DEP
    qte_pms: Decimal | None
    qte_dep: Decimal | None
    libelle_titre: str
    libelle_type: str
    action: str
    piste: str
    sources: list[str]


@dataclass
class Resultat:
    suspens: list[Suspens] = field(default_factory=list)
    journal: list[Anomalie] = field(default_factory=list)


def _agreger(positions: list[Position]) -> dict[tuple[str, str, str], list[Position]]:
    groupes: dict[tuple[str, str, str], list[Position]] = defaultdict(list)
    for p in positions:
        groupes[(p.entite, p.isin, p.conservateur)].append(p)
    return groupes


def _somme(positions: list[Position]) -> Decimal:
    return sum((p.quantite for p in positions), Decimal(0))


def _libelle(*groupes: list[Position]) -> str:
    return next((p.libelle for g in groupes for p in g if p.libelle), "")


def _piste(db: sqlite3.Connection, fonds: str, isin: str) -> str:
    lignes = db.execute(
        "SELECT sens, quantite, date_denouement FROM mouvements"
        " WHERE portefeuille = ? AND isin = ? AND statut = 'EN_ATTENTE' ORDER BY id",
        (fonds, isin),
    ).fetchall()
    return " ; ".join(
        f"{sens} {qte} EN_ATTENTE (dén. {date[8:10]}/{date[5:7]})" for sens, qte, date in lignes
    )


def rapprocher(fichiers: dict[str, bytes], parametrage: Path, db_path: Path) -> Resultat:
    """`fichiers` : nom de fichier -> contenu brut, une entrée par source (PMS, A, B, C)."""
    param = lire_parametrage(parametrage)
    resultat = Resultat()
    pms: list[Position] = []
    dep: list[Position] = []
    for source, (prefixe, lecteur) in LECTEURS.items():
        nom = next(n for n in fichiers if Path(n).name.startswith(prefixe))
        lecture: Lecture = lecteur(nom, fichiers[nom], param)
        resultat.journal.extend(lecture.journal)
        (pms if source == "PMS" else dep).extend(lecture.positions)

    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    fonds_par_entite = dict(db.execute("SELECT nom, code FROM portefeuilles").fetchall())

    cote_pms, cote_dep = _agreger(pms), _agreger(dep)
    bruts: list[tuple[str, tuple[str, str, str], list[Position], list[Position]]] = []
    for cle in sorted(cote_pms.keys() | cote_dep.keys()):
        g_pms, g_dep = cote_pms.get(cle, []), cote_dep.get(cle, [])
        if not g_dep:
            bruts.append(("ABS_DEP", cle, g_pms, g_dep))
        elif not g_pms:
            bruts.append(("ABS_INT", cle, g_pms, g_dep))
        elif _somme(g_pms) != _somme(g_dep):
            bruts.append(("QTE", cle, g_pms, g_dep))

    # Un ABS_DEP chez X et un ABS_INT chez Y pour le même (fonds, ISIN) forment un seul DEP.
    absents: dict[tuple[str, str], dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for brut in bruts:
        if brut[0] in ("ABS_DEP", "ABS_INT"):
            absents[brut[1][:2]][brut[0]].append(brut)
    for (entite, isin), par_type in absents.items():
        if len(par_type["ABS_DEP"]) == 1 and len(par_type["ABS_INT"]) == 1:
            (_, cle_x, g_pms, _), (_, cle_y, _, g_dep) = (
                par_type["ABS_DEP"][0],
                par_type["ABS_INT"][0],
            )
            bruts = [b for b in bruts if b[1] not in (cle_x, cle_y)]
            bruts.append(("DEP", (entite, isin, f"{cle_x[2]}→{cle_y[2]}"), g_pms, g_dep))

    for type_, (entite, isin, conservateur), g_pms, g_dep in bruts:
        fonds = fonds_par_entite[entite]
        libelle_type, action = param.types_ecarts[type_]
        resultat.suspens.append(
            Suspens(
                fonds=fonds,
                isin=isin,
                conservateur=conservateur,
                type=type_,
                qte_pms=_somme(g_pms) if g_pms else None,
                qte_dep=_somme(g_dep) if g_dep else None,
                libelle_titre=_libelle(g_pms, g_dep),
                libelle_type=libelle_type,
                action=action,
                piste=_piste(db, fonds, isin),
                sources=[p.ref for p in g_pms + g_dep],
            )
        )
    db.close()
    resultat.suspens.sort(key=lambda s: (s.fonds, s.type, s.isin))
    return resultat


def rapprocher_dossier(dossier: Path) -> Resultat:
    fichiers = {
        f.name: f.read_bytes()
        for f in sorted(dossier.iterdir())
        if any(f.name.startswith(prefixe) for prefixe, _ in LECTEURS.values())
    }
    return rapprocher(fichiers, dossier / "parametrage.xlsx", dossier / "orsay.db")
