"""Tombées d'échéances à venir : titres détenus qui arrivent à maturité dans l'horizon demandé."""

import calendar
from datetime import date
from decimal import Decimal
from pathlib import Path

from middle_office.domain.formats import amount, date_fr, format_quantity
from middle_office.domain.management_db import decimal, read_only_connection
from middle_office.domain.questions.catalog.common import PMS_WARNING, scope_label
from middle_office.domain.questions.models import (
    Answer,
    Figure,
    SourceRow,
)

DEFAULT_HORIZON_MONTHS = 12  # à valider avec le client (NOTES.md, Q4)


SQL_MATURITIES = """
SELECT p.portefeuille, f.nom, p.isin, t.libelle, t.type_titre, t.date_echeance, p.quantite
FROM positions p
JOIN portefeuilles f ON f.code = p.portefeuille
JOIN titres t ON t.isin = p.isin
WHERE p.date_arrete = :date AND p.quantite > 0
  AND t.date_echeance > :date AND t.date_echeance <= :end
  AND (:fund IS NULL OR p.portefeuille = :fund) AND (:isin IS NULL OR p.isin = :isin)
ORDER BY t.date_echeance, p.portefeuille, p.isin
""".strip()


def add_months(d: date, months: int) -> date:
    year, month_0 = divmod(d.month - 1 + months, 12)
    year += d.year
    return date(year, month_0 + 1, min(d.day, calendar.monthrange(year, month_0 + 1)[1]))


def _end_bound(
    ref_date: date, horizon_months: int | None, isin: str | None, end: date | None
) -> tuple[date | None, bool]:
    """Date de fin (None : pas de borne) et vrai si l'horizon par défaut s'applique. Un titre précis
    sans horizon n'a pas de borne : « quand tombe EDF 2031 ? » ne doit pas répondre « aucune tombée »
    parce que c'est au-delà de 12 mois."""
    if end is not None or horizon_months is not None:
        return end or add_months(ref_date, horizon_months or DEFAULT_HORIZON_MONTHS), False
    if isin is not None:
        return None, False
    return add_months(ref_date, DEFAULT_HORIZON_MONTHS), True


def _source(line: tuple) -> SourceRow:
    code, _name, isin, label, security_type, maturity, quantity = line
    return SourceRow(
        "positions × titres",
        {
            "portefeuille": code,
            "isin": isin,
            "libelle": label,
            "type_titre": security_type,
            "date_echeance": maturity,
            "nominal": str(decimal(quantity)),
        },
    )


def _detail(line: tuple) -> str:
    code, _name, _isin, label, _type, maturity, quantity = line
    return f"{label} ({code}) le {date_fr(date.fromisoformat(maturity))} pour {format_quantity(decimal(quantity))}"


def maturities(
    db_path: Path,
    fund: str | None,
    ref_date: date,
    horizon_months: int | None = None,
    isin: str | None = None,
    end: date | None = None,
) -> Answer:
    """Titres détenus arrivant à échéance après la date de référence, dans l'horizon donné."""
    end, default_horizon = _end_bound(ref_date, horizon_months, isin, end)
    params = {
        "date": ref_date.isoformat(),
        "end": (end or date.max).isoformat(),
        "fund": fund,
        "isin": isin,
    }
    with read_only_connection(db_path) as db:
        lines = db.execute(SQL_MATURITIES, params).fetchall()
    warnings = [
        "Montant remboursé = nominal détenu (remboursement au pair), hors dernier coupon.",
        PMS_WARNING,
    ]
    if default_horizon:
        warnings.insert(
            0,
            f"Horizon par défaut de {DEFAULT_HORIZON_MONTHS} mois (à valider avec le middle office).",
        )
    scope = scope_label(fund, isin)
    bound = (
        f"entre le {date_fr(ref_date)} et le {date_fr(end)}"
        if end
        else f"après le {date_fr(ref_date)}"
    )
    if not lines:
        sentence = f"Aucune tombée d'échéance {scope} {bound}."
        return Answer(sentence, [], SQL_MATURITIES, params, [], warnings=warnings)

    nominal = sum((decimal(line[6]) for line in lines), Decimal(0))
    sentence = (
        f"{len(lines)} tombée(s) d'échéance {scope} {bound} : {', '.join(map(_detail, lines))}. "
        f"Nominal remboursé : {amount(nominal)} EUR."
    )
    figures = [
        Figure("Tombées d'échéance", Decimal(len(lines)), "lignes"),
        Figure("Nominal remboursé", nominal, "EUR"),
    ]
    sources = [_source(line) for line in lines]
    return Answer(sentence, figures, SQL_MATURITIES, params, sources, warnings=warnings)
