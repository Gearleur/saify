"""Forme d'une réponse (contrat : docs/API.md, POST /api/questions) : chaque chiffre est traçable."""

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class Chiffre:
    libelle: str
    valeur: Decimal
    unite: str


@dataclass(frozen=True)
class LigneSource:
    table: str
    valeurs: dict[str, str]


@dataclass(frozen=True)
class Vigilance:
    """Seuil de vigilance interne franchi : attire l'attention, ne juge pas la conformité."""

    code: str
    message: str
    emetteurs: list[str]
    valeur: Decimal  # en %


@dataclass
class Reponse:
    reponse: str  # phrase issue d'un gabarit, jamais rédigée par le LLM
    chiffres: list[Chiffre]
    requete_sql: str  # la requête exacte exécutée, rejouable avec `parametres_sql`
    parametres_sql: dict[str, str | None]
    lignes_sources: list[LigneSource]
    confiance: str = "haute"  # haute, ou basse dès qu'un chiffre est partiel ou douteux
    avertissements: list[str] = field(default_factory=list)
    vigilances: list[Vigilance] = field(default_factory=list)
    question: str = ""
    reformulations: list[str] = field(default_factory=list)  # proposées quand on ne répond pas
    comprehension: dict = field(
        default_factory=dict
    )  # intention retenue, paramètres, source (llm ou mots_cles)


@dataclass(frozen=True)
class ContexteRapprochement:
    """Le rapprochement sur lequel répondre à « d'où vient le suspens sur X ? ».

    `id` est le dernier rapprochement exploitable (statut OK) ; `bloque_plus_recent`, l'id d'un
    rapprochement plus récent mais bloqué : la réponse doit le dire, sinon elle rassure à tort.
    """

    id: str | None
    date_arrete: str | None = None
    suspens: list[dict] = field(default_factory=list)
    bloque_plus_recent: str | None = None


def montant(valeur: Decimal) -> str:
    """724836.00 -> « 724 836,00 »"""
    return f"{valeur:,.2f}".replace(",", " ").replace(".", ",")
