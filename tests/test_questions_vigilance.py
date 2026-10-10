"""Règles de vigilance sur la concentration : seuils internes simples et modifiables, jamais un verdict réglementaire."""

from datetime import date
from decimal import Decimal

from middle_office.domaine.questions.catalogue import concentration_emetteurs
from middle_office.domaine.questions.vigilance import REGLES_PAR_DEFAUT, ReglesVigilance
from tests.fabrique import DONNEES

BASE = DONNEES / "orsay.db"
ARRETE = date(2026, 9, 25)


def _alertes(reponse) -> dict[str, list[str]]:
    return {v.code: v.emetteurs for v in reponse.vigilances}


def test_regles_par_defaut_lisibles():
    assert REGLES_PAR_DEFAUT.seuil_emetteur == Decimal("10")
    assert REGLES_PAR_DEFAUT.seuil_cumul_individuel == Decimal("5")
    assert REGLES_PAR_DEFAUT.plafond_cumul == Decimal("40")
    assert len(REGLES_PAR_DEFAUT.description()) == 2


def test_obl_emetteurs_au_dessus_de_10_pourcent():
    reponse = concentration_emetteurs(BASE, "OBL", ARRETE)
    assert _alertes(reponse)["EMETTEUR_AU_DESSUS_DU_SEUIL"] == [
        "Agence française de développement", "Caisse des dépôts", "SFIL", "BPCE",
    ]  # fmt: skip


def test_obl_cumul_calcule_sur_valeurs_exactes():
    reponse = concentration_emetteurs(BASE, "OBL", ARRETE)
    cumul = next(v for v in reponse.vigilances if v.code == "CUMUL_AU_DESSUS_DU_PLAFOND")
    # 89,34 % sur les montants exacts ; additionner les % arrondis donnerait 89,35 %.
    assert cumul.valeur == Decimal("89.34")
    assert "EDF" in cumul.emetteurs and "Unédic" not in cumul.emetteurs  # 5,48 % compte, 4,89 % non


def test_pat_kering():
    reponse = concentration_emetteurs(BASE, "PAT", ARRETE)
    assert _alertes(reponse)["EMETTEUR_AU_DESSUS_DU_SEUIL"] == ["Kering"]
    assert any("Kering" in v.message and "87,54 %" in v.message for v in reponse.vigilances)


def test_jamais_un_verdict_reglementaire():
    reponse = concentration_emetteurs(BASE, "OBL", ARRETE)
    for v in reponse.vigilances:
        assert "seuil de vigilance interne" in v.message
        assert "non conforme" not in v.message.lower() and "infraction" not in v.message.lower()


def test_seuils_modifiables():
    regles = ReglesVigilance(seuil_emetteur=Decimal("30"), seuil_cumul_individuel=Decimal("5"), plafond_cumul=Decimal("95"))  # fmt: skip
    reponse = concentration_emetteurs(BASE, "OBL", ARRETE, regles)
    assert _alertes(reponse) == {
        "EMETTEUR_AU_DESSUS_DU_SEUIL": ["Agence française de développement"]
    }


def test_aucune_alerte_sous_les_seuils():
    regles = ReglesVigilance(seuil_emetteur=Decimal("90"), seuil_cumul_individuel=Decimal("5"), plafond_cumul=Decimal("100"))  # fmt: skip
    assert concentration_emetteurs(BASE, "PAT", ARRETE, regles).vigilances == []
