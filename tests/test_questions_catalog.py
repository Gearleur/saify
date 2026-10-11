"""Besoin 2 : requêtes du catalogue, chiffres vérifiés contre un oracle calculé à la main (NOTES.md)."""

import hashlib
import sqlite3
from datetime import date
from decimal import Decimal

import pytest

from middle_office.domain.management_db import read_only_connection
from middle_office.domain.questions.catalog import (
    break_origin,
    fund_valuation,
    issuer_concentration,
    maturities,
    unsettled_trades,
)
from middle_office.domain.questions.models import ReconciliationContext
from tests.factory import DATA_DIR, modified_db

DB_PATH = DATA_DIR / "orsay.db"
AS_OF = date(2026, 9, 25)

# Oracle à la main. Obligations : nominal × cours / 100 (pas × valeur_nominale), pied de coupon.
VALUATION_OBL = Decimal("724836.00")
VALUATION_ACT = Decimal("167647000.00")
VALUATION_PAT = Decimal("256448170.50")


# Garantie client : « personne ne doit pouvoir modifier l'inventaire par ce biais ».
@pytest.mark.parametrize(
    "query",
    [
        "DELETE FROM positions",
        "UPDATE positions SET quantite = 0",
        "INSERT INTO cours VALUES ('X', '2026-09-25', 1)",
        "DROP TABLE titres",
        "CREATE TABLE pirate (x)",
        "ATTACH DATABASE ':memory:' AS autre",
        "PRAGMA query_only = OFF",
    ],
)
def test_base_refuse_toute_ecriture(query):
    fingerprint = hashlib.sha256(DB_PATH.read_bytes()).hexdigest()
    with read_only_connection(DB_PATH) as db, pytest.raises(sqlite3.DatabaseError):
        db.execute(query)
    assert hashlib.sha256(DB_PATH.read_bytes()).hexdigest() == fingerprint


def test_base_autorise_la_lecture():
    with read_only_connection(DB_PATH) as db:
        assert db.execute("SELECT count(*) FROM positions").fetchone()[0] == 29


def test_encours_obl_oracle():
    answer = fund_valuation(DB_PATH, "OBL", AS_OF)
    (total,) = answer.figures
    assert total.value == VALUATION_OBL
    assert total.unit == "EUR"
    assert "ORSAY OBLIGATIONS" in answer.answer and "724 836,00 EUR" in answer.answer
    assert "25/09/2026" in answer.answer  # date de référence toujours affichée
    assert len(answer.source_rows) == 10
    assert any("pied de coupon" in a for a in answer.warnings)


def test_obligation_valorisee_en_pourcentage_du_nominal():
    answer = fund_valuation(DB_PATH, "OBL", AS_OF)
    afd = next(line for line in answer.source_rows if line.values["isin"] == "FR0000015927")
    assert afd.values["valorisation"] == "242500.00"  # 250 000 × 97,00 % ; pas 242 500 000


def test_encours_actions_oracle():
    (total,) = fund_valuation(DB_PATH, "ACT", AS_OF).figures
    assert total.value == VALUATION_ACT


def test_encours_tous_fonds():
    answer = fund_valuation(DB_PATH, None, AS_OF)
    values = {c.label: c.value for c in answer.figures}
    assert values["ORSAY OBLIGATIONS"] == VALUATION_OBL
    assert values["ORSAY ACTIONS EUROPE"] == VALUATION_ACT
    assert values["ORSAY PATRIMOINE"] == VALUATION_PAT
    assert values["Total des 3 fonds"] == VALUATION_OBL + VALUATION_ACT + VALUATION_PAT


def test_requete_sql_exposee_est_celle_executee():
    answer = fund_valuation(DB_PATH, "OBL", AS_OF)
    assert answer.sql_query.lstrip().upper().startswith("SELECT")
    with read_only_connection(DB_PATH) as db:
        lines = db.execute(answer.sql_query, answer.sql_params).fetchall()
    assert len(lines) == len(answer.source_rows)


def test_cours_manquant_jamais_valorise_a_zero(tmp_path):
    db_path = modified_db(
        tmp_path, "DELETE FROM cours WHERE isin = 'FR0000015927' AND date_cours = '2026-09-25'"
    )
    answer = fund_valuation(db_path, "OBL", AS_OF)
    (total,) = answer.figures
    assert "partiel" in total.label.lower()
    assert total.value == VALUATION_OBL - Decimal("242500.00")
    assert answer.confidence == "basse"
    assert any("FR0000015927" in a and "cours" in a for a in answer.warnings)


def test_mode_de_cotation_inconnu_jamais_devine(tmp_path):
    db_path = modified_db(
        tmp_path, "UPDATE titres SET mode_cotation = 'AUTRE' WHERE isin = 'FR0000015927'"
    )
    answer = fund_valuation(db_path, "OBL", AS_OF)
    assert answer.confidence == "basse"
    assert any("mode de cotation" in a for a in answer.warnings)


def test_fonds_sans_position():
    answer = fund_valuation(DB_PATH, "OBL", date(2026, 9, 24))
    assert answer.figures == []
    assert answer.confidence == "basse"
    assert "aucune position" in answer.answer.lower()


# 2.2 : échéances, concentration, opérations non dénouées, origine d'un suspens.
def test_echeances_12_mois_par_defaut():
    answer = maturities(DB_PATH, None, AS_OF)
    assert [line.values["isin"] for line in answer.source_rows] == [
        "FR0000011116",
        "FR0000010373",
    ]
    values = {c.label: c.value for c in answer.figures}
    assert values["Tombées d'échéance"] == 2
    assert values["Nominal remboursé"] == Decimal("45000")
    assert "25/09/2027" in answer.answer  # borne de l'horizon affichée
    assert any("12 mois" in a for a in answer.warnings)


def test_echeances_horizon_et_fonds():
    assert [
        line.values["isin"]
        for line in maturities(DB_PATH, None, AS_OF, horizon_months=3).source_rows
    ] == ["FR0000011116"]
    assert [line.values["isin"] for line in maturities(DB_PATH, "OBL", AS_OF).source_rows] == [
        "FR0000010373"
    ]


def test_aucune_echeance_est_une_reponse_fiable():
    answer = maturities(DB_PATH, "ACT", AS_OF)
    assert answer.source_rows == [] and answer.confidence == "haute"
    assert "aucune" in answer.answer.lower()


def test_concentration_obl():
    answer = issuer_concentration(DB_PATH, "OBL", AS_OF)
    first = answer.figures[0]
    assert first.label == "Agence française de développement"
    assert first.value == Decimal("33.46") and first.unit == "%"
    assert len(answer.figures) == 10  # 10 émetteurs distincts dans OBL
    assert any("ratios réglementaires" in a for a in answer.warnings)


def test_concentration_regroupe_par_emetteur():
    answer = issuer_concentration(DB_PATH, "PAT", AS_OF)
    values = {c.label: c.value for c in answer.figures}
    assert values["Kering"] == Decimal("87.54")
    assert values["République française"] == Decimal("0.03")  # 4 lignes d'État regroupées


def test_concentration_exige_un_fonds():
    answer = issuer_concentration(DB_PATH, None, AS_OF)
    assert answer.figures == [] and answer.confidence == "basse"


def test_operations_non_denouees():
    answer = unsettled_trades(DB_PATH, None, AS_OF)
    assert [line.values["id"] for line in answer.source_rows] == ["19", "20"]
    assert answer.figures[0].value == 2
    amounts = {line.values["id"]: line.values["montant"] for line in answer.source_rows}
    assert amounts == {"19": "10948000.00", "20": "217730.00"}
    assert "CSDR" not in answer.answer


def test_operation_non_denouee_en_retard_signale_csdr(tmp_path):
    db_path = modified_db(
        tmp_path, "UPDATE mouvements SET date_denouement = '2026-09-24' WHERE id = 19"
    )
    answer = unsettled_trades(db_path, None, AS_OF)
    assert "CSDR" in answer.answer
    assert any("n°19" in a and "CSDR" in a for a in answer.warnings)


SCHNEIDER_BREAK = {
    "id": "S6",
    "priority": "en_attente",
    "fund": "ACT",
    "entity": "ORSAY ACTIONS EUROPE",
    "isin": "FR0000012965",
    "security_name": "SCHNEIDER",
    "custodian": "A",
    "type": "QTE",
    "break_type_label": "Quantité différente",
    "pms_qty": "250000",
    "custodian_qty": "225000",
    "difference": "25000",
    "action": "Vérifier les opérations de la veille non dénouées",
    "lead": "op. n°19 ACHAT 25 000 dén. 26/09/2026 → écart entièrement expliqué",
    "flags": [],
    "sources": ["positions_internes.csv:21", "depositaire_A_20260925.xlsx:7"],
}


def _context(*breaks, blocked=None) -> ReconciliationContext:
    return ReconciliationContext("r_abc123", "2026-09-25", list(breaks), blocked)


def test_origine_suspens():
    answer = break_origin(DB_PATH, "FR0000012965", _context(SCHNEIDER_BREAK))
    assert "SCHNEIDER" in answer.answer and "r_abc123 (arrêté du 25/09/2026)" in answer.answer
    assert answer.figures[0].value == Decimal("25000")
    tables = [line.table for line in answer.source_rows]
    assert "positions_internes.csv:21" in tables and "mouvements" in tables


def test_origine_suspens_absent():
    answer = break_origin(DB_PATH, "FR0000010001", _context(SCHNEIDER_BREAK))
    assert "aucun suspens" in answer.answer.lower() and answer.confidence == "haute"


def test_origine_suspens_sans_rapprochement():
    answer = break_origin(DB_PATH, "FR0000012965", None)
    assert answer.confidence == "basse" and "rapprochement" in answer.answer.lower()


def test_origine_suspens_dit_qu_un_rapprochement_plus_recent_est_bloque():
    answer = break_origin(DB_PATH, "FR0000010001", _context(SCHNEIDER_BREAK, blocked="r_bloque"))
    assert answer.confidence == "basse"
    assert any("r_bloque" in a and "bloqué" in a for a in answer.warnings)


def test_origine_suspens_seul_rapprochement_bloque():
    context = ReconciliationContext(None, newer_blocked="r_bloque")
    answer = break_origin(DB_PATH, "FR0000012965", context)
    assert "r_bloque" in answer.answer and "aucun suspens" not in answer.answer.lower()


def test_origine_suspens_cite_les_mouvements_de_chaque_fonds(tmp_path):
    """Un même ISIN en suspens dans deux fonds : les mouvements des deux sont cités, pas du premier seul."""
    db_path = modified_db(
        tmp_path,
        "INSERT INTO mouvements VALUES (99, '2026-09-24', '2026-09-26', 'PAT',"
        " 'FR0000012965', 'VENTE', 100, 400, 'X', 'EN_ATTENTE')",
    )
    pat = {**SCHNEIDER_BREAK, "id": "S7", "fund": "PAT", "entity": "ORSAY PATRIMOINE"}
    answer = break_origin(db_path, "FR0000012965", _context(SCHNEIDER_BREAK, pat))
    lines = [line.values for line in answer.source_rows if line.table == "mouvements"]
    assert sorted(m["portefeuille"] for m in lines) == ["ACT", "PAT"]
