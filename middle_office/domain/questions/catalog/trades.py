"""Opérations non dénouées : en attente de règlement-livraison ; une date prévue dépassée est un
défaut de règlement, donc un risque CSDR.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import NamedTuple

from middle_office.domain.formats import CENT, date_fr, format_quantity
from middle_office.domain.management_db import decimal, read_only_connection
from middle_office.domain.questions.catalog.common import market_value, scope_label
from middle_office.domain.questions.models import (
    Answer,
    Figure,
    SourceRow,
)

SQL_UNSETTLED = """
SELECT m.id, m.date_operation, m.date_denouement, m.portefeuille, m.isin, t.libelle,
       t.mode_cotation, m.sens, m.quantite, m.prix, m.contrepartie
FROM mouvements m
LEFT JOIN titres t ON t.isin = m.isin
WHERE m.statut = 'EN_ATTENTE' AND (:fund IS NULL OR m.portefeuille = :fund)
  AND (:isin IS NULL OR m.isin = :isin)
ORDER BY m.date_denouement, m.id
""".strip()


class _Trade(NamedTuple):
    detail: str  # pour la phrase de réponse
    source: SourceRow
    delay: str | None  # avertissement CSDR si la date de dénouement prévue est dépassée


def _trade(line: tuple, ref_date: date) -> _Trade:
    (
        id_,
        trade_date,
        settlement_date,
        code,
        isin,
        label,
        mode,
        side,
        quantity,
        price,
        counterparty,
    ) = line
    qty, price = decimal(quantity), decimal(price)
    value = None if price is None else market_value(qty, price, mode)
    due = date.fromisoformat(settlement_date)
    delay = None
    if due <= ref_date:
        delay = (
            f"Op. n°{id_} ({label or isin}) devait être dénouée le {date_fr(due)} : "
            "défaut de règlement-livraison, risque CSDR."
        )
    detail = (
        f"n°{id_} {side} {format_quantity(qty)} {label or isin} ({code}, dén. prévu {date_fr(due)})"
    )
    source = SourceRow(
        "mouvements",
        {
            "id": str(id_),
            "date_operation": trade_date,
            "date_denouement": settlement_date,
            "portefeuille": code,
            "isin": isin,
            "sens": side,
            "quantite": str(qty),
            "prix": "" if price is None else str(price),
            "montant": "" if value is None else str(value.quantize(CENT)),
            "contrepartie": counterparty or "",
        },
    )
    return _Trade(detail, source, delay)


def unsettled_trades(
    db_path: Path, fund: str | None, ref_date: date, isin: str | None = None
) -> Answer:
    """Opérations en attente de dénouement ; une date prévue dépassée est un défaut de règlement (CSDR)."""
    params = {"fund": fund, "isin": isin}
    with read_only_connection(db_path) as db:
        lines = db.execute(SQL_UNSETTLED, params).fetchall()
    scope = scope_label(fund, isin)
    warnings = ["Statut lu dans la base de gestion (opérations de la semaine)."]
    if not lines:
        sentence = f"Aucune opération non dénouée {scope}."
        return Answer(sentence, [], SQL_UNSETTLED, params, [], warnings=warnings)

    trades = [_trade(line, ref_date) for line in lines]
    delays = [o.delay for o in trades if o.delay]
    warnings = list(reversed(delays)) + warnings  # les retards d'abord, le plus récent en tête
    suffix = f", dont {len(delays)} en retard (risque CSDR)" if delays else ""
    sentence = (
        f"{len(lines)} opération(s) non dénouée(s) {scope} au {date_fr(ref_date)}{suffix} : "
        f"{', '.join(o.detail for o in trades)}."
    )
    figures = [Figure("Opérations non dénouées", Decimal(len(lines)), "opérations")]
    if delays:
        figures.append(Figure("En retard (risque CSDR)", Decimal(len(delays)), "opérations"))
    sources = [o.source for o in trades]
    return Answer(sentence, figures, SQL_UNSETTLED, params, sources, warnings=warnings)
