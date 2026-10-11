"""Le suspens et sa priorité : ce que l'opérateur doit traiter, dans quel ordre.

La priorité se décide sur des codes stables (`explication`, alertes des signalements), jamais sur
les libellés, rédigés pour les humains et susceptibles de changer.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import NamedTuple

from middle_office.domain.reconciliation.sources import Anomaly

PRIORITIES = ("critique", "a_relever", "en_attente")  # ordre de traitement


EXPLAINABLE_TYPES = ("QTE", "ABS_DEP", "ABS_INT")  # par une opération en attente de dénouement


EXPLANATIONS = ("aucune", "totale", "partielle", "contraire")  # par les opérations en attente


ALERTS = ("CSDR", "DEP_AMBIGU", "ISIN_INVALIDE", "PISTE_MULTI_CONSERVATEURS")


class Flag(NamedTuple):
    code: str  # ALERTES : c'est lui que lisent la priorité et l'interface
    message: str  # pour l'opérateur


@dataclass
class Break:
    entity: str  # clé fonds : nom d'entité du paramétrage (la référence)
    isin: str
    custodian: str  # A, B, C, ou « A→B » pour un DEP
    type: str  # QTE, ABS_DEP, ABS_INT, DEP
    pms_qty: Decimal | None
    custodian_qty: Decimal | None
    security_name: str
    sources: list[str]
    fund: str = ""  # code court (PAT, OBL, ACT) lu dans orsay.db, vide si la base manque
    break_type_label: str = ""
    action: str = ""
    lead: str = ""
    flags: list[Flag] = field(default_factory=list)
    # Ce qui décide de la priorité : des codes stables, jamais les libellés (faits pour les humains).
    explanation: str = "aucune"  # EXPLICATIONS

    @property
    def alerts(self) -> set[str]:
        return {s.code for s in self.flags}

    def flag(self, code: str, message: str) -> None:
        assert code in ALERTS, code
        self.flags.append(Flag(code, message))

    @property
    def difference(self) -> Decimal:
        """PMS − conservateur : positif si le PMS en a plus (achat non dénoué, par exemple)."""
        return (self.pms_qty or Decimal(0)) - (self.custodian_qty or Decimal(0))

    @property
    def priority(self) -> str:
        return priority(self)


def priority(s: Break) -> str:
    """critique : risque CSDR ; en_attente : écart entièrement expliqué par des opérations en attente,
    sans alerte ; sinon a_relever. Un achat de ligne nouvelle non dénoué donne un ABS_DEP expliqué,
    une vente totale un ABS_INT : même traitement qu'un QTE. Un DEP (mauvais conservateur) n'est
    jamais expliqué par une opération."""
    if "CSDR" in s.alerts:
        return "critique"
    if s.type in EXPLAINABLE_TYPES and s.explanation == "totale" and not s.alerts:
        return "en_attente"
    return "a_relever"


@dataclass
class Result:
    status: str = "OK"  # OK, ou BLOQUE si une anomalie BLOQUANT empêche le rapprochement
    as_of_date: date | None = None  # lue dans le PMS ; None si absente ou ambiguë
    breaks: list[Break] = field(default_factory=list)
    cleaning_log: list[Anomaly] = field(default_factory=list)
