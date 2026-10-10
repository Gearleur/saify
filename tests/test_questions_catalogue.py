"""Besoin 2 : requêtes du catalogue, chiffres vérifiés contre un oracle calculé à la main (NOTES.md)."""

import hashlib
import sqlite3
from datetime import date
from decimal import Decimal

import pytest

from reco.domaine.questions.base import connexion_lecture_seule
from reco.domaine.questions.catalogue import encours_valorise
from tests.fabrique import DONNEES, db_modifiee

BASE = DONNEES / "orsay.db"
ARRETE = date(2026, 9, 25)

# Oracle à la main. Obligations : nominal × cours / 100 (pas × valeur_nominale), pied de coupon.
ENCOURS_OBL = Decimal("724836.00")
ENCOURS_ACT = Decimal("167647000.00")
ENCOURS_PAT = Decimal("256448170.50")


# Garantie client : « personne ne doit pouvoir modifier l'inventaire par ce biais ».
@pytest.mark.parametrize(
    "requete",
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
def test_base_refuse_toute_ecriture(requete):
    empreinte = hashlib.sha256(BASE.read_bytes()).hexdigest()
    with connexion_lecture_seule(BASE) as db, pytest.raises(sqlite3.DatabaseError):
        db.execute(requete)
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == empreinte


def test_base_autorise_la_lecture():
    with connexion_lecture_seule(BASE) as db:
        assert db.execute("SELECT count(*) FROM positions").fetchone()[0] == 29


def test_encours_obl_oracle():
    reponse = encours_valorise(BASE, "OBL", ARRETE)
    (total,) = reponse.chiffres
    assert total.valeur == ENCOURS_OBL
    assert total.unite == "EUR"
    assert "ORSAY OBLIGATIONS" in reponse.reponse and "724 836,00 EUR" in reponse.reponse
    assert "25/09/2026" in reponse.reponse  # date de référence toujours affichée
    assert len(reponse.lignes_sources) == 10
    assert any("pied de coupon" in a for a in reponse.avertissements)


def test_obligation_valorisee_en_pourcentage_du_nominal():
    reponse = encours_valorise(BASE, "OBL", ARRETE)
    afd = next(ligne for ligne in reponse.lignes_sources if ligne.valeurs["isin"] == "FR0000015927")
    assert afd.valeurs["valorisation"] == "242500.00"  # 250 000 × 97,00 % ; pas 242 500 000


def test_encours_actions_oracle():
    (total,) = encours_valorise(BASE, "ACT", ARRETE).chiffres
    assert total.valeur == ENCOURS_ACT


def test_encours_tous_fonds():
    reponse = encours_valorise(BASE, None, ARRETE)
    valeurs = {c.libelle: c.valeur for c in reponse.chiffres}
    assert valeurs["ORSAY OBLIGATIONS"] == ENCOURS_OBL
    assert valeurs["ORSAY ACTIONS EUROPE"] == ENCOURS_ACT
    assert valeurs["ORSAY PATRIMOINE"] == ENCOURS_PAT
    assert valeurs["Total des 3 fonds"] == ENCOURS_OBL + ENCOURS_ACT + ENCOURS_PAT


def test_requete_sql_exposee_est_celle_executee():
    reponse = encours_valorise(BASE, "OBL", ARRETE)
    assert reponse.requete_sql.lstrip().upper().startswith("SELECT")
    with connexion_lecture_seule(BASE) as db:
        lignes = db.execute(reponse.requete_sql, reponse.parametres_sql).fetchall()
    assert len(lignes) == len(reponse.lignes_sources)


def test_cours_manquant_jamais_valorise_a_zero(tmp_path):
    base = db_modifiee(
        tmp_path, "DELETE FROM cours WHERE isin = 'FR0000015927' AND date_cours = '2026-09-25'"
    )
    reponse = encours_valorise(base, "OBL", ARRETE)
    (total,) = reponse.chiffres
    assert "partiel" in total.libelle.lower()
    assert total.valeur == ENCOURS_OBL - Decimal("242500.00")
    assert reponse.confiance == "basse"
    assert any("FR0000015927" in a and "cours" in a for a in reponse.avertissements)


def test_mode_de_cotation_inconnu_jamais_devine(tmp_path):
    base = db_modifiee(
        tmp_path, "UPDATE titres SET mode_cotation = 'AUTRE' WHERE isin = 'FR0000015927'"
    )
    reponse = encours_valorise(base, "OBL", ARRETE)
    assert reponse.confiance == "basse"
    assert any("mode de cotation" in a for a in reponse.avertissements)


def test_fonds_sans_position():
    reponse = encours_valorise(BASE, "OBL", date(2026, 9, 24))
    assert reponse.chiffres == []
    assert reponse.confiance == "basse"
    assert "aucune position" in reponse.reponse.lower()
