"""PMS (positions_internes.csv) : la source interne du rapprochement, par sous-compte."""

import csv
import io
from datetime import date

from middle_office.domain.reconciliation.sources.client_config import ClientConfig
from middle_office.domain.reconciliation.sources.common import (
    SourceReading,
    check_date,
    decode_text,
    flag_ambiguous_separator,
    is_blank,
    normalize_isin,
    parse_decimal,
)

EXCLUDED_SUB_ACCOUNTS = {"P3G"}
PMS_COLUMNS = ("date_arrete", "sous_compte", "isin", "libelle", "quantite", "depositaire")


def custodian_code(label: str) -> str | None:
    """CACEIS -> A, EUROCLEAR -> B, BNP/BP2S -> C (insensible à la casse) ; None si inconnu."""
    upper = label.upper()
    if "CACEIS" in upper:
        return "A"
    if "EUROCLEAR" in upper:
        return "B"
    if "BNP" in upper or "BP2S" in upper:
        return "C"
    return None


def pms_dates(content: bytes) -> set[str]:
    """Dates d'arrêté distinctes du PMS : la source interne fixe la date du rapprochement."""
    text = decode_text(SourceReading(""), content)
    lines = csv.DictReader(io.StringIO(text, newline=""), delimiter=";")
    return {(line.get("date_arrete") or "").strip() for line in lines}


def _read_line(
    reading: SourceReading, num: int, line: dict, config: ClientConfig, as_of_date: date | None
) -> None:
    raw = ";".join(str(v or "") for v in line.values())
    try:
        read_date = date.fromisoformat((line["date_arrete"] or "").strip())
    except ValueError:
        read_date = None
    check_date(reading, num, read_date, as_of_date, raw)

    sub_account = (line["sous_compte"] or "").strip()
    if not sub_account:
        reading.exclude("SANS_SOUS_COMPTE", num, raw, "ligne sans sous-compte : anomalie de saisie")
        return
    if sub_account in EXCLUDED_SUB_ACCOUNTS:
        reading.exclude("P3G", num, raw, "compte technique de passage exclu")
        return
    if sub_account not in config.sub_accounts:
        reading.missing_mapping(num, sub_account, "TRANSCO_SOUS_COMPTES")
        return
    if is_blank(line["isin"]):
        reading.block("LIGNE_INCOMPLETE", num, raw, "ISIN vide")
        return

    custodian_label = (line["depositaire"] or "").strip()
    custodian = custodian_code(custodian_label)
    if custodian is None:
        reading.block(
            "CONSERVATEUR_INCONNU", num, custodian_label, "libellé de conservateur inconnu"
        )
        return
    reading.normalize(
        "LIBELLE_CONSERVATEUR", num, custodian_label, custodian, "libellé → code conservateur"
    )

    quantity = parse_decimal((line["quantite"] or "").strip())
    flag_ambiguous_separator(reading, num, line["quantite"] or "")
    if quantity is None:
        reading.block("QUANTITE_ILLISIBLE", num, line["quantite"], "quantité non numérique")
        return

    isin = normalize_isin(reading, num, line["isin"])
    entity, label = config.sub_accounts[sub_account], (line["libelle"] or "").strip()
    reading.add("PMS", entity, isin, custodian, quantity, label, num, account=sub_account)


def read_pms(
    name: str, content: bytes, config: ClientConfig, as_of_date: date | None
) -> SourceReading:
    reading = SourceReading(name)
    lines = csv.DictReader(io.StringIO(decode_text(reading, content), newline=""), delimiter=";")
    missing_columns = [c for c in PMS_COLUMNS if c not in (lines.fieldnames or [])]
    if missing_columns:
        header = ";".join(lines.fieldnames or [])
        reading.block("FORMAT", 1, header, f"colonne(s) absente(s) : {', '.join(missing_columns)}")
        return reading
    for num, line in enumerate(lines, start=2):
        _read_line(reading, num, line, config, as_of_date)
    return reading
