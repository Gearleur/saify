"""Modèles d'entrée et de sortie (contrat : docs/API.md). Quantités en chaînes décimales, jamais de float."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from middle_office.api.config import EXTENSIONS

# Entrées : champs inconnus refusés


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FileIn(Input):
    name: str = Field(min_length=1, max_length=255)
    content_b64: str

    @field_validator("name")
    @classmethod
    def base_name_only(cls, name: str) -> str:
        if "/" in name or "\\" in name or ".." in name or any(ord(c) < 32 for c in name):
            raise ValueError(
                "nom de base seul attendu (ni chemin, ni « .. », ni caractère de contrôle)"
            )
        if not name.lower().endswith(EXTENSIONS):
            raise ValueError(f"extension non autorisée (attendu : {', '.join(EXTENSIONS)})")
        return name


class ReconciliationRequest(Input):
    files: list[FileIn] = Field(min_length=1, max_length=8)


WorkStatus = Literal["a_traiter", "en_cours", "traite"]


class WorkStatusChange(Input):
    status: WorkStatus


class Question(Input):
    question: str = Field(min_length=3, max_length=500)

    @field_validator("question")
    @classmethod
    def clean_text(cls, question: str) -> str:
        """Caractères de contrôle retirés, espaces normalisés : ce qui part au LLM et aux logs reste propre."""
        cleaned = " ".join("".join(c if c.isprintable() else " " for c in question).split())
        if len(cleaned) < 3:
            raise ValueError("question trop courte")
        return cleaned


# Sorties : rapprochement


class FileOut(BaseModel):
    name: str
    source: str
    size: int
    sha256: str


class FundSummary(BaseModel):
    code: str
    entity: str
    break_count: int


class Summary(BaseModel):
    break_count: int
    by_priority: dict[str, int]
    by_type: dict[str, int]
    by_fund: list[FundSummary]
    by_custodian: dict[str, int]
    cleaning_log: dict[str, int]


class FlagOut(BaseModel):
    code: str  # CSDR, DEP_AMBIGU, ISIN_INVALIDE, PISTE_MULTI_CONSERVATEURS
    message: str


class BreakOut(BaseModel):
    id: str
    priority: str
    fund: str
    entity: str
    isin: str
    security_name: str
    custodian: str
    type: str
    break_type_label: str
    pms_qty: str | None
    custodian_qty: str | None
    difference: str
    action: str
    lead: str
    explanation: str  # aucune, totale, partielle, contraire (par les opérations en attente)
    alerts: list[str]  # codes des signalements, triés : ce que lit l'interface, jamais le texte
    flags: list[FlagOut]
    sources: list[str]


class AnomalyOut(BaseModel):
    file: str
    line: int
    level: str
    rule: str
    raw: str
    kept: str
    reason: str
    remedy: str


class Reconciliation(BaseModel):
    id: str
    created_at: str
    as_of_date: str | None  # lue dans le PMS ; None si absente ou ambiguë (rapprochement BLOQUE)
    status: str
    files: list[FileOut]
    summary: Summary
    breaks: list[BreakOut]
    cleaning_log: list[AnomalyOut]


class ReconciliationSummary(BaseModel):
    id: str
    created_at: str
    as_of_date: str | None  # lue dans le PMS ; None si absente ou ambiguë (rapprochement BLOQUE)
    status: str
    break_count: int
    open_count: int


class WorkStatuses(BaseModel):
    """Statut de chaque suspens du rapprochement (id S1…Sn) ; absent = « a_traiter »."""

    statuses: dict[str, WorkStatus]


class BreakWorkStatus(BaseModel):
    break_id: str
    status: WorkStatus
    updated_at: str


class StatusReport(BaseModel):
    text: str


# Sorties : santé et référentiel


class LlmState(BaseModel):
    enabled: bool
    model: str
    calls_today: int
    daily_budget: int


class Health(BaseModel):
    status: str
    version: str
    as_of_date: str | None  # date de référence de la base de gestion (dernières positions)
    db_available: bool
    llm: LlmState


class Fund(BaseModel):
    entity: str
    code: str


class Custodian(BaseModel):
    code: str
    name: str


class BreakType(BaseModel):
    code: str
    label: str
    expected_action: str


class Mapping(BaseModel):
    key: str
    entity: str


class ClientConfigOut(BaseModel):
    as_of_date: str | None
    fund: list[Fund]
    custodians: list[Custodian]
    break_types: list[BreakType]
    mappings: dict[str, list[Mapping]]
    exclusions: list[str]


# Sorties : questions sur la base (besoin 2)


class FigureOut(BaseModel):
    label: str
    value: str  # décimal en texte
    unit: str


class SourceRowOut(BaseModel):
    table: str
    values: dict[str, str]


class VigilanceOut(BaseModel):
    code: str
    message: str
    issuers: list[str]
    value: str  # en %


class UnderstandingOut(BaseModel):
    intent: str
    fund: str | None
    horizon_months: int | None
    isin: str | None
    source: str  # llm ou mots_cles
    confidence: float
    detail: str
    requested_date: str | None = (
        None  # date citée dans la question (AAAA-MM-JJ ou expression relative)
    )


class QuestionAnswer(BaseModel):
    question: str
    answer: str
    figures: list[FigureOut]
    sql_query: str
    sql_params: dict[str, str | None]
    source_rows: list[SourceRowOut]
    confidence: str
    warnings: list[str]
    vigilances: list[VigilanceOut]
    suggestions: list[str]
    understanding: UnderstandingOut
