"""Un test par piège : fichiers altérés en mémoire, niveau attendu dans le journal."""

import pytest

from middle_office.domaine.rapprochement.sources import isin_valide
from tests.fabrique import (
    PMS,
    B,
    C,
    fichiers,
    lancer,
    parametrage_modifie,
    regles,
    remplacer,
    xlsx_a,
)


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
    assert any("clé invalide" in g.message for g in suspens.signalements)


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
            "DATE_ARRETE",  # rien n'est lu hors namespace : date introuvable, donc pas AUCUNE_LIGNE
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
    assert all(a.remede for a in resultat.journal if a.niveau == "BLOQUANT")


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


# Revue étape 2 : une donnée ne sort pas de nulle part, et ne disparaît pas sans trace.
def test_ligne_a_vide_ignoree():
    resultat = lancer(fichiers(a=xlsx_a(ajouter=[None, None, " ", None])))
    assert resultat.statut == "OK"


def test_ligne_a_incomplete_bloquante():
    resultat = lancer(fichiers(a=xlsx_a(ajouter=[None, "FR0000010001", "OAT 2.5% 2030", "1 000"])))
    assert "LIGNE_INCOMPLETE" in regles(resultat, "BLOQUANT")


def test_ligne_b_vide_ignoree():
    resultat = lancer(fichiers(b=remplacer(B, ("T000013", "\r\nT000013"))))
    assert resultat.statut == "OK"


def test_ligne_b_type_inconnu_bloquante():
    resultat = lancer(
        fichiers(b=remplacer(B, ("T000013", "XORAFR0000014078000000001000000\r\nT000013")))
    )
    assert "TYPE_LIGNE_INCONNU" in regles(resultat, "BLOQUANT")


def test_isin_vide_pms_bloquant():
    resultat = lancer(fichiers(pms=remplacer(PMS, (" fr0000014078 ", ""))))
    assert "LIGNE_INCOMPLETE" in regles(resultat, "BLOQUANT")


def test_valeur_vide_c_bloquante():
    resultat = lancer(fichiers(c=remplacer(C, ('"CODE_ISIN">FR0000050007', '"CODE_ISIN">'))))
    assert "CHAMP_MANQUANT" in regles(resultat, "BLOQUANT")


@pytest.mark.parametrize("quantite", ["10.000", "-10000"])
def test_quantite_non_entiere_ou_negative_signalee(quantite):
    resultat = lancer(fichiers(pms=remplacer(PMS, (";VINCI;10000;", f";VINCI;{quantite};"))))
    assert resultat.statut == "OK"
    assert "QUANTITE_SUSPECTE" in regles(resultat, "SIGNALE")


def test_parametrage_type_manquant_bloquant(tmp_path):
    def retirer_dep(ws):
        ws.delete_rows(next(c.row for c in ws["A"] if c.value == "DEP"))

    param = parametrage_modifie(tmp_path, "TYPES_ECARTS", retirer_dep)
    resultat = lancer(fichiers(), param=param)
    assert resultat.statut == "BLOQUE"
    assert "PARAMETRAGE" in regles(resultat, "BLOQUANT")


def test_parametrage_transco_contradictoire_bloquante(tmp_path):
    param = parametrage_modifie(
        tmp_path, "TRANSCO_SOUS_COMPTES", lambda ws: ws.append(["SC-PAT-01", "ORSAY OBLIGATIONS"])
    )
    resultat = lancer(fichiers(), param=param)
    assert "PARAMETRAGE" in regles(resultat, "BLOQUANT")


def test_bloquant_dit_quoi_faire():
    resultat = lancer(
        fichiers(pms=remplacer(PMS, ("SC-OBL-01;FR0000011488", "SC-XXX-01;FR0000011488")))
    )
    (transco,) = [a for a in resultat.journal if a.regle == "TRANSCO"]
    assert "SC-XXX-01" in transco.remede and "TRANSCO_SOUS_COMPTES" in transco.remede


def test_encodage_latin1_trace():
    texte = (remplacer(PMS, (";VINCI;", ";VINCI É;"))).decode()
    resultat = lancer(fichiers(pms=texte.encode("latin-1")))
    assert resultat.statut == "OK"
    assert "ENCODAGE" in regles(resultat, "NORMALISE")


def test_entete_csv_incomplete_bloquante():
    resultat = lancer(fichiers(pms=remplacer(PMS, (";quantite;", ";qte;"))))
    (format_,) = [a for a in resultat.journal if a.regle == "FORMAT"]
    assert "quantite" in format_.motif
