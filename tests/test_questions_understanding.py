"""Besoin 2, étape 2.3 : comprendre la question (LLM ou mots-clés), seuil de confiance, reformulations.

Aucun appel réseau : un faux client simule Claude Haiku 5.5, ses réponses et ses pannes.
"""

from datetime import date
from decimal import Decimal

import anthropic
import httpx2
import pytest

from middle_office.domain.questions.models import ReconciliationContext
from middle_office.domain.questions.refusal import CONFIDENCE_THRESHOLD
from middle_office.domain.questions.understanding import (
    LlmIntent,
    answer_question,
    execute,
    understand,
)
from tests.factory import DATA_DIR, FakeClient

DB_PATH = DATA_DIR / "orsay.db"
AS_OF = date(2026, 9, 25)


def _llm(
    intent: str,
    fund=None,
    horizon_months=None,
    security=None,
    confidence=0.95,
    suggestions=(),
    requested_date=None,
):
    return LlmIntent.model_validate(
        {
            "intent": intent,
            "fund": fund,
            "horizon_months": horizon_months,
            "security": security,
            "confidence": confidence,
            "suggestions": list(suggestions),
            "requested_date": requested_date,
        }
    )


# Repli sans LLM : les 5 questions de l'énoncé sont reconnues par mots-clés.
@pytest.mark.parametrize(
    "question, intent, fund",
    [
        ("Encours valorisé du fonds OBL au cours de clôture", "ENCOURS", "OBL"),
        ("Quelles sont les tombées d'échéances à venir ?", "ECHEANCES", None),
        ("Concentration par émetteur d'Orsay Patrimoine", "CONCENTRATION", "PAT"),
        ("Quelles opérations ne sont pas encore dénouées ?", "NON_DENOUEES", None),
        ("D'où vient le suspens sur SCHNEIDER ?", "ORIGINE_SUSPENS", None),
    ],
)
def test_mots_cles_questions_de_l_enonce(question, intent, fund):
    c = understand(question, DB_PATH, client=None)
    assert (c.intent, c.fund, c.source) == (intent, fund, "mots_cles")
    assert c.confidence >= CONFIDENCE_THRESHOLD


def test_mots_cles_horizon_en_mois_et_en_ans():
    assert understand("échéances dans les 3 mois", DB_PATH, client=None).horizon_months == 3
    assert (
        understand("tombées d'échéance sur 2 ans pour OBL", DB_PATH, client=None).horizon_months
        == 24
    )


def test_titre_resolu_en_isin():
    assert understand("origine du suspens SCHNEIDER", DB_PATH, client=None).isin == "FR0000012965"
    assert understand("suspens fr0000999914 ?", DB_PATH, client=None).isin == "FR0000999914"


def test_question_hors_catalogue_attention_et_reformulations():
    answer = answer_question("Quel temps fera-t-il demain ?", DB_PATH, AS_OF, client=None)
    assert answer.figures == [] and answer.confidence == "basse"
    assert answer.answer.startswith("Attention")
    assert 2 <= len(answer.suggestions) <= 3


def test_deux_intentions_melangees_attention():
    answer = answer_question("encours et échéances de OBL", DB_PATH, AS_OF, client=None)
    assert answer.figures == [] and answer.answer.startswith("Attention")


def test_concentration_sans_fonds_demande_de_preciser():
    answer = answer_question("concentration par émetteur", DB_PATH, AS_OF, client=None)
    assert answer.figures == [] and answer.answer.startswith("Attention")
    assert any("OBL" in r for r in answer.suggestions)


# Chemin LLM : Haiku 5.5 ne fait que classer ; les chiffres viennent toujours du catalogue.
def test_llm_classe_puis_catalogue_calcule():
    client = FakeClient(_llm("ENCOURS", fund="OBL"))
    answer = answer_question("Combien pèse le fonds obligataire ?", DB_PATH, AS_OF, client=client)
    assert answer.figures[0].value == Decimal("724836.00")
    assert answer.understanding["source"] == "llm"
    call = client.calls[0]
    assert call["model"] == "claude-haiku-5-5" and call["output_format"] is LlmIntent
    # Rien de la base n'est envoyé au LLM : seulement la question.
    assert "724" not in str(call["messages"]) and "FR0000" not in str(call["system"])


def test_llm_peu_sur_de_lui_attention():
    client = FakeClient(
        _llm("ENCOURS", confidence=0.4, suggestions=["Encours de OBL ?", "Encours de ACT ?"])
    )
    answer = answer_question("ça vaut combien ?", DB_PATH, AS_OF, client=client)
    assert answer.figures == [] and answer.answer.startswith("Attention")
    assert answer.suggestions == ["Encours de OBL ?", "Encours de ACT ?"]


def test_llm_en_panne_repli_mots_cles():
    failure = anthropic.APIConnectionError(
        request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    )
    answer = answer_question(
        "Encours valorisé du fonds OBL", DB_PATH, AS_OF, client=FakeClient(error=failure)
    )
    assert answer.figures[0].value == Decimal("724836.00")
    assert answer.understanding["source"] == "mots_cles"
    assert "indisponible" in answer.understanding["detail"]


def test_llm_refus_repli_mots_cles():
    client = FakeClient(None, stop_reason="refusal")
    answer = answer_question("Opérations non dénouées", DB_PATH, AS_OF, client=client)
    assert answer.understanding["source"] == "mots_cles"
    assert answer.figures[0].value == 2


def test_question_et_comprehension_tracees_dans_la_reponse():
    answer = answer_question("Échéances à venir dans les 3 mois", DB_PATH, AS_OF, client=None)
    assert answer.question == "Échéances à venir dans les 3 mois"
    assert answer.understanding == {
        "intent": "ECHEANCES",
        "fund": None,
        "horizon_months": 3,
        "isin": None,
        "source": "mots_cles",
        "confidence": answer.understanding["confidence"],
        "detail": "",
        "requested_date": None,
    }


def test_origine_suspens_utilise_le_dernier_rapprochement():
    breaks = [
        {
            "id": "S6",
            "isin": "FR0000012965",
            "fund": "ACT",
            "entity": "ORSAY ACTIONS EUROPE",
            "security_name": "SCHNEIDER",
            "custodian": "A",
            "type": "QTE",
            "break_type_label": "Quantité différente",
            "pms_qty": "250000",
            "custodian_qty": "225000",
            "difference": "25000",
            "action": "Vérifier",
            "lead": "",
            "flags": [],
            "sources": ["positions_internes.csv:21"],
        }
    ]
    answer = answer_question(
        "Pourquoi un suspens sur SCHNEIDER ?",
        DB_PATH,
        AS_OF,
        client=None,
        context=ReconciliationContext("r_123abc", "2026-09-25", breaks),
    )
    assert "r_123abc" in answer.answer and answer.figures[0].value == Decimal("25000")


# Corrections issues de l'essai réel avec Haiku 5.5 (NOTES.md).
def test_date_de_reference_donnee_au_llm():
    client = FakeClient(_llm("ECHEANCES", horizon_months=3))
    answer_question(
        "Qu'est-ce qui arrive à maturité d'ici la fin de l'année ?", DB_PATH, AS_OF, client=client
    )
    assert "25/09/2026" in client.calls[0]["system"]


@pytest.mark.parametrize(
    "question",
    ["Supprime la position LVMH", "Modifie la quantité de SCHNEIDER", "Ajoute 100 titres Kering"],
)
def test_demande_d_ecriture_refusee_explicitement(question):
    answer = answer_question(
        question, DB_PATH, AS_OF, client=FakeClient(_llm("HORS_CATALOGUE", confidence=0.9))
    )
    assert answer.figures == [] and "lecture seule" in answer.answer


def test_hors_catalogue_bien_compris_message_honnete():
    client = FakeClient(
        _llm("HORS_CATALOGUE", fund="PAT", confidence=0.9, suggestions=["Encours du fonds PAT"])
    )
    answer = answer_question("Performance YTD du fonds PAT", DB_PATH, AS_OF, client=client)
    assert answer.answer.startswith("Attention") and "pas sûr d'avoir compris" not in answer.answer
    assert "ne sais pas" in answer.answer


def test_hors_catalogue_prime_sur_la_confiance_basse():
    client = FakeClient(_llm("HORS_CATALOGUE", confidence=0.2))
    assert (
        "ne sais pas"
        in answer_question("Performance YTD du fonds PAT", DB_PATH, AS_OF, client=client).answer
    )


def test_reformulations_du_llm_verifiees_contre_le_catalogue():
    proposed = [
        "Hors catalogue : explication générale d'un écart",
        "Encours valorisé du fonds PAT",
    ]
    client = FakeClient(_llm("ENCOURS", confidence=0.4, suggestions=proposed))
    answer = answer_question("ça vaut combien ?", DB_PATH, AS_OF, client=client)
    assert answer.suggestions == ["Encours valorisé du fonds PAT"]


# Revue de code : ne jamais répondre à côté de la question (un vrai chiffre, mais d'une autre question).
@pytest.mark.parametrize(
    ("question", "isin"),
    [
        ("D'où vient le suspens sur SFIL ?", "FR0000051641"),  # nom court d'une obligation
        ("suspens sur l'Unédic", "FR0000014813"),  # émetteur, avec accent
        ("suspens OAT 2,5% 2030", "FR0000010001"),  # libellé complet, virgule décimale
        ("suspens sur EDF", "FR0000011488"),
    ],
)
def test_titre_reconnu_par_son_nom_court(question, isin):
    assert understand(question, DB_PATH, client=None).isin == isin


def test_titre_ambigu_on_demande_de_preciser():
    c = understand("D'où vient le suspens sur l'OAT ?", DB_PATH, client=None)
    assert c.isin is None and len(c.candidate_securities) == 4
    answer = execute(c, "D'où vient le suspens sur l'OAT ?", DB_PATH, AS_OF)
    assert answer.figures == [] and "plusieurs titres" in answer.answer
    assert all("OAT" in r for r in answer.suggestions)


def test_mot_courant_n_est_pas_un_titre():
    for question in (
        "Encours valorisé du fonds OBL",
        "Concentration par émetteur de PAT",
        "Opérations en attente de règlement-livraison",
    ):
        assert understand(question, DB_PATH, client=None).candidate_securities == []
        assert understand(question, DB_PATH, client=None).isin is None


@pytest.mark.parametrize(
    "question",
    [
        "Encours valorisé du fonds OBL au 01/01/2025 ?",
        "Encours du fonds OBL hier",
        "Concentration par émetteur de PAT au 2025-12-31",
        "Opérations non dénouées la semaine dernière",
        "Encours valorisé d'OBL au 1er janvier 2026",
    ],
)
def test_autre_date_que_la_reference_pas_de_chiffre(question):
    """Reproduit en revue : « au 01/01/2025 » recevait l'encours du 25/09/2026."""
    answer = answer_question(question, DB_PATH, AS_OF, client=None)
    assert answer.figures == [] and answer.confidence == "basse"
    assert "25/09/2026" in answer.answer and answer.suggestions


def test_date_de_reference_citee_on_repond():
    answer = answer_question(
        "Encours valorisé du fonds OBL au 25/09/2026", DB_PATH, AS_OF, client=None
    )
    assert answer.figures[0].value == Decimal("724836.00")


def test_date_du_llm_aussi_controlee():
    client = FakeClient(_llm("ENCOURS", fund="OBL", requested_date="2025-12-31"))
    answer = answer_question(
        "Combien pesait le fonds obligataire fin 2025 ?", DB_PATH, AS_OF, client=client
    )
    assert answer.figures == [] and answer.understanding["requested_date"] == "2025-12-31"


def test_encours_d_un_titre_refuse():
    """Reproduit en revue : « Encours de LVMH » recevait le total des 3 fonds."""
    answer = answer_question("Encours valorisé de LVMH ?", DB_PATH, AS_OF, client=None)
    assert answer.figures == [] and "par fonds" in answer.answer


def test_operations_non_denouees_filtrees_par_titre():
    answer = answer_question("Opérations non dénouées sur SAFRAN", DB_PATH, AS_OF, client=None)
    assert answer.figures[0].value == 1 and "FR0000016297" in answer.answer
    assert answer.sql_params["isin"] == "FR0000016297"


def test_echeance_d_un_titre_sans_borne_de_fin():
    """Sans horizon, « quand tombe EDF ? » ne doit pas répondre « aucune » parce que c'est en 2031."""
    answer = answer_question("Quelle est l'échéance de EDF ?", DB_PATH, AS_OF, client=None)
    assert answer.figures[0].value == 1 and "10/07/2031" in answer.answer


def test_echeances_jusqu_a_une_date_deviennent_un_horizon():
    answer = answer_question("Tombées d'échéances d'ici le 31/12/2026", DB_PATH, AS_OF, client=None)
    assert answer.understanding["requested_date"] == "2026-12-31"
    assert answer.sql_params["end"] == "2026-12-31"  # la date citée, pas un horizon arrondi
    assert "BTF" in answer.answer


@pytest.mark.parametrize(
    "question", ["Corrige l'encours du fonds OBL", "Peux-tu supprimer le suspens sur SCHNEIDER ?"]
)
def test_ordre_d_ecriture_refuse_meme_dans_le_catalogue(question):
    answer = answer_question(question, DB_PATH, AS_OF, client=None)
    assert answer.figures == [] and "lecture seule" in answer.answer


def test_lecture_d_operations_annulees_n_est_pas_une_ecriture():
    answer = answer_question("Opérations non dénouées ou annulées ?", DB_PATH, AS_OF, client=None)
    assert "lecture seule" not in answer.answer
