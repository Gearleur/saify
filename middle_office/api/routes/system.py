"""Santé de l'API et référentiel (lecture seule)."""

from fastapi import APIRouter

from middle_office.api.config import VERSION
from middle_office.api.dependencies import LlmDep, SettingsDep
from middle_office.api.schemas import ClientConfigOut, Health, LlmState
from middle_office.api.services import reference_data
from middle_office.domain.questions.understanding import MODEL

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
def health(settings: SettingsDep, llm: LlmDep) -> Health:
    state = LlmState(
        enabled=llm is not None,
        model=MODEL,
        daily_budget=settings.llm_daily_budget,
        calls_today=0 if llm is None else llm.calls_today,
    )
    return Health(
        status="ok",
        version=VERSION,
        as_of_date=reference_data.db_date(settings.db_path),
        db_available=reference_data.db_available(settings.db_path),
        llm=state,
    )


@router.get("/client-config")
def client_config(settings: SettingsDep) -> ClientConfigOut:
    return reference_data.client_config(settings)
