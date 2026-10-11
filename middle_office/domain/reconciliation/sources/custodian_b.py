"""Conservateur B (Euroclear) : fichier à largeur fixe, décimales implicites, total de contrôle."""

from datetime import date
from decimal import Decimal

from middle_office.domain.reconciliation.sources.client_config import ClientConfig
from middle_office.domain.reconciliation.sources.common import (
    SourceReading,
    check_date,
    decode_text,
    normalize_isin,
)


def _read_detail(reading: SourceReading, num: int, line: str, config: ClientConfig) -> None:
    """D + desk(3) + ISIN(12) + quantité(15, 2 décimales implicites) : 31 caractères exactement."""
    desk, isin, raw = line[1:4], line[4:16], line[16:31]
    if len(line) != 31:
        reading.block("FORMAT", num, line, "ligne de détail de longueur ≠ 31")
        return
    if desk not in config.desks_b:
        reading.missing_mapping(num, desk, "TRANSCO_DEPOSITAIRE_B")
        return
    if not raw.isdigit():
        reading.block("QUANTITE_ILLISIBLE", num, raw, "quantité non numérique")
        return
    qty = Decimal(raw).scaleb(-2)
    reading.normalize("DECIMALES_IMPLICITES", num, raw, qty, "2 décimales implicites")
    reading.add(
        "B",
        config.desks_b[desk],
        normalize_isin(reading, num, isin),
        "B",
        qty,
        "",
        num,
        account=desk,
    )


def read_custodian_b(
    name: str, content: bytes, config: ClientConfig, as_of_date: date | None
) -> SourceReading:
    """Largeur fixe : H+date, lignes de détail D, puis T + nombre de lignes de détail (contrôle)."""
    reading = SourceReading(name)
    lines = decode_text(reading, content).splitlines()
    header = next((line for line in lines if line.startswith("H")), "")
    try:
        read_date = date(int(header[1:5]), int(header[5:7]), int(header[7:9]))
    except ValueError:
        read_date = None
    check_date(reading, 1, read_date, as_of_date, header)

    details, control_line = 0, None
    for num, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        if line[0] not in "HDT":
            reading.block("TYPE_LIGNE_INCONNU", num, line, f"enregistrement de type « {line[0]} »")
        elif line[0] == "T":
            control_line = line
        elif line[0] == "D":
            details += 1
            _read_detail(reading, num, line, config)

    if control_line is None or not control_line[1:].isdigit() or int(control_line[1:]) != details:
        reason = f"total de contrôle {control_line!r} ≠ {details} lignes de détail"
        reading.block("TOTAL_CONTROLE", len(lines), control_line, reason, kept=details)
    return reading
