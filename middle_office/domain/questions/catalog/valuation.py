"""Encours valorisé et concentration par émetteur : la même valorisation ligne à ligne, au cours
de clôture de la date de référence (obligations en % du nominal, pied de coupon ; actions à l'unité).
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from middle_office.domain.formats import CENT, amount, date_fr, percentage
from middle_office.domain.management_db import decimal, read_only_connection
from middle_office.domain.questions.catalog.common import PMS_WARNING, market_value
from middle_office.domain.questions.models import (
    Answer,
    Figure,
    SourceRow,
)
from middle_office.domain.questions.vigilance import DEFAULT_RULES, VigilanceRules

SQL_VALUATION = """
SELECT p.portefeuille, f.nom, p.isin, t.libelle, t.emetteur, t.type_titre, t.mode_cotation,
       p.quantite, c.cours, c.date_cours
FROM positions p
JOIN portefeuilles f ON f.code = p.portefeuille
JOIN titres t ON t.isin = p.isin
LEFT JOIN cours c ON c.isin = p.isin AND c.date_cours = :date
WHERE p.date_arrete = :date AND (:fund IS NULL OR p.portefeuille = :fund)
ORDER BY p.portefeuille, p.isin
""".strip()


@dataclass
class _Valuation:
    """Positions valorisées ligne à ligne : base commune de l'encours et de la concentration."""

    params: dict[str, str | None]
    lines: list[tuple]
    values: list[Decimal | None]  # None : ligne non valorisée (cours absent, mode inconnu)
    sources: list[SourceRow]
    warnings: list[str]

    @property
    def excluded(self) -> int:
        return sum(v is None for v in self.values)


def _value_line(line: tuple, ref_date: date) -> tuple[Decimal | None, SourceRow, str | None]:
    """Valeur (None si non valorisable), ligne source affichée, avertissement éventuel."""
    code, _name, isin, label, issuer, security_type, mode, quantity, price, price_date = line
    qty, price = decimal(quantity), decimal(price)
    value = None if price is None else market_value(qty, price, mode)
    warning = None
    if price is None:
        warning = f"{isin} {label} : pas de cours au {date_fr(ref_date)}, ligne non valorisée"
    elif value is None:
        warning = f"{isin} {label} : mode de cotation « {mode} » inconnu, ligne non valorisée"
    source = SourceRow(
        "positions × titres × cours",
        {
            "portefeuille": code,
            "isin": isin,
            "libelle": label,
            "emetteur": issuer or "",
            "type_titre": security_type,
            "mode_cotation": mode or "",
            "quantite": str(qty),
            "cours": "" if price is None else str(price),
            "date_cours": price_date or "",
            "valorisation": "" if value is None else str(value.quantize(CENT)),
        },
    )
    return value, source, warning


def value_positions(db_path: Path, fund: str | None, ref_date: date) -> _Valuation:
    params = {"date": ref_date.isoformat(), "fund": fund}
    with read_only_connection(db_path) as db:
        lines = db.execute(SQL_VALUATION, params).fetchall()
    valued = [_value_line(line, ref_date) for line in lines]
    warnings = [a for _, _, a in valued if a]
    if any(line[6] == "POURCENTAGE" for line in lines):
        warnings.append(
            "Obligations valorisées au pied de coupon (cours en % du nominal), sans coupon couru."
        )
    warnings.append(PMS_WARNING)
    values, sources = [v for v, _, _ in valued], [s for _, s, _ in valued]
    return _Valuation(params, lines, values, sources, warnings)


def _total_by(v: _Valuation, column: int, default: str = "") -> dict[str, Decimal]:
    """Somme des lignes valorisées, regroupées par une colonne de SQL_ENCOURS (fonds, émetteur…)."""
    totals: dict[str, Decimal] = defaultdict(Decimal)
    for line, value in zip(v.lines, v.values, strict=True):
        if value is not None:
            totals[line[column] or default] += value
    return totals


def fund_valuation(db_path: Path, fund: str | None, ref_date: date) -> Answer:
    v = value_positions(db_path, fund, ref_date)
    day = date_fr(ref_date)
    if not v.lines:
        return Answer(
            f"Aucune position pour {fund or 'les fonds'} au {day} dans la base de gestion.",
            [],
            SQL_VALUATION,
            v.params,
            [],
            confidence="basse",
        )

    totals = _total_by(v, column=1)
    partial = " partiel" if v.excluded else ""
    figures = [
        Figure(f"Encours valorisé{partial}" if fund else name, total.quantize(CENT), "EUR")
        for name, total in sorted(totals.items())
    ]
    if fund is None:
        total = sum(totals.values(), Decimal(0)).quantize(CENT)
        figures.append(Figure(f"Total des {len(totals)} fonds{partial}", total, "EUR"))
        sentence = f"L'encours valorisé{partial} des {len(totals)} fonds au {day} est de {amount(total)} EUR"
    else:
        sentence = f"L'encours valorisé{partial} d'{v.lines[0][1]} au {day} est de {amount(figures[0].value)} EUR"
    sentence += f" ({len(v.lines) - v.excluded} lignes valorisées au cours de clôture du {day}"
    sentence += f", {v.excluded} non valorisées)." if v.excluded else ")."
    return Answer(
        sentence,
        figures,
        SQL_VALUATION,
        v.params,
        v.sources,
        confidence="basse" if v.excluded else "haute",
        warnings=v.warnings,
    )


def issuer_concentration(
    db_path: Path, fund: str | None, ref_date: date, rules: VigilanceRules = DEFAULT_RULES
) -> Answer:
    """Part de chaque émetteur dans l'encours valorisé d'un fonds. Chiffres bruts, sans jugement réglementaire."""
    if fund is None:
        return Answer(
            "Précisez le fonds : la concentration par émetteur se lit fonds par fonds (PAT, OBL ou ACT).",
            [],
            SQL_VALUATION,
            {"date": ref_date.isoformat(), "fund": None},
            [],
            confidence="basse",
        )
    v = value_positions(db_path, fund, ref_date)
    day = date_fr(ref_date)
    by_issuer = _total_by(v, column=4, default="Émetteur non renseigné")
    total = sum(by_issuer.values(), Decimal(0))
    if not total:
        return Answer(
            f"Aucune position valorisée pour {fund} au {day} dans la base de gestion.",
            [],
            SQL_VALUATION,
            v.params,
            v.sources,
            confidence="basse",
            warnings=v.warnings,
        )

    ranking = sorted(by_issuer.items(), key=lambda e: (-e[1], e[0]))
    figures = [
        Figure(issuer, (value / total * 100).quantize(CENT), "%") for issuer, value in ranking
    ]
    first, top_value = ranking[0]
    partial = " partiel" if v.excluded else ""
    sentence = (
        f"Premier émetteur d'{v.lines[0][1]} au {day} : {first}, {percentage(figures[0].value)} "
        f"de l'encours valorisé{partial} ({amount(top_value.quantize(CENT))} EUR sur "
        f"{amount(total.quantize(CENT))} EUR, {len(ranking)} émetteurs)."
    )
    warnings = [
        "Aucune appréciation des ratios réglementaires (5/10/40, dérogations des émetteurs publics) : "
        "chiffres bruts, à interpréter par le gérant ou le RCCI.",
        *v.warnings,
    ]
    return Answer(
        sentence,
        figures,
        SQL_VALUATION,
        v.params,
        v.sources,
        confidence="basse" if v.excluded else "haute",
        warnings=warnings,
        vigilances=rules.evaluate(ranking, total),
    )
