"""Règles de vigilance sur la concentration : seuils internes, modifiables, jamais un verdict réglementaire."""

from datetime import date
from decimal import Decimal

from middle_office.domain.questions.catalog import issuer_concentration
from middle_office.domain.questions.vigilance import DEFAULT_RULES, VigilanceRules
from tests.factory import DATA_DIR

DB_PATH = DATA_DIR / "orsay.db"
AS_OF = date(2026, 9, 25)


def _alerts(answer) -> dict[str, list[str]]:
    return {v.code: v.issuers for v in answer.vigilances}


def test_regles_par_defaut_lisibles():
    assert DEFAULT_RULES.issuer_threshold == Decimal("10")
    assert DEFAULT_RULES.individual_threshold == Decimal("5")
    assert DEFAULT_RULES.cumulative_cap == Decimal("40")
    assert len(DEFAULT_RULES.description()) == 2


def test_obl_emetteurs_au_dessus_de_10_pourcent():
    answer = issuer_concentration(DB_PATH, "OBL", AS_OF)
    assert _alerts(answer)["EMETTEUR_AU_DESSUS_DU_SEUIL"] == [
        "Agence française de développement",
        "Caisse des dépôts",
        "SFIL",
        "BPCE",
    ]


def test_obl_cumul_calcule_sur_valeurs_exactes():
    answer = issuer_concentration(DB_PATH, "OBL", AS_OF)
    cumulative = next(v for v in answer.vigilances if v.code == "CUMUL_AU_DESSUS_DU_PLAFOND")
    # 89,34 % sur les montants exacts ; additionner les % arrondis donnerait 89,35 %.
    assert cumulative.value == Decimal("89.34")
    assert (
        "EDF" in cumulative.issuers and "Unédic" not in cumulative.issuers
    )  # 5,48 % compte, 4,89 % non


def test_pat_kering():
    answer = issuer_concentration(DB_PATH, "PAT", AS_OF)
    assert _alerts(answer)["EMETTEUR_AU_DESSUS_DU_SEUIL"] == ["Kering"]
    assert any("Kering" in v.message and "87,54 %" in v.message for v in answer.vigilances)


def test_jamais_un_verdict_reglementaire():
    answer = issuer_concentration(DB_PATH, "OBL", AS_OF)
    for v in answer.vigilances:
        assert "seuil de vigilance interne" in v.message
        assert "non conforme" not in v.message.lower() and "infraction" not in v.message.lower()


def test_seuils_modifiables():
    rules = VigilanceRules(
        issuer_threshold=Decimal("30"),
        individual_threshold=Decimal("5"),
        cumulative_cap=Decimal("95"),
    )
    answer = issuer_concentration(DB_PATH, "OBL", AS_OF, rules)
    assert _alerts(answer) == {"EMETTEUR_AU_DESSUS_DU_SEUIL": ["Agence française de développement"]}


def test_aucune_alerte_sous_les_seuils():
    rules = VigilanceRules(
        issuer_threshold=Decimal("90"),
        individual_threshold=Decimal("5"),
        cumulative_cap=Decimal("100"),
    )
    assert issuer_concentration(DB_PATH, "PAT", AS_OF, rules).vigilances == []
