"""Besoin 2, étape 2.3 : comprendre la question (LLM ou mots-clés), seuil de confiance, reformulations.

Aucun appel réseau : un faux client simule Claude Haiku 5.5, ses réponses et ses pannes.
"""

from datetime import date
from decimal import Decimal

import anthropic
import httpx2
import pytest

from middle_office.domaine.questions.comprehension import (
    SEUIL_CONFIANCE,
    IntentionLLM,
    comprendre,
    repondre,
)
from tests.fabrique import DONNEES, FauxClient

BASE = DONNEES / "orsay.db"
ARRETE = date(2026, 9, 25)


def _llm(
    intention: str, fonds=None, horizon_mois=None, titre=None, confiance=0.95, reformulations=()
):
    return IntentionLLM(intention=intention, fonds=fonds, horizon_mois=horizon_mois, titre=titre,
                        confiance=confiance, reformulations=list(reformulations))  # fmt: skip


# Repli sans LLM : les 5 questions de l'énoncé sont reconnues par mots-clés.
@pytest.mark.parametrize(
    "question, intention, fonds",
    [
        ("Encours valorisé du fonds OBL au cours de clôture", "ENCOURS", "OBL"),
        ("Quelles sont les tombées d'échéances à venir ?", "ECHEANCES", None),
        ("Concentration par émetteur d'Orsay Patrimoine", "CONCENTRATION", "PAT"),
        ("Quelles opérations ne sont pas encore dénouées ?", "NON_DENOUEES", None),
        ("D'où vient le suspens sur SCHNEIDER ?", "ORIGINE_SUSPENS", None),
    ],
)
def test_mots_cles_questions_de_l_enonce(question, intention, fonds):
    c = comprendre(question, BASE, client=None)
    assert (c.intention, c.fonds, c.source) == (intention, fonds, "mots_cles")
    assert c.confiance >= SEUIL_CONFIANCE


def test_mots_cles_horizon_en_mois_et_en_ans():
    assert comprendre("échéances dans les 3 mois", BASE, client=None).horizon_mois == 3
    assert comprendre("tombées d'échéance sur 2 ans pour OBL", BASE, client=None).horizon_mois == 24


def test_titre_resolu_en_isin():
    assert comprendre("origine du suspens SCHNEIDER", BASE, client=None).isin == "FR0000012965"
    assert comprendre("suspens fr0000999914 ?", BASE, client=None).isin == "FR0000999914"


def test_question_hors_catalogue_attention_et_reformulations():
    reponse = repondre("Quel temps fera-t-il demain ?", BASE, ARRETE, client=None)
    assert reponse.chiffres == [] and reponse.confiance == "basse"
    assert reponse.reponse.startswith("Attention")
    assert 2 <= len(reponse.reformulations) <= 3


def test_deux_intentions_melangees_attention():
    reponse = repondre("encours et échéances de OBL", BASE, ARRETE, client=None)
    assert reponse.chiffres == [] and reponse.reponse.startswith("Attention")


def test_concentration_sans_fonds_demande_de_preciser():
    reponse = repondre("concentration par émetteur", BASE, ARRETE, client=None)
    assert reponse.chiffres == [] and reponse.reponse.startswith("Attention")
    assert any("OBL" in r for r in reponse.reformulations)


# Chemin LLM : Haiku 5.5 ne fait que classer ; les chiffres viennent toujours du catalogue.
def test_llm_classe_puis_catalogue_calcule():
    client = FauxClient(_llm("ENCOURS", fonds="OBL"))
    reponse = repondre("Combien pèse le fonds obligataire ?", BASE, ARRETE, client=client)
    assert reponse.chiffres[0].valeur == Decimal("724836.00")
    assert reponse.comprehension["source"] == "llm"
    appel = client.appels[0]
    assert appel["model"] == "claude-haiku-5-5" and appel["output_format"] is IntentionLLM
    # Rien de la base n'est envoyé au LLM : seulement la question.
    assert "724" not in str(appel["messages"]) and "FR0000" not in str(appel["system"])


def test_llm_peu_sur_de_lui_attention():
    client = FauxClient(_llm("ENCOURS", confiance=0.4, reformulations=["Encours de OBL ?", "Encours de ACT ?"]))  # fmt: skip
    reponse = repondre("ça vaut combien ?", BASE, ARRETE, client=client)
    assert reponse.chiffres == [] and reponse.reponse.startswith("Attention")
    assert reponse.reformulations == ["Encours de OBL ?", "Encours de ACT ?"]


def test_llm_en_panne_repli_mots_cles():
    panne = anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))  # fmt: skip
    reponse = repondre(
        "Encours valorisé du fonds OBL", BASE, ARRETE, client=FauxClient(erreur=panne)
    )
    assert reponse.chiffres[0].valeur == Decimal("724836.00")
    assert reponse.comprehension["source"] == "mots_cles"
    assert "indisponible" in reponse.comprehension["detail"]


def test_llm_refus_repli_mots_cles():
    client = FauxClient(None, stop_reason="refusal")
    reponse = repondre("Opérations non dénouées", BASE, ARRETE, client=client)
    assert reponse.comprehension["source"] == "mots_cles"
    assert reponse.chiffres[0].valeur == 2


def test_question_et_comprehension_tracees_dans_la_reponse():
    reponse = repondre("Échéances à venir dans les 3 mois", BASE, ARRETE, client=None)
    assert reponse.question == "Échéances à venir dans les 3 mois"
    assert reponse.comprehension == {
        "intention": "ECHEANCES", "fonds": None, "horizon_mois": 3, "isin": None,
        "source": "mots_cles", "confiance": reponse.comprehension["confiance"], "detail": "",
    }  # fmt: skip


def test_origine_suspens_utilise_le_dernier_rapprochement():
    suspens = [{"id": "S6", "isin": "FR0000012965", "fonds": "ACT", "entite": "ORSAY ACTIONS EUROPE",
                "libelle_titre": "SCHNEIDER", "conservateur": "A", "type": "QTE", "libelle_type": "Quantité différente",
                "qte_pms": "250000", "qte_dep": "225000", "ecart": "25000", "action": "Vérifier",
                "piste": "", "signalements": [], "sources": ["positions_internes.csv:21"]}]  # fmt: skip
    reponse = repondre("Pourquoi un suspens sur SCHNEIDER ?", BASE, ARRETE, client=None,
                       suspens=suspens, id_rapprochement="r_123abc")  # fmt: skip
    assert "r_123abc" in reponse.reponse and reponse.chiffres[0].valeur == Decimal("25000")


# Corrections issues de l'essai réel avec Haiku 5.5 (NOTES.md).
def test_date_de_reference_donnee_au_llm():
    client = FauxClient(_llm("ECHEANCES", horizon_mois=3))
    repondre(
        "Qu'est-ce qui arrive à maturité d'ici la fin de l'année ?", BASE, ARRETE, client=client
    )
    assert "25/09/2026" in client.appels[0]["system"]


@pytest.mark.parametrize("question", ["Supprime la position LVMH", "Modifie la quantité de SCHNEIDER", "Ajoute 100 titres Kering"])  # fmt: skip
def test_demande_d_ecriture_refusee_explicitement(question):
    reponse = repondre(
        question, BASE, ARRETE, client=FauxClient(_llm("HORS_CATALOGUE", confiance=0.9))
    )
    assert reponse.chiffres == [] and "lecture seule" in reponse.reponse


def test_hors_catalogue_bien_compris_message_honnete():
    client = FauxClient(_llm("HORS_CATALOGUE", fonds="PAT", confiance=0.9, reformulations=["Encours du fonds PAT"]))  # fmt: skip
    reponse = repondre("Performance YTD du fonds PAT", BASE, ARRETE, client=client)
    assert (
        reponse.reponse.startswith("Attention") and "pas sûr d'avoir compris" not in reponse.reponse
    )
    assert "ne sais pas" in reponse.reponse


def test_hors_catalogue_prime_sur_la_confiance_basse():
    client = FauxClient(_llm("HORS_CATALOGUE", confiance=0.2))
    assert (
        "ne sais pas"
        in repondre("Performance YTD du fonds PAT", BASE, ARRETE, client=client).reponse
    )


def test_reformulations_du_llm_verifiees_contre_le_catalogue():
    proposees = [
        "Hors catalogue : explication générale d'un écart",
        "Encours valorisé du fonds PAT",
    ]
    client = FauxClient(_llm("ENCOURS", confiance=0.4, reformulations=proposees))
    reponse = repondre("ça vaut combien ?", BASE, ARRETE, client=client)
    assert reponse.reformulations == ["Encours valorisé du fonds PAT"]
