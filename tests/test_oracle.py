"""Oracle : les 7 suspens calculés à la main (NOTES.md, « Résultat attendu »)."""

from decimal import Decimal
from pathlib import Path

from middle_office import reconcile_folder

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "donnees"

EXPECTED = {
    ("ACT", "FR0000012965", "A", "QTE", Decimal(250000), Decimal(225000)),
    ("ACT", "FR0000016297", "B", "QTE", Decimal(40000), Decimal(41000)),
    ("OBL", "FR0000051641", "C", "QTE", Decimal(100000), Decimal(50000)),
    ("OBL", "FR0000011488", "A", "ABS_DEP", Decimal(40000), None),
    ("OBL", "FR0000012966", "A", "ABS_DEP", Decimal(7000), None),
    ("OBL", "FR0000015927", "A→B", "DEP", Decimal(250000), Decimal(250000)),
    ("OBL", "FR0000999914", "B", "ABS_INT", None, Decimal(30000)),
}


def test_sept_suspens_exacts():
    result = reconcile_folder(DATA_DIR)
    obtained = {
        (s.fund, s.isin, s.custodian, s.type, s.pms_qty, s.custodian_qty) for s in result.breaks
    }
    assert obtained == EXPECTED


def test_action_lue_dans_le_parametrage():
    result = reconcile_folder(DATA_DIR)
    custodian_positions = next(s for s in result.breaks if s.type == "DEP")
    assert custodian_positions.action == "Corriger le référentiel dépositaire"


def test_piste_mouvement_en_attente():
    result = reconcile_folder(DATA_DIR)
    leads = {s.isin: s.lead for s in result.breaks}
    assert leads["FR0000012965"].startswith("op. n°19 ACHAT 25 000 dén. 26/09/2026")
    assert leads["FR0000016297"].startswith("op. n°20 VENTE 1 000 dén. 29/09/2026")
    assert leads["FR0000051641"] == ""


def test_trois_exclusions_tracees():
    result = reconcile_folder(DATA_DIR)
    excluded = [a for a in result.cleaning_log if a.level == "EXCLU"]
    assert {a.rule for a in excluded} == {"SANS_SOUS_COMPTE", "P3G", "ANNULATION_S"}
    assert len(excluded) == 3
