"""Rapprochement PMS ↔ conservateurs à la maille (fonds, ISIN, conservateur). Déterministe, sans LLM.

Quatre temps : comparer les quantités agrégées, fusionner les DEP, compléter chaque suspens
(action du paramétrage, piste orsay.db, signalements), trier.
"""

import csv
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import NamedTuple

from middle_office.domaine.base_gestion import connexion_lecture_seule
from middle_office.domaine.formats import date_fr, formater_quantite
from middle_office.domaine.rapprochement.sources import (
    ERREURS_DE_FORMAT,
    Anomalie,
    Lecture,
    Parametrage,
    Position,
    anomalie,
    dates_pms,
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


def source_du_fichier(nom: str) -> str | None:
    """PMS, A, B ou C d'après le début du nom, sans tenir compte de la casse ; None si inconnu.

    Seule règle de reconnaissance des fichiers (dépôt, exemple, CLI) : le front applique la même.
    """
    base = Path(nom).name.lower()
    return next(
        (src for src, (prefixe, _) in LECTEURS.items() if base.startswith(prefixe.lower())), None
    )


PRIORITES = ("critique", "a_relever", "en_attente")  # ordre de traitement
TYPES_EXPLICABLES = ("QTE", "ABS_DEP", "ABS_INT")  # par une opération en attente de dénouement
EXPLICATIONS = ("aucune", "totale", "partielle", "contraire")  # par les opérations en attente
ALERTES = ("CSDR", "DEP_AMBIGU", "ISIN_INVALIDE", "PISTE_MULTI_CONSERVATEURS")


class Signalement(NamedTuple):
    code: str  # ALERTES : c'est lui que lisent la priorité et l'interface
    message: str  # pour l'opérateur


@dataclass
class Suspens:
    entite: str  # clé fonds : nom d'entité du paramétrage (la référence)
    isin: str
    conservateur: str  # A, B, C, ou « A→B » pour un DEP
    type: str  # QTE, ABS_DEP, ABS_INT, DEP
    qte_pms: Decimal | None
    qte_dep: Decimal | None
    libelle_titre: str
    sources: list[str]
    fonds: str = ""  # code court (PAT, OBL, ACT) lu dans orsay.db, vide si la base manque
    libelle_type: str = ""
    action: str = ""
    piste: str = ""
    signalements: list[Signalement] = field(default_factory=list)
    # Ce qui décide de la priorité : des codes stables, jamais les libellés (faits pour les humains).
    explication: str = "aucune"  # EXPLICATIONS

    @property
    def alertes(self) -> set[str]:
        return {s.code for s in self.signalements}

    def signaler(self, code: str, message: str) -> None:
        assert code in ALERTES, code
        self.signalements.append(Signalement(code, message))

    @property
    def ecart(self) -> Decimal:
        """PMS − conservateur : positif si le PMS en a plus (achat non dénoué, par exemple)."""
        return (self.qte_pms or Decimal(0)) - (self.qte_dep or Decimal(0))

    @property
    def priorite(self) -> str:
        return priorite(self)


def priorite(s: Suspens) -> str:
    """critique : risque CSDR ; en_attente : écart entièrement expliqué par des opérations en attente,
    sans alerte ; sinon a_relever. Un achat de ligne nouvelle non dénoué donne un ABS_DEP expliqué,
    une vente totale un ABS_INT : même traitement qu'un QTE. Un DEP (mauvais conservateur) n'est
    jamais expliqué par une opération."""
    if "CSDR" in s.alertes:
        return "critique"
    if s.type in TYPES_EXPLICABLES and s.explication == "totale" and not s.alertes:
        return "en_attente"
    return "a_relever"


@dataclass
class Resultat:
    statut: str = "OK"  # OK, ou BLOQUE si une anomalie BLOQUANT empêche le rapprochement
    date_arrete: date | None = None  # lue dans le PMS ; None si absente ou ambiguë
    suspens: list[Suspens] = field(default_factory=list)
    journal: list[Anomalie] = field(default_factory=list)


class Mouvement(NamedTuple):
    id: int
    date_denouement: date
    portefeuille: str
    isin: str
    sens: str
    quantite: Decimal

    @property
    def signe(self) -> Decimal:
        """Effet sur PMS − conservateur tant que l'opération n'est pas dénouée."""
        return self.quantite if self.sens == "ACHAT" else -self.quantite


@dataclass
class Base:
    """Ce qu'on lit dans orsay.db, à titre d'information uniquement."""

    codes_fonds: dict[str, str] = field(default_factory=dict)
    referentiel: dict[str, str] | None = None  # None : référentiel indisponible
    en_attente: list[Mouvement] = field(default_factory=list)


def _lire_base(db_path: Path | None, journal: list[Anomalie]) -> Base:
    try:
        if db_path is None:
            raise sqlite3.OperationalError("aucune base fournie")
        with connexion_lecture_seule(db_path) as db:
            return Base(
                codes_fonds=dict(db.execute("SELECT nom, code FROM portefeuilles")),
                referentiel=dict(db.execute("SELECT isin, libelle FROM titres")),
                en_attente=[
                    Mouvement(i, date.fromisoformat(d), pf, isin, sens, Decimal(q))
                    for i, d, pf, isin, sens, q in db.execute(
                        "SELECT id, date_denouement, portefeuille, isin, sens, quantite"
                        " FROM mouvements WHERE statut = 'EN_ATTENTE' ORDER BY id"
                    )
                ],
            )
    except sqlite3.Error as erreur:
        journal.append(
            Anomalie(
                "orsay.db",
                0,
                "SIGNALE",
                "BASE_INDISPONIBLE",
                str(db_path),
                "",
                f"orsay.db illisible ({erreur}) : suspens sans code fonds ni piste",
            )
        )
        return Base()


def _signaler(positions: list[Position], base: Base) -> list[Anomalie]:
    """ISIN douteux et libellés divergents : conservés, mais remontés à un humain."""
    anomalies = []
    vus: set[str] = set()
    for p in positions:
        if p.isin in vus:
            continue
        vus.add(p.isin)
        if not isin_valide(p.isin):
            anomalies.append(
                Anomalie(
                    p.fichier,
                    p.ligne,
                    "SIGNALE",
                    "ISIN_CLE_INVALIDE",
                    p.isin,
                    p.isin,
                    "clé de contrôle ISIN invalide : probable erreur de saisie",
                )
            )
        if base.referentiel is not None and p.isin not in base.referentiel:
            anomalies.append(
                Anomalie(
                    p.fichier,
                    p.ligne,
                    "SIGNALE",
                    "ISIN_HORS_REFERENTIEL",
                    p.isin,
                    p.isin,
                    "ISIN absent du référentiel titres",
                )
            )
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
            anomalies.append(
                Anomalie(
                    d.fichier,
                    d.ligne,
                    "SIGNALE",
                    "LIBELLE_DIFFERENT",
                    d.libelle,
                    p.libelle,
                    f"{isin} : libellé PMS « {p.libelle} » ≠ conservateur « {d.libelle} »",
                )
            )
    return anomalies


def _agreger(positions: list[Position]) -> dict[tuple[str, str, str], list[Position]]:
    groupes: dict[tuple[str, str, str], list[Position]] = defaultdict(list)
    for p in positions:
        groupes[(p.entite, p.isin, p.conservateur)].append(p)
    return groupes


def _comparer(pms: list[Position], dep: list[Position]) -> list[Suspens]:
    """Jointure complète : une clé présente d'un seul côté est un suspens (sinon LVMH serait raté)."""
    cote_pms, cote_dep = _agreger(pms), _agreger(dep)
    suspens = []
    for cle in sorted(cote_pms.keys() | cote_dep.keys()):
        g_pms, g_dep = cote_pms.get(cle, []), cote_dep.get(cle, [])
        # Une position nulle est une absence : pas de suspens « ABS_DEP » pour 0 titre.
        q_pms = sum((p.quantite for p in g_pms), Decimal(0)) or None
        q_dep = sum((p.quantite for p in g_dep), Decimal(0)) or None
        if q_pms == q_dep:  # tolérance nulle : une seule unité d'écart est un suspens
            continue
        type_ = "ABS_DEP" if q_dep is None else "ABS_INT" if q_pms is None else "QTE"
        entite, isin, conservateur = cle
        libelle = next((p.libelle for p in g_pms + g_dep if p.libelle), "")
        sources = [p.ref for p in g_pms + g_dep]
        suspens.append(Suspens(entite, isin, conservateur, type_, q_pms, q_dep, libelle, sources))
    return suspens


def _fusionner_dep(suspens: list[Suspens]) -> list[Suspens]:
    """Attendu chez X, livré chez Y : un seul suspens DEP (énoncé), même si les quantités diffèrent.

    Plusieurs candidats (2 conservateurs possibles) : on ne devine pas, on signale sur chaque suspens.
    """
    par_titre: dict[tuple[str, str], list[Suspens]] = defaultdict(list)
    for s in suspens:
        if s.type in ("ABS_DEP", "ABS_INT"):
            par_titre[(s.entite, s.isin)].append(s)
    for groupe in par_titre.values():
        absents = [s for s in groupe if s.type == "ABS_DEP"]
        trouves = [s for s in groupe if s.type == "ABS_INT"]
        if not absents or not trouves:
            continue
        if len(absents) == 1 and len(trouves) == 1:
            x, y = absents[0], trouves[0]
            suspens = [s for s in suspens if s is not x and s is not y]
            suspens.append(
                Suspens(
                    x.entite,
                    x.isin,
                    f"{x.conservateur}→{y.conservateur}",
                    "DEP",
                    x.qte_pms,
                    y.qte_dep,
                    x.libelle_titre or y.libelle_titre,
                    x.sources + y.sources,
                )
            )
        else:
            message = (
                f"DEP ambigu : absent chez {', '.join(s.conservateur for s in absents)}, "
                f"trouvé chez {', '.join(s.conservateur for s in trouves)} : à trancher par l'opérateur"
            )
            for s in groupe:
                s.signaler("DEP_AMBIGU", message)
    return suspens


def _piste(
    mouvements: list[Mouvement], ecart: Decimal, plusieurs_conservateurs: bool
) -> tuple[str, str]:
    """Cite les opérations en attente et dit, calcul signé à l'appui, si elles expliquent l'écart.

    Renvoie (libellé pour l'opérateur, explication parmi EXPLICATIONS).
    """
    if not mouvements:
        return "", "aucune"
    operations = ", ".join(
        f"op. n°{m.id} {m.sens} {formater_quantite(m.quantite)} dén. {date_fr(m.date_denouement)}"
        for m in mouvements
    )
    net = sum((m.signe for m in mouvements), Decimal(0))
    if net == ecart:
        explication, verdict = "totale", "écart entièrement expliqué"
    elif net * ecart > 0 and abs(net) < abs(ecart):
        explication = "partielle"
        verdict = f"écart partiellement expliqué, reste {formater_quantite(ecart - net)}"
    else:
        explication, verdict = "contraire", "n'explique pas l'écart"
    if plusieurs_conservateurs:  # mouvements n'indique pas le conservateur
        verdict += " (explication possible seulement : titre détenu chez plusieurs conservateurs)"
    return f"{operations} → {verdict}", explication


def _completer(
    suspens: list[Suspens],
    param: Parametrage,
    base: Base,
    date_arrete: date,
    conservateurs: dict[tuple[str, str], set[str]],
) -> None:
    for s in suspens:
        s.fonds = base.codes_fonds.get(s.entite, "")
        s.libelle_type, s.action = param.types_ecarts[s.type]
        if s.type == "DEP" and s.ecart:
            s.action += (
                f" ; puis {param.types_ecarts['QTE'][1]} (écart {formater_quantite(s.ecart)})"
            )
        if not s.libelle_titre and base.referentiel:
            s.libelle_titre = base.referentiel.get(s.isin, "")
        mouvements = [m for m in base.en_attente if m.portefeuille == s.fonds and m.isin == s.isin]
        plusieurs = sorted(conservateurs[(s.entite, s.isin)])
        s.piste, s.explication = _piste(mouvements, s.ecart, len(plusieurs) > 1)
        if mouvements and len(plusieurs) > 1:
            s.signaler(
                "PISTE_MULTI_CONSERVATEURS",
                f"piste à vérifier : titre détenu chez plusieurs conservateurs ({', '.join(plusieurs)}),"
                " l'opération peut concerner l'autre",
            )
        for m in mouvements:
            if m.date_denouement <= date_arrete:
                s.signaler(
                    "CSDR",
                    f"op. n°{m.id} non dénouée au {date_fr(m.date_denouement)} : "
                    "défaut de règlement-livraison, risque CSDR",
                )
        if not isin_valide(s.isin):
            s.signaler("ISIN_INVALIDE", "ISIN à clé invalide, probable erreur de saisie")


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
        motif = (
            f"plusieurs dates d'arrêté dans le PMS ({', '.join(sorted(dates))})"
            if dates
            else "date d'arrêté du PMS illisible"
        )
        return None, anomalie(noms[0], 0, "BLOQUANT", "DATE_ARRETE", "", "", motif)
    if date_attendue is not None and lue != date_attendue:
        return None, anomalie(
            noms[0],
            0,
            "BLOQUANT",
            "DATE_ARRETE",
            lue.isoformat(),
            "",
            f"fichiers arrêtés au {date_fr(lue)}, attendu le {date_fr(date_attendue)}",
        )
    return lue, None


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
    ) as erreur:  # sans paramétrage fiable, aucun fonds n'est identifiable
        resultat.journal.append(
            anomalie(
                Path(parametrage).name,
                0,
                "BLOQUANT",
                "PARAMETRAGE",
                "",
                "",
                f"{type(erreur).__name__} : {erreur}",
            )
        )
        resultat.statut = "BLOQUE"
        return resultat
    date_arrete, refus = _date_du_depot(fichiers, date_attendue)
    if refus:
        resultat.journal.append(refus)
    resultat.date_arrete = date_arrete
    pms: list[Position] = []
    dep: list[Position] = []
    for source, (prefixe, lecteur) in LECTEURS.items():
        noms = [n for n in fichiers if source_du_fichier(n) == source]
        if len(noms) != 1:
            regle, motif = (
                ("FICHIER_MANQUANT", f"fichier {source} absent")
                if not noms
                else ("FICHIERS_MULTIPLES", f"{len(noms)} fichiers {source} : lequel est le bon ?")
            )
            resultat.journal.append(
                anomalie(prefixe, 0, "BLOQUANT", regle, ", ".join(noms), "", motif)
            )
            continue
        nom = noms[0]
        try:
            lecture: Lecture = lecteur(nom, fichiers[nom], param, date_arrete)
        except (
            ERREURS_DE_FORMAT
        ) as erreur:  # fichier corrompu ou format inattendu : refusé, pas deviné
            resultat.journal.append(
                anomalie(
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
        # Un lecteur qui a déjà bloqué a dit pourquoi : « 0 position » en plus serait du bruit.
        if not lecture.positions and not any(a.niveau == "BLOQUANT" for a in lecture.journal):
            lecture.noter("BLOQUANT", "AUCUNE_LIGNE", 0, "", "", "0 position lue")
        resultat.journal.extend(lecture.journal)
        (pms if source == "PMS" else dep).extend(lecture.positions)

    if any(a.niveau == "BLOQUANT" for a in resultat.journal):
        resultat.statut = "BLOQUE"
        return resultat

    base = _lire_base(db_path, resultat.journal)
    resultat.journal.extend(_signaler(pms + dep, base))
    for m in base.en_attente:
        if m.date_denouement <= date_arrete:
            resultat.journal.append(
                Anomalie(
                    "orsay.db",
                    m.id,
                    "SIGNALE",
                    "DENOUEMENT_DEPASSE",
                    f"mouvement {m.id}",
                    "",
                    f"{m.portefeuille} {m.isin} {m.sens} {formater_quantite(m.quantite)} non dénoué "
                    f"au {date_fr(m.date_denouement)} : risque CSDR",
                )
            )

    conservateurs: dict[tuple[str, str], set[str]] = defaultdict(set)
    for p in pms + dep:
        if p.quantite:
            conservateurs[(p.entite, p.isin)].add(p.conservateur)

    resultat.suspens = _fusionner_dep(_comparer(pms, dep))
    _completer(resultat.suspens, param, base, date_arrete, conservateurs)
    resultat.suspens.sort(key=lambda s: (PRIORITES.index(s.priorite), s.entite, s.type, s.isin))
    return resultat


def rapprocher_dossier(dossier: Path) -> Resultat:
    fichiers = {
        f.name: f.read_bytes()
        for f in sorted(dossier.iterdir())
        if f.is_file() and source_du_fichier(f.name)
    }
    return rapprocher(fichiers, dossier / "parametrage.xlsx", dossier / "orsay.db")
