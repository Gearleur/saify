"""Conservateur C (BNP Paribas, BP2S) : XML à namespace, lots, annulations, NbItems de contrôle."""

import xml.etree.ElementTree as ET
from datetime import date

from middle_office.domain.reconciliation.sources.client_config import ClientConfig
from middle_office.domain.reconciliation.sources.common import (
    SourceReading,
    check_date,
    flag_ambiguous_separator,
    normalize_isin,
    parse_decimal,
)

NS_C = {"c": "urn:orsay:depositaire-c:positions:2026"}
PROPS_C = ("ACTION", "COMPTE", "CODE_ISIN", "LIBELLE_TITRE", "QUANTITE", "LOT")


ACTIONS_C = {"C", "S"}  # C : position, S : annulation


def _dtd_present(content: bytes) -> bool:
    """Cherche aussi dans la version UTF-16, qu'expat accepterait avec un BOM."""
    texts = [content.upper()]
    if content[:2] in (b"\xff\xfe", b"\xfe\xff"):
        texts.append(content.decode("utf-16", errors="replace").upper().encode())
    return any(b"<!DOCTYPE" in t or b"<!ENTITY" in t for t in texts)


def _check_header(
    reading: SourceReading, root: ET.Element, read_count: int, as_of_date: date | None
) -> None:
    """Date d'arrêté (JJMMAAAA) et NbItems, qui compte aussi les annulations."""
    raw_date = root.findtext(".//c:DateArrete", "", NS_C).strip()
    try:
        read_date = date(int(raw_date[4:8]), int(raw_date[2:4]), int(raw_date[0:2]))
    except ValueError:
        read_date = None
    check_date(reading, 0, read_date, as_of_date, raw_date)
    item_count = root.findtext(".//c:NbItems", "", NS_C).strip()
    if item_count != str(read_count):
        reading.block(
            "TOTAL_CONTROLE",
            0,
            item_count,
            f"NbItems {item_count!r} ≠ {read_count} Item lus",
            kept=read_count,
        )


def _read_item(reading: SourceReading, num: int, dims: dict, config: ClientConfig) -> None:
    missing = [p for p in PROPS_C if p not in dims or (p != "LIBELLE_TITRE" and not dims[p])]
    if missing:
        reading.block("CHAMP_MANQUANT", num, dims, f"Dim manquant ou vide : {', '.join(missing)}")
        return
    if dims["ACTION"] == "S":
        reading.exclude("ANNULATION_S", num, dims, "item annulé (ACTION=S), ni ajouté ni soustrait")
        return
    if dims["ACTION"] not in ACTIONS_C:
        # Ni additionné (il pourrait combler un écart) ni écarté (il pourrait en créer un) : refusé.
        reason = f"ACTION « {dims['ACTION']} » inconnue (attendu : C ou S)"
        reading.block("ACTION_INCONNUE", num, dims["ACTION"], reason)
        return
    if dims["COMPTE"] not in config.accounts_c:
        reading.missing_mapping(num, dims["COMPTE"], "TRANSCO_DEPOSITAIRE_C")
        return
    raw = dims["QUANTITE"]
    qty = parse_decimal(raw.replace(",", "."))
    flag_ambiguous_separator(reading, num, raw)
    if qty is None:
        reading.block("QUANTITE_ILLISIBLE", num, raw, "quantité non numérique")
        return
    if "," in raw:
        reading.normalize("VIRGULE_DECIMALE", num, raw, qty, "virgule décimale")
    isin = normalize_isin(reading, num, dims["CODE_ISIN"])
    entity, account = config.accounts_c[dims["COMPTE"]], f"{dims['COMPTE']} lot {dims['LOT']}"
    reading.add("C", entity, isin, "C", qty, dims["LIBELLE_TITRE"], num, account=account)


def read_custodian_c(
    name: str, content: bytes, config: ClientConfig, as_of_date: date | None
) -> SourceReading:
    """XML à namespace ; les lots distincts d'un même (compte, ISIN) sont additionnés, un lot répété bloque."""
    reading = SourceReading(name)
    if _dtd_present(content):  # avant tout parsing : entités externes, « billion laughs »
        reason = "DOCTYPE ou ENTITY interdit dans le XML conservateur : fichier refusé par sécurité"
        reading.block("FORMAT", 0, "", reason)
        return reading
    root = ET.fromstring(content)
    items = root.findall(".//c:Item", NS_C)
    _check_header(reading, root, len(items), as_of_date)
    for num, item in enumerate(items, start=1):
        dims = {dim.get("prop"): (dim.text or "").strip() for dim in item.iterfind("c:Dim", NS_C)}
        _read_item(reading, num, dims, config)
    return reading
