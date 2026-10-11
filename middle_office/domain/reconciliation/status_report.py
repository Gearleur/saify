"""Restitutions texte d'un rapprochement : point de situation (à coller dans un mail) et CSV des suspens."""

import csv
import io
from collections import Counter
from decimal import Decimal
from typing import overload

from middle_office.domain.formats import format_quantity
from middle_office.domain.reconciliation.breaks import (
    PRIORITIES,
    Break,
    Result,
)

CSV_COLUMNS = (
    "priorite",
    "fonds",
    "entite",
    "isin",
    "titre",
    "conservateur",
    "type",
    "libelle_type",
    "qte_pms",
    "qte_conservateur",
    "ecart",
    "action",
    "piste",
    "signalements",
    "sources",
)
PRIORITY_TITLES = {"critique": "CRITIQUE", "a_relever": "À RELEVER", "en_attente": "EN ATTENTE"}


@overload
def quantity_text(q: Decimal) -> str: ...
@overload
def quantity_text(q: None) -> None: ...
def quantity_text(q: Decimal | None) -> str | None:
    """Écriture décimale sans exposant ni zéros inutiles (25000000 au 1/100 → « 250000 »)."""
    if q is None:
        return None
    return format(q.normalize(), "f") if q else "0"


def _qty(q: Decimal | None) -> str:
    return "—" if q is None else format_quantity(q)


def _breaks(s: Break) -> list[str]:
    lines = [
        f"- {s.fund or s.entity} · {s.isin} · {s.security_name or '(sans libellé)'} · "
        f"conservateur {s.custodian} · {s.type} ({s.break_type_label})",
        f"  PMS {_qty(s.pms_qty)} · conservateur {_qty(s.custodian_qty)} · écart {_qty(s.difference)}",
        f"  Action : {s.action}",
    ]
    if s.lead:
        lines.append(f"  Piste : {s.lead}")
    lines += [f"  ⚠ {sig.message}" for sig in s.flags]
    return lines


def build_status_report(result: Result) -> str:
    day = f"{result.as_of_date:%d/%m/%Y}" if result.as_of_date else "date d'arrêté inconnue"
    lines = [f"Point de situation · rapprochement du {day}", ""]
    if result.status == "BLOQUE":
        blocking = [a for a in result.cleaning_log if a.level == "BLOQUANT"]
        lines += [
            f"Statut : BLOQUÉ · rapprochement refusé ({len(blocking)} blocage(s)), aucun suspens "
            "calculé : un rapprochement partiel masquerait des écarts.",
            "",
            "Blocages et remèdes",
        ]
        for a in blocking:
            lines += [f"- {a.file}:{a.line} · {a.rule} · {a.reason}", f"  → {a.remedy}"]
        return "\n".join(lines) + "\n"

    by_priority = Counter(s.priority for s in result.breaks)
    lines.append(
        f"Statut : OK · {len(result.breaks)} suspens ("
        + ", ".join(f"{by_priority[p]} {PRIORITY_TITLES[p].lower()}" for p in PRIORITIES)
        + ")"
    )
    lines += ["", "Synthèse par fonds"]
    by_fund = Counter((s.fund, s.entity) for s in result.breaks)
    lines += [
        f"- {code or '?'} · {entity} : {n} suspens" for (code, entity), n in sorted(by_fund.items())
    ]
    by_custodian = Counter(s.custodian for s in result.breaks)
    lines += ["", "Synthèse par conservateur"]
    lines += [f"- {c} : {n} suspens" for c, n in sorted(by_custodian.items())]

    for p in PRIORITIES:
        group = [s for s in result.breaks if s.priority == p]
        lines += ["", f"{PRIORITY_TITLES[p]} ({len(group)})"]
        if not group:
            lines.append("- aucun")
        for s in group:
            lines += _breaks(s)

    for level, security in (("EXCLU", "Exclusions"), ("SIGNALE", "Signalements du journal")):
        anomalies = [a for a in result.cleaning_log if a.level == level]
        lines += ["", f"{security} ({len(anomalies)})"]
        lines += [f"- {a.file}:{a.line} · {a.rule} · {a.reason}" for a in anomalies] or ["- aucun"]
    return "\n".join(lines) + "\n"


def _safe_text(value: str) -> str:
    """Une cellule texte qui commence par = + - @ (ou tabulation, retour chariot) serait exécutée
    comme formule par Excel : on la préfixe d'une apostrophe (recommandation OWASP). Les libellés
    viennent des fichiers déposés, donc de l'extérieur."""
    return f"'{value}" if value[:1] in ("=", "+", "-", "@", "\t", "\r") else value


def breaks_csv(breaks: list[Break]) -> bytes:
    """`;` et BOM UTF-8 : Excel l'ouvre directement, accents compris. Les quantités sont écrites
    telles quelles (un écart négatif reste un nombre), tout le reste passe par `_texte_sur`."""
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";", lineterminator="\r\n")
    writer.writerow(CSV_COLUMNS)
    for s in breaks:
        text = [
            s.priority,
            s.fund,
            s.entity,
            s.isin,
            s.security_name,
            s.custodian,
            s.type,
            s.break_type_label,
        ]
        quantities = [
            quantity_text(s.pms_qty) or "",
            quantity_text(s.custodian_qty) or "",
            quantity_text(s.difference) or "",
        ]
        rest = [
            s.action,
            s.lead,
            " | ".join(g.message for g in s.flags),
            " | ".join(s.sources),
        ]
        writer.writerow([*map(_safe_text, text), *quantities, *map(_safe_text, rest)])
    return output.getvalue().encode("utf-8-sig")
