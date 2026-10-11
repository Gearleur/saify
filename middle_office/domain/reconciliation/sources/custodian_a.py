"""Conservateur A (CACEIS) : classeur Excel, titre daté, quantités parfois en texte."""

import io
import re
from contextlib import closing
from datetime import date

import openpyxl

from middle_office.domain.reconciliation.sources.client_config import ClientConfig
from middle_office.domain.reconciliation.sources.common import (
    SourceReading,
    check_date,
    flag_ambiguous_separator,
    is_blank,
    normalize_isin,
    parse_decimal,
)


def _read_line(reading: SourceReading, num: int, cells: tuple, config: ClientConfig) -> None:
    account, isin, designation, quantity = (list(cells) + [None] * 4)[:4]
    if all(is_blank(v) for v in cells):
        return
    if is_blank(account) or is_blank(isin) or is_blank(quantity):
        reading.block("LIGNE_INCOMPLETE", num, cells, "compte, ISIN ou quantité vide")
        return
    account = str(account).strip()
    if account not in config.accounts_a:
        reading.missing_mapping(num, account, "TRANSCO_DEPOSITAIRE_A")
        return
    raw = str(quantity)
    qty = parse_decimal(re.sub(r"\s", "", raw))
    flag_ambiguous_separator(reading, num, raw)
    if qty is None:
        reading.block("QUANTITE_ILLISIBLE", num, raw, "quantité non numérique")
        return
    if raw != str(qty):
        reading.normalize("SEPARATEUR_MILLIERS", num, raw, qty, "quantité texte → nombre")
    isin, label = normalize_isin(reading, num, str(isin)), str(designation or "").strip()
    reading.add("A", config.accounts_a[account], isin, "A", qty, label, num, account=account)


def read_custodian_a(
    name: str, content: bytes, config: ClientConfig, as_of_date: date | None
) -> SourceReading:
    """Classeur : titre daté (JJ/MM/AAAA), puis un tableau sous l'en-tête « Compte »."""
    reading = SourceReading(name)
    with closing(openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)) as wb:
        lines = list(wb.worksheets[0].iter_rows(values_only=True))

    security = str(lines[0][0] or "") if lines else ""
    date_match = re.search(r"(\d{2})/(\d{2})/(\d{4})", security)
    read_date = (
        date(int(date_match[3]), int(date_match[2]), int(date_match[1])) if date_match else None
    )
    check_date(reading, 1, read_date, as_of_date, security)

    header = next((i for i, line in enumerate(lines) if line and line[0] == "Compte"), None)
    if header is None:
        reading.block("FORMAT", 0, "", "en-tête « Compte » introuvable")
        return reading
    for num, cells in enumerate(lines[header + 1 :], start=header + 2):
        _read_line(reading, num, cells, config)
    return reading
