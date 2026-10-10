"""Un test par piège : fichiers altérés en mémoire, niveau attendu dans le journal."""

import pytest

from reco.sources import isin_valide
from tests.fabrique import PMS, B, C, fichiers, lancer, regles, remplacer, xlsx_a


def test_fichiers_du_jour_non_bloques():
    resultat = lancer(fichiers())
    assert resultat.statut == "OK"
    assert regles(resultat, "BLOQUANT") == set()


def test_normalisations_tracees():
    resultat = lancer(fichiers())
    assert {
        "ISIN_FORMAT",
        "LIBELLE_CONSERVATEUR",
        "SEPARATEUR_MILLIERS",
        "DECIMALES_IMPLICITES",
        "VIRGULE_DECIMALE",
    } <= regles(resultat, "NORMALISE")
    isin = next(a for a in resultat.journal if a.regle == "ISIN_FORMAT")
    assert isin.brut == " fr0000014078 " and isin.retenu == "FR0000014078"


def test_isin_cle_invalide_signale():
    assert isin_valide("FR0000012965")
    assert not isin_valide("FR0000012966")
    resultat = lancer(fichiers())
    signales = [a for a in resultat.journal if a.regle == "ISIN_CLE_INVALIDE"]
    assert [a.retenu for a in signales] == ["FR0000012966"]
    suspens = next(s for s in resultat.suspens if s.isin == "FR0000012966")
    assert any("clé invalide" in m for m in suspens.signalements)


def test_isin_hors_referentiel_signale():
    resultat = lancer(fichiers())
    hors = {a.retenu for a in resultat.journal if a.regle == "ISIN_HORS_REFERENTIEL"}
    assert "FR0000012966" in hors


@pytest.mark.parametrize(
    "fichier, avant, apres, regle",
    [
        (
            "pms",
            "2026-09-25;SC-ACT-01; fr0000014078",
            "2026-09-24;SC-ACT-01; fr0000014078",
            "DATE_ARRETE",
        ),
        ("pms", "SC-OBL-01;FR0000011488", "SC-XXX-01;FR0000011488", "TRANSCO"),
        ("pms", ";40000;CACEIS BANK", ";4O000;CACEIS BANK", "QUANTITE_ILLISIBLE"),
        ("pms", ";5000;Euroclear\r\n", ";5000;SOCIETE GENERALE\r\n", "CONSERVATEUR_INCONNU"),
        ("b", "H20260925", "H20260924", "DATE_ARRETE"),
        ("b", "T000013", "T000012", "TOTAL_CONTROLE"),
        ("b", "DOROFR0000010373", "DXXXFR0000010373", "TRANSCO"),
        ("c", "<DateArrete>25092026", "<DateArrete>24092026", "DATE_ARRETE"),
        ("c", "<NbItems>9</NbItems>", "<NbItems>8</NbItems>", "TOTAL_CONTROLE"),
        (
            "c",
            'xmlns="urn:orsay:depositaire-c:positions:2026"',
            'xmlns="urn:autre"',
            "AUCUNE_LIGNE",
        ),
        ("c", '<Dim prop="COMPTE">ORS-PAT</Dim>', "", "CHAMP_MANQUANT"),
        ("c", "ORS-OBL", "ORS-XXX", "TRANSCO"),
    ],
)
def test_piege_bloquant(fichier, avant, apres, regle):
    nom = {"pms": PMS, "b": B, "c": C}[fichier]
    resultat = lancer(fichiers(**{fichier: remplacer(nom, (avant, apres))}))
    assert resultat.statut == "BLOQUE"
    assert regle in regles(resultat, "BLOQUANT")
    assert resultat.suspens == []


def test_a_date_arrete_bloquante():
    resultat = lancer(fichiers(a=xlsx_a(titre="RELEVE - ARRETE DU 24/09/2026")))
    assert "DATE_ARRETE" in regles(resultat, "BLOQUANT")


def test_a_quantite_illisible_bloquante():
    resultat = lancer(fichiers(a=xlsx_a(quantite="dix mille")))
    assert "QUANTITE_ILLISIBLE" in regles(resultat, "BLOQUANT")


def test_fichier_manquant_bloquant():
    depot = fichiers()
    del depot[B]
    resultat = lancer(depot)
    assert "FICHIER_MANQUANT" in regles(resultat, "BLOQUANT")


def test_libelle_different_signale_sans_bloquer():
    contenu = remplacer(C, ("DASSAULT SYSTEMES", "DASSAULT AVIATION"))
    resultat = lancer(fichiers(c=contenu))
    assert resultat.statut == "OK"
    assert "LIBELLE_DIFFERENT" in regles(resultat, "SIGNALE")
