"""Ce que orsay.db apporte au rapprochement, à titre d'information : codes fonds, référentiel et
opérations en attente, qui donnent la piste de chaque suspens. Elle informe, elle ne décide pas.
"""

import sqlite3
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import NamedTuple

from middle_office.domaine.base_gestion import connexion_lecture_seule
from middle_office.domaine.formats import date_fr, formater_quantite
from middle_office.domaine.rapprochement.sources import Anomalie, Parametrage, isin_valide
from middle_office.domaine.rapprochement.suspens import Suspens


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


def lire_base(db_path: Path | None, journal: list[Anomalie]) -> Base:
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


def piste(
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


def completer(
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
        s.piste, s.explication = piste(mouvements, s.ecart, len(plusieurs) > 1)
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
