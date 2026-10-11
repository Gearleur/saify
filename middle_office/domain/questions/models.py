"""Forme d'une réponse (contrat : docs/API.md, POST /api/questions) : chaque chiffre est traçable."""

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class Figure:
    label: str
    value: Decimal
    unit: str


@dataclass(frozen=True)
class SourceRow:
    table: str
    values: dict[str, str]


@dataclass(frozen=True)
class Vigilance:
    """Seuil de vigilance interne franchi : attire l'attention, ne juge pas la conformité."""

    code: str
    message: str
    issuers: list[str]
    value: Decimal  # en %


@dataclass
class Answer:
    answer: str  # phrase issue d'un gabarit, jamais rédigée par le LLM
    figures: list[Figure]
    sql_query: str  # la requête exacte exécutée, rejouable avec `parametres_sql`
    sql_params: dict[str, str | None]
    source_rows: list[SourceRow]
    confidence: str = "haute"  # haute, ou basse dès qu'un chiffre est partiel ou douteux
    warnings: list[str] = field(default_factory=list)
    vigilances: list[Vigilance] = field(default_factory=list)
    question: str = ""
    suggestions: list[str] = field(default_factory=list)  # proposées quand on ne répond pas
    understanding: dict = field(
        default_factory=dict
    )  # intention retenue, paramètres, source (llm ou mots_cles)


@dataclass(frozen=True)
class ReconciliationContext:
    """Le rapprochement sur lequel répondre à « d'où vient le suspens sur X ? ».

    `id` est le dernier rapprochement exploitable (statut OK) ; `bloque_plus_recent`, l'id d'un
    rapprochement plus récent mais bloqué : la réponse doit le dire, sinon elle rassure à tort.
    """

    id: str | None
    as_of_date: str | None = None
    breaks: list[dict] = field(default_factory=list)
    newer_blocked: str | None = None
