"""Oracle : les 7 suspens calculés à la main (NOTES.md, « Résultat attendu »)."""

from decimal import Decimal
from pathlib import Path

from reco import rapprocher_dossier

DONNEES = Path(__file__).resolve().parents[1] / "data" / "donnees"

ATTENDU = {
    ("ACT", "FR0000012965", "A", "QTE", Decimal(250000), Decimal(225000)),
    ("ACT", "FR0000016297", "B", "QTE", Decimal(40000), Decimal(41000)),
    ("OBL", "FR0000051641", "C", "QTE", Decimal(100000), Decimal(50000)),
    ("OBL", "FR0000011488", "A", "ABS_DEP", Decimal(40000), None),
    ("OBL", "FR0000012966", "A", "ABS_DEP", Decimal(7000), None),
    ("OBL", "FR0000015927", "A→B", "DEP", Decimal(250000), Decimal(250000)),
    ("OBL", "FR0000999914", "B", "ABS_INT", None, Decimal(30000)),
}


def test_sept_suspens_exacts():
    resultat = rapprocher_dossier(DONNEES)
    obtenu = {
        (s.fonds, s.isin, s.conservateur, s.type, s.qte_pms, s.qte_dep) for s in resultat.suspens
    }
    assert obtenu == ATTENDU


def test_action_lue_dans_le_parametrage():
    resultat = rapprocher_dossier(DONNEES)
    dep = next(s for s in resultat.suspens if s.type == "DEP")
    assert dep.action == "Corriger le référentiel dépositaire"


def test_piste_mouvement_en_attente():
    resultat = rapprocher_dossier(DONNEES)
    pistes = {s.isin: s.piste for s in resultat.suspens}
    assert "ACHAT 25000" in pistes["FR0000012965"] and "26/09" in pistes["FR0000012965"]
    assert "VENTE 1000" in pistes["FR0000016297"]
    assert pistes["FR0000051641"] == ""


def test_trois_exclusions_tracees():
    resultat = rapprocher_dossier(DONNEES)
    exclus = [a for a in resultat.journal if a.niveau == "EXCLU"]
    assert {a.regle for a in exclus} == {"SANS_SOUS_COMPTE", "P3G", "ANNULATION_S"}
    assert len(exclus) == 3
