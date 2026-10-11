"""Comparaison PMS ↔ conservateurs à la maille (fonds, ISIN, conservateur), tolérance nulle.

Une clé présente d'un seul côté est un suspens ; attendu chez X et livré chez Y, c'est un seul DEP.
"""

from collections import defaultdict
from decimal import Decimal

from middle_office.domain.reconciliation.breaks import Break
from middle_office.domain.reconciliation.sources import Position


def aggregate(positions: list[Position]) -> dict[tuple[str, str, str], list[Position]]:
    groups: dict[tuple[str, str, str], list[Position]] = defaultdict(list)
    for p in positions:
        groups[(p.entity, p.isin, p.custodian)].append(p)
    return groups


def compare(pms: list[Position], custodian_positions: list[Position]) -> list[Break]:
    """Jointure complète : une clé présente d'un seul côté est un suspens (sinon LVMH serait raté)."""
    pms_side, custodian_side = aggregate(pms), aggregate(custodian_positions)
    breaks = []
    for key in sorted(pms_side.keys() | custodian_side.keys()):
        pms_group, dep_group = pms_side.get(key, []), custodian_side.get(key, [])
        # Une position nulle est une absence : pas de suspens « ABS_DEP » pour 0 titre.
        pms_total = sum((p.quantity for p in pms_group), Decimal(0)) or None
        dep_qty = sum((p.quantity for p in dep_group), Decimal(0)) or None
        if pms_total == dep_qty:  # tolérance nulle : une seule unité d'écart est un suspens
            continue
        type_ = "ABS_DEP" if dep_qty is None else "ABS_INT" if pms_total is None else "QTE"
        entity, isin, custodian = key
        label = next((p.label for p in pms_group + dep_group if p.label), "")
        sources = [p.ref for p in pms_group + dep_group]
        breaks.append(Break(entity, isin, custodian, type_, pms_total, dep_qty, label, sources))
    return breaks


def merge_dep(breaks: list[Break]) -> list[Break]:
    """Attendu chez X, livré chez Y : un seul suspens DEP (énoncé), même si les quantités diffèrent.

    Plusieurs candidats (2 conservateurs possibles) : on ne devine pas, on signale sur chaque suspens.
    """
    by_security: dict[tuple[str, str], list[Break]] = defaultdict(list)
    for s in breaks:
        if s.type in ("ABS_DEP", "ABS_INT"):
            by_security[(s.entity, s.isin)].append(s)
    for group in by_security.values():
        absent = [s for s in group if s.type == "ABS_DEP"]
        found = [s for s in group if s.type == "ABS_INT"]
        if not absent or not found:
            continue
        if len(absent) == 1 and len(found) == 1:
            x, y = absent[0], found[0]
            breaks = [s for s in breaks if s is not x and s is not y]
            breaks.append(
                Break(
                    x.entity,
                    x.isin,
                    f"{x.custodian}→{y.custodian}",
                    "DEP",
                    x.pms_qty,
                    y.custodian_qty,
                    x.security_name or y.security_name,
                    x.sources + y.sources,
                )
            )
        else:
            message = (
                f"DEP ambigu : absent chez {', '.join(s.custodian for s in absent)}, "
                f"trouvé chez {', '.join(s.custodian for s in found)} : à trancher par l'opérateur"
            )
            for s in group:
                s.flag("DEP_AMBIGU", message)
    return breaks


def custodians_by_security(positions: list[Position]) -> dict[tuple[str, str], set[str]]:
    """(entité, ISIN) -> conservateurs qui le détiennent (quantité non nulle), pour juger une piste :
    `mouvements` ne dit pas chez quel conservateur une opération se dénoue."""
    result: dict[tuple[str, str], set[str]] = defaultdict(set)
    for p in positions:
        if p.quantity:
            result[(p.entity, p.isin)].add(p.custodian)
    return result
