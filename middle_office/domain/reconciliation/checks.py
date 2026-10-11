"""Contrôles qui n'empêchent pas le rapprochement mais remontent à un humain (niveau SIGNALE)."""

from collections import defaultdict
from datetime import date

from middle_office.domain.formats import date_fr, format_quantity
from middle_office.domain.reconciliation.db_context import DbContext
from middle_office.domain.reconciliation.sources import Anomaly, Position, is_valid_isin


def _flagged(file: str, line: int, rule: str, raw: str, kept: str, reason: str) -> Anomaly:
    return Anomaly(file, line, "SIGNALE", rule, raw, kept, reason)


def _doubtful_isins(positions: list[Position], db_info: DbContext) -> list[Anomaly]:
    """Une fois par ISIN : clé de contrôle invalide, ou absent du référentiel de orsay.db."""
    anomalies, seen = [], set()
    for p in positions:
        if p.isin in seen:
            continue
        seen.add(p.isin)
        if not is_valid_isin(p.isin):
            reason = "clé de contrôle ISIN invalide : probable erreur de saisie"
            anomalies.append(_flagged(p.file, p.line, "ISIN_CLE_INVALIDE", p.isin, p.isin, reason))
        if db_info.reference_data is not None and p.isin not in db_info.reference_data:
            reason = "ISIN absent du référentiel titres"
            anomalies.append(
                _flagged(p.file, p.line, "ISIN_HORS_REFERENTIEL", p.isin, p.isin, reason)
            )
    return anomalies


def _diverging_names(positions: list[Position]) -> list[Anomaly]:
    """Même ISIN, libellés PMS et conservateur différents (casse ignorée) : vérifier le titre."""
    by_isin: dict[str, dict[str, Position]] = defaultdict(dict)
    for p in positions:
        if p.label:
            by_isin[p.isin].setdefault("PMS" if p.source == "PMS" else "DEP", p)
    anomalies = []
    for isin, sides in by_isin.items():
        pms_position, custodian_position = sides.get("PMS"), sides.get("DEP")
        if (
            pms_position
            and custodian_position
            and pms_position.label.upper() != custodian_position.label.upper()
        ):
            reason = f"{isin} : libellé PMS « {pms_position.label} » ≠ conservateur « {custodian_position.label} »"
            anomalies.append(
                _flagged(
                    custodian_position.file,
                    custodian_position.line,
                    "LIBELLE_DIFFERENT",
                    custodian_position.label,
                    pms_position.label,
                    reason,
                )
            )
    return anomalies


def flag_positions(positions: list[Position], db_info: DbContext) -> list[Anomaly]:
    """ISIN douteux et libellés divergents : conservés, mais remontés à un humain."""
    return _doubtful_isins(positions, db_info) + _diverging_names(positions)


def overdue_settlements(db_info: DbContext, as_of_date: date) -> list[Anomaly]:
    """Opération toujours en attente alors que son dénouement était prévu au plus tard à l'arrêté :
    défaut de règlement-livraison, signalé même si les positions tombent juste."""
    return [
        Anomaly(
            "orsay.db",
            m.id,
            "SIGNALE",
            "DENOUEMENT_DEPASSE",
            f"mouvement {m.id}",
            "",
            f"{m.portfolio} {m.isin} {m.side} {format_quantity(m.quantity)} non dénoué "
            f"au {date_fr(m.settlement_date)} : risque CSDR",
        )
        for m in db_info.pending
        if m.settlement_date <= as_of_date
    ]
