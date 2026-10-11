"""Exécution d'un rapprochement et traduction du résultat métier en réponse d'API."""

import hashlib
import logging
from collections import Counter
from datetime import UTC, datetime

from middle_office.api.config import Settings
from middle_office.api.schemas import (
    AnomalyOut,
    BreakOut,
    FileOut,
    FlagOut,
    FundSummary,
    Reconciliation,
    ReconciliationSummary,
    Summary,
)
from middle_office.api.services.history import History
from middle_office.api.services.upload import source_of
from middle_office.domain.reconciliation.breaks import PRIORITIES, Result
from middle_office.domain.reconciliation.engine import reconcile
from middle_office.domain.reconciliation.sources import REQUIRED_TYPES
from middle_office.domain.reconciliation.status_report import (
    breaks_csv,
    build_status_report,
    quantity_text,
)

LEVELS = ("BLOQUANT", "SIGNALE", "EXCLU", "NORMALISE")

log = logging.getLogger("middle_office.api.audit")


def execute(upload: dict[str, bytes], settings: Settings, history: History) -> Reconciliation:
    """Rapproche, enregistre dans l'historique et trace l'audit (sha256 des fichiers, jamais leur contenu)."""
    result = reconcile(upload, settings.client_config, settings.db_path, settings.expected_date())
    created_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    model = to_model(history.new_id(), created_at, upload, result)
    # CSV et point de situation figés maintenant : l'historique les relit sans garder `resultat`.
    history.add(model, breaks_csv(result.breaks), build_status_report(result))
    log.info(
        "audit rapprochement id=%s statut=%s nb_suspens=%d fichiers=%s",
        model.id,
        model.status,
        model.summary.break_count,
        ",".join(f"{f.name}:{f.sha256}" for f in model.files),
    )
    return model


def summarize(model: Reconciliation) -> ReconciliationSummary:
    priorities = model.summary.by_priority
    return ReconciliationSummary(
        id=model.id,
        created_at=model.created_at,
        as_of_date=model.as_of_date,
        status=model.status,
        break_count=model.summary.break_count,
        open_count=priorities["critique"] + priorities["a_relever"],
    )


def to_model(id_: str, created_at: str, upload: dict[str, bytes], r: Result) -> Reconciliation:
    breaks = [
        BreakOut(
            id=f"S{i}",
            priority=s.priority,
            fund=s.fund,
            entity=s.entity,
            isin=s.isin,
            security_name=s.security_name,
            custodian=s.custodian,
            type=s.type,
            break_type_label=s.break_type_label,
            pms_qty=quantity_text(s.pms_qty),
            custodian_qty=quantity_text(s.custodian_qty),
            difference=quantity_text(s.difference),
            action=s.action,
            lead=s.lead,
            explanation=s.explanation,
            alerts=sorted(s.alerts),
            flags=[FlagOut(code=g.code, message=g.message) for g in s.flags],
            sources=list(s.sources),
        )
        for i, s in enumerate(r.breaks, start=1)
    ]
    return Reconciliation(
        id=id_,
        created_at=created_at,
        as_of_date=r.as_of_date.isoformat() if r.as_of_date else None,
        status=r.status,
        files=[
            FileOut(
                name=name,
                source=source_of(name),
                size=len(content),
                sha256=hashlib.sha256(content).hexdigest(),
            )
            for name, content in upload.items()
        ],
        summary=_summary(r, breaks),
        breaks=breaks,
        cleaning_log=[AnomalyOut(**vars(a)) for a in r.cleaning_log],
    )


def _summary(r: Result, breaks: list[BreakOut]) -> Summary:
    by_fund = Counter((s.fund, s.entity) for s in r.breaks)
    levels = Counter(a.level for a in r.cleaning_log)
    return Summary(
        break_count=len(breaks),
        by_priority={p: sum(s.priority == p for s in breaks) for p in PRIORITIES},
        by_type={t: sum(s.type == t for s in breaks) for t in REQUIRED_TYPES},
        by_fund=[
            FundSummary(code=code, entity=entity, break_count=n)
            for (code, entity), n in sorted(by_fund.items())
        ],
        by_custodian=dict(Counter(s.custodian for s in breaks)),
        cleaning_log={n: levels[n] for n in LEVELS},
    )
