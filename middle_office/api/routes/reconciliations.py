"""Rapprochements : création (dépôt ou exemple), historique, exports (CSV, point de situation)."""

from fastapi import APIRouter, Request, Response

from middle_office.api.dependencies import HistoryDep, SettingsDep
from middle_office.api.schemas import (
    BreakWorkStatus,
    Reconciliation,
    ReconciliationRequest,
    ReconciliationSummary,
    StatusReport,
    WorkStatusChange,
    WorkStatuses,
)
from middle_office.api.services import reconciliations, statuses, upload

router = APIRouter(prefix="/api/reconciliations", tags=["reconciliations"])


def _http_status(model: Reconciliation, response: Response) -> Reconciliation:
    # Refus métier : pas une erreur HTTP, le journal dit quoi faire (docs/API.md).
    response.status_code = 200 if model.status == "BLOQUE" else 201
    return model


@router.post("", status_code=201)
def create(
    request_body: ReconciliationRequest,
    response: Response,
    settings: SettingsDep,
    history: HistoryDep,
) -> Reconciliation:
    files = upload.decode(request_body, settings.max_file_size)
    return _http_status(reconciliations.execute(files, settings, history), response)


@router.post("/sample", status_code=201)
def sample(response: Response, settings: SettingsDep, history: HistoryDep) -> Reconciliation:
    files = upload.sample_upload(settings.data_dir)
    return _http_status(reconciliations.execute(files, settings, history), response)


@router.get("")
def list_reconciliations(history: HistoryDep) -> list[ReconciliationSummary]:
    return [reconciliations.summarize(r) for r in history.recent()]


@router.get("/{id_}")
def read(id_: str, history: HistoryDep) -> Reconciliation:
    return history.read(id_).model


@router.get("/{id_}/breaks.csv")
def breaks_csv(id_: str, history: HistoryDep) -> Response:
    entry = history.read(id_)
    return Response(
        entry.csv,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="suspens_{entry.model.as_of_date or "date-inconnue"}.csv"'
        },
    )


@router.get("/{id_}/status-report")
def status_report(id_: str, history: HistoryDep) -> StatusReport:
    return StatusReport(text=history.read(id_).status_report)


@router.get("/{id_}/statuses")
def get_statuses(id_: str, history: HistoryDep) -> WorkStatuses:
    return statuses.read(history, id_)


@router.put("/{id_}/breaks/{break_id}/status")
def save_status(
    id_: str,
    break_id: str,
    change: WorkStatusChange,
    request: Request,
    history: HistoryDep,
) -> BreakWorkStatus:
    return statuses.set_status(history, id_, break_id, change.status, request.state.request_id)
