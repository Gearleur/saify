"""Rapprochement PMS ↔ conservateurs à la maille (fonds, ISIN, conservateur). Déterministe, sans LLM."""

import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

from reco.sources import (
    Anomalie,
    Lecture,
    Position,
    isin_valide,
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
DATE_ARRETE = date(2026, 9, 25)


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
    statut: str = "OK"  # OK, ou BLOQUE si une anomalie BLOQUANT empêche le rapprochement
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
    pistes = [f"{sens} {qte} EN_ATTENTE (dén. {d[8:10]}/{d[5:7]})" for sens, qte, d in lignes]
    if not isin_valide(isin):
        pistes.append("ISIN à clé invalide, probable erreur de saisie")
    return " ; ".join(pistes)


def _signaler(positions: list[Position], referentiel: dict[str, str]) -> list[Anomalie]:
    """ISIN douteux et libellés divergents : conservés, mais remontés à un humain."""
    anomalies = []
    vus: set[str] = set()
    for p in positions:
        if p.isin in vus:
            continue
        vus.add(p.isin)
        if not isin_valide(p.isin):
            anomalies.append(Anomalie(p.fichier, p.ligne, "SIGNALE", "ISIN_CLE_INVALIDE", p.isin, p.isin,
                                      "clé de contrôle ISIN invalide : probable erreur de saisie"))  # fmt: skip
        if p.isin not in referentiel:
            anomalies.append(Anomalie(p.fichier, p.ligne, "SIGNALE", "ISIN_HORS_REFERENTIEL", p.isin, p.isin,
                                      "ISIN absent du référentiel titres"))  # fmt: skip
    libelles: dict[str, dict[str, Position]] = defaultdict(dict)
    for p in positions:
        if p.libelle:
            libelles[p.isin].setdefault("PMS" if p.source == "PMS" else "DEP", p)
    for isin, par_cote in libelles.items():
        if (
            len(par_cote) == 2
            and par_cote["PMS"].libelle.upper() != par_cote["DEP"].libelle.upper()
        ):
            p, d = par_cote["PMS"], par_cote["DEP"]
            anomalies.append(Anomalie(d.fichier, d.ligne, "SIGNALE", "LIBELLE_DIFFERENT", d.libelle, p.libelle,
                                      f"{isin} : libellé PMS « {p.libelle} » ≠ conservateur « {d.libelle} »"))  # fmt: skip
    return anomalies


def rapprocher(
    fichiers: dict[str, bytes], parametrage: Path, db_path: Path, date_arrete: date = DATE_ARRETE
) -> Resultat:
    """`fichiers` : nom de fichier -> contenu brut, une entrée par source (PMS, A, B, C).

    Une seule anomalie BLOQUANT suffit à refuser le rapprochement : un rapprochement partiel
    rendrait des faux négatifs invisibles.
    """
    param = lire_parametrage(parametrage)
    resultat = Resultat()
    pms: list[Position] = []
    dep: list[Position] = []
    for source, (prefixe, lecteur) in LECTEURS.items():
        nom = next((n for n in fichiers if Path(n).name.startswith(prefixe)), None)
        if nom is None:
            resultat.journal.append(
                Anomalie(
                    prefixe, 0, "BLOQUANT", "FICHIER_MANQUANT", "", "", f"fichier {source} absent"
                )
            )
            continue
        try:
            lecture: Lecture = lecteur(nom, fichiers[nom], param, date_arrete)
        except Exception as erreur:  # fichier corrompu ou format inattendu : refusé, pas deviné
            resultat.journal.append(
                Anomalie(
                    nom,
                    0,
                    "BLOQUANT",
                    "FORMAT_ILLISIBLE",
                    "",
                    "",
                    f"{type(erreur).__name__} : {erreur}",
                )
            )
            continue
        if not lecture.positions:
            lecture.noter("BLOQUANT", "AUCUNE_LIGNE", 0, "", "", "0 position lue")
        resultat.journal.extend(lecture.journal)
        (pms if source == "PMS" else dep).extend(lecture.positions)

    if any(a.niveau == "BLOQUANT" for a in resultat.journal):
        resultat.statut = "BLOQUE"
        return resultat

    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    fonds_par_entite = dict(db.execute("SELECT nom, code FROM portefeuilles").fetchall())
    referentiel = dict(db.execute("SELECT isin, libelle FROM titres").fetchall())
    resultat.journal.extend(_signaler(pms + dep, referentiel))

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
                libelle_titre=_libelle(g_pms, g_dep) or referentiel.get(isin, ""),
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
