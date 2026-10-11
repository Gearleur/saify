"""Ce que orsay.db apporte au rapprochement, à titre d'information : codes fonds, référentiel et
opérations en attente, qui donnent la piste de chaque suspens. Elle informe, elle ne décide pas.
"""

import sqlite3
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import NamedTuple

from middle_office.domain.formats import date_fr, format_quantity
from middle_office.domain.management_db import read_only_connection
from middle_office.domain.reconciliation.breaks import Break
from middle_office.domain.reconciliation.sources import Anomaly, ClientConfig, is_valid_isin


class Movement(NamedTuple):
    id: int
    settlement_date: date
    portfolio: str
    isin: str
    side: str
    quantity: Decimal

    @property
    def signed_quantity(self) -> Decimal:
        """Effet sur PMS − conservateur tant que l'opération n'est pas dénouée."""
        return self.quantity if self.side == "ACHAT" else -self.quantity


@dataclass
class DbContext:
    """Ce qu'on lit dans orsay.db, à titre d'information uniquement."""

    fund_codes: dict[str, str] = field(default_factory=dict)
    reference_data: dict[str, str] | None = None  # None : référentiel indisponible
    pending: list[Movement] = field(default_factory=list)


def read_db_context(db_path: Path | None, cleaning_log: list[Anomaly]) -> DbContext:
    try:
        if db_path is None:
            raise sqlite3.OperationalError("aucune base fournie")
        with read_only_connection(db_path) as db:
            return DbContext(
                fund_codes=dict(db.execute("SELECT nom, code FROM portefeuilles")),
                reference_data=dict(db.execute("SELECT isin, libelle FROM titres")),
                pending=[
                    Movement(i, date.fromisoformat(d), pf, isin, side, Decimal(q))
                    for i, d, pf, isin, side, q in db.execute(
                        "SELECT id, date_denouement, portefeuille, isin, sens, quantite"
                        " FROM mouvements WHERE statut = 'EN_ATTENTE' ORDER BY id"
                    )
                ],
            )
    except sqlite3.Error as error:
        cleaning_log.append(
            Anomaly(
                "orsay.db",
                0,
                "SIGNALE",
                "BASE_INDISPONIBLE",
                str(db_path),
                "",
                f"orsay.db illisible ({error}) : suspens sans code fonds ni piste",
            )
        )
        return DbContext()


def lead(
    movements: list[Movement], difference: Decimal, several_custodians: bool
) -> tuple[str, str]:
    """Cite les opérations en attente et dit, calcul signé à l'appui, si elles expliquent l'écart.

    Renvoie (libellé pour l'opérateur, explication parmi EXPLICATIONS).
    """
    if not movements:
        return "", "aucune"
    trades = ", ".join(
        f"op. n°{m.id} {m.side} {format_quantity(m.quantity)} dén. {date_fr(m.settlement_date)}"
        for m in movements
    )
    net = sum((m.signed_quantity for m in movements), Decimal(0))
    if net == difference:
        explanation, verdict = "totale", "écart entièrement expliqué"
    elif net * difference > 0 and abs(net) < abs(difference):
        explanation = "partielle"
        verdict = f"écart partiellement expliqué, reste {format_quantity(difference - net)}"
    else:
        explanation, verdict = "contraire", "n'explique pas l'écart"
    if several_custodians:  # mouvements n'indique pas le conservateur
        verdict += " (explication possible seulement : titre détenu chez plusieurs conservateurs)"
    return f"{trades} → {verdict}", explanation


def complete(
    breaks: list[Break],
    config: ClientConfig,
    db_info: DbContext,
    as_of_date: date,
    custodians: dict[tuple[str, str], set[str]],
) -> None:
    for s in breaks:
        s.fund = db_info.fund_codes.get(s.entity, "")
        s.break_type_label, s.action = config.break_types[s.type]
        if s.type == "DEP" and s.difference:
            s.action += (
                f" ; puis {config.break_types['QTE'][1]} (écart {format_quantity(s.difference)})"
            )
        if not s.security_name and db_info.reference_data:
            s.security_name = db_info.reference_data.get(s.isin, "")
        movements = [m for m in db_info.pending if m.portfolio == s.fund and m.isin == s.isin]
        several = sorted(custodians[(s.entity, s.isin)])
        s.lead, s.explanation = lead(movements, s.difference, len(several) > 1)
        if movements and len(several) > 1:
            s.flag(
                "PISTE_MULTI_CONSERVATEURS",
                f"piste à vérifier : titre détenu chez plusieurs conservateurs ({', '.join(several)}),"
                " l'opération peut concerner l'autre",
            )
        for m in movements:
            if m.settlement_date <= as_of_date:
                s.flag(
                    "CSDR",
                    f"op. n°{m.id} non dénouée au {date_fr(m.settlement_date)} : "
                    "défaut de règlement-livraison, risque CSDR",
                )
        if not is_valid_isin(s.isin):
            s.flag("ISIN_INVALIDE", "ISIN à clé invalide, probable erreur de saisie")
