"""Le suspens et sa priorité : ce que l'opérateur doit traiter, dans quel ordre.

La priorité se décide sur des codes stables (`explication`, alertes des signalements), jamais sur
les libellés, rédigés pour les humains et susceptibles de changer.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import NamedTuple

from middle_office.domaine.rapprochement.sources import Anomalie

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
