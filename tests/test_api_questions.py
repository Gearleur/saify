"""Besoin 2, étape 2.4 : POST /api/questions (JSON et flux SSE) et encadrement de l'usage du LLM."""

import base64
import json
import threading

import pytest
from fastapi.testclient import TestClient

from middle_office.api import create_app
from middle_office.api.services.llm import ClientEncadre
from middle_office.domaine.questions.comprehension import MODELE, IntentionLLM, LLMIndisponible
from tests.fabrique import FauxClient, fichiers


def _client(**surcharges) -> TestClient:
    surcharges.setdefault("fichier_historique", None)
    surcharges.setdefault("client_llm", None)
    return TestClient(create_app(**surcharges))


def _intention(intention="ENCOURS", fonds="OBL", confiance=0.95) -> IntentionLLM:
    return IntentionLLM(intention=intention, fonds=fonds, horizon_mois=None, titre=None,
                        confiance=confiance, reformulations=[])  # fmt: skip


def _poser(client: TestClient, question: str):
    return client.post("/api/questions", json={"question": question})


def test_question_encours_json():
    reponse = _poser(_client(), "Encours valorisé du fonds OBL")
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["chiffres"][0] == {
        "libelle": "Encours valorisé",
        "valeur": "724836.00",
        "unite": "EUR",
    }
    assert corps["requete_sql"].startswith("SELECT") and corps["parametres_sql"]["fonds"] == "OBL"
    assert corps["comprehension"]["source"] == "mots_cles"
    assert corps["question"] == "Encours valorisé du fonds OBL"
    assert len(corps["lignes_sources"]) == 10 and corps["confiance"] == "haute"


def test_vigilances_exposees():
    corps = _poser(_client(), "Concentration par émetteur du fonds PAT").json()
    assert corps["vigilances"][0]["emetteurs"] == ["Kering"]
    assert corps["vigilances"][0]["valeur"] == "87.54"


def test_hors_catalogue_et_lecture_seule():
    corps = _poser(_client(), "Supprime la position LVMH").json()
    assert corps["chiffres"] == [] and "lecture seule" in corps["reponse"]
    assert 2 <= len(corps["reformulations"]) <= 3


def test_origine_suspens_lit_le_dernier_rapprochement():
    client = _client()
    assert "lancez" in _poser(client, "D'où vient le suspens sur SCHNEIDER ?").json()["reponse"]
    id_ = client.post("/api/rapprochements/exemple").json()["id"]
    corps = _poser(client, "D'où vient le suspens sur SCHNEIDER ?").json()
    assert id_ in corps["reponse"] and corps["chiffres"][0]["valeur"] == "25000"


def test_origine_suspens_apres_un_rapprochement_bloque():
    """Reproduit en revue : le dernier rapprochement bloqué faisait répondre « aucun suspens »."""
    client = _client()
    id_ok = client.post("/api/rapprochements/exemple").json()["id"]
    sans_c = [{"nom": n, "contenu_b64": base64.b64encode(b).decode()}
              for n, b in fichiers().items() if not n.startswith("depositaire_C")]  # fmt: skip
    id_bloque = client.post("/api/rapprochements", json={"fichiers": sans_c}).json()["id"]
    corps = _poser(client, "D'où vient le suspens sur FR0000051641 ?").json()
    assert "aucun suspens" not in corps["reponse"].lower()
    assert id_ok in corps["reponse"] and "SFIL" in corps["reponse"]
    assert corps["confiance"] == "basse"
    assert any(id_bloque in a for a in corps["avertissements"])


@pytest.mark.parametrize(
    "corps",
    [
        {"question": "a"},
        {"question": "x" * 501},
        {"question": "Encours OBL", "modele": "claude-opus-5-5"},
        {},
    ],
)
def test_entree_invalide_422(corps):
    reponse = _client().post("/api/questions", json=corps)
    assert reponse.status_code == 422 and reponse.json()["erreur"]["code"] == "VALIDATION"


def test_rate_limit_dedie_aux_questions():
    client = _client(limite_questions=2)
    assert [_poser(client, "Encours OBL").status_code for _ in range(3)] == [200, 200, 429]
    assert (
        client.post("/api/rapprochements/exemple").status_code == 201
    )  # les autres routes ne sont pas touchées


def _evenements(texte: str) -> list[tuple[str, dict]]:
    evenements = []
    for bloc in texte.strip().split("\n\n"):
        lignes = dict(ligne.split(": ", 1) for ligne in bloc.splitlines())
        evenements.append((lignes["event"], json.loads(lignes["data"])))
    return evenements


def test_flux_sse_etapes_puis_reponse():
    client = _client()
    reponse = client.post("/api/questions/flux", json={"question": "Encours valorisé du fonds OBL"})
    assert reponse.status_code == 200
    assert reponse.headers["content-type"].startswith("text/event-stream")
    assert reponse.headers["cache-control"] == "no-cache"
    evenements = _evenements(reponse.text)
    assert [nom for nom, _ in evenements] == ["etape", "comprehension", "etape", "reponse", "fin"]
    assert evenements[1][1]["intention"] == "ENCOURS"
    assert evenements[3][1] == _poser(client, "Encours valorisé du fonds OBL").json()


def test_flux_valide_l_entree_avant_de_streamer():
    assert _client().post("/api/questions/flux", json={"question": ""}).status_code == 422


# Encadrement de la clé API : budget, cache, concurrence, modèle imposé.
def test_llm_utilise_quand_disponible():
    faux = FauxClient(_intention())
    corps = _poser(_client(client_llm=faux), "Combien pèse le fonds obligataire ?").json()
    assert (
        corps["comprehension"]["source"] == "llm" and corps["chiffres"][0]["valeur"] == "724836.00"
    )


def test_question_identique_servie_par_le_cache():
    faux = FauxClient(_intention())
    client = _client(client_llm=faux)
    for _ in range(3):
        assert (
            _poser(client, "Combien pèse le fonds obligataire ?").json()["comprehension"]["source"]
            == "llm"
        )
    assert len(faux.appels) == 1


def test_budget_quotidien_epuise_repli_mots_cles():
    faux = FauxClient(_intention())
    client = _client(client_llm=faux, llm_budget_jour=1)
    _poser(client, "Combien pèse le fonds obligataire ?")
    corps = _poser(client, "Encours valorisé du fonds OBL").json()
    assert (
        corps["comprehension"]["source"] == "mots_cles"
        and "budget" in corps["comprehension"]["detail"]
    )
    assert len(faux.appels) == 1


def test_concurrence_bornee():
    encadre = ClientEncadre(FauxClient(_intention()), budget_jour=10, concurrence=1, timeout=5.0)
    occupe = threading.Event()
    encadre._places.acquire()  # une question déjà en cours
    with pytest.raises(LLMIndisponible, match="simultanées"):
        encadre.messages.parse(model=MODELE, max_tokens=1024, system="s", messages=[{"role": "user", "content": "q"}], output_format=IntentionLLM)  # fmt: skip
    encadre._places.release()
    assert not occupe.is_set()


def test_modele_impose():
    encadre = ClientEncadre(FauxClient(_intention()), budget_jour=10, concurrence=1, timeout=5.0)
    with pytest.raises(LLMIndisponible, match="modèle"):
        encadre.messages.parse(model="claude-opus-5-5", max_tokens=1024, system="s", messages=[], output_format=IntentionLLM)  # fmt: skip


def test_sante_expose_l_etat_du_llm_jamais_la_cle(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "cle-factice-de-test-0000")
    faux = FauxClient(_intention())
    client = _client(client_llm=faux, llm_budget_jour=50)
    _poser(client, "Combien pèse le fonds obligataire ?")
    sante = client.get("/api/sante")
    llm = sante.json()["llm"]
    assert llm == {"actif": True, "modele": MODELE, "appels_aujourdhui": 1, "budget_jour": 50}
    for route in ("/api/sante", "/api/parametrage"):
        assert "cle-factice-de-test-0000" not in client.get(route).text
    assert "cle-factice-de-test-0000" not in _poser(client, "Encours OBL").text


def test_sans_llm_sante_le_dit():
    assert _client().get("/api/sante").json()["llm"]["actif"] is False


def test_chaque_question_laisse_une_ligne_d_audit_sans_la_question(caplog):
    caplog.set_level("INFO", logger="middle_office.api")
    client = _client()
    question = "Encours valorisé du fonds OBL"
    reponse = client.post(
        "/api/questions", json={"question": question}, headers={"X-Request-ID": "rid-audit-1"}
    )
    client.post(
        "/api/questions/flux", json={"question": question}, headers={"X-Request-ID": "rid-audit-2"}
    )
    audits = [r.getMessage() for r in caplog.records if r.getMessage().startswith("audit question")]
    assert len(audits) == 2
    assert "rid=rid-audit-1" in audits[0] and "rid=rid-audit-2" in audits[1]
    assert (
        "intention=ENCOURS source=mots_cles" in audits[0]
        and "reponse=haute chiffres=1" in audits[0]
    )
    assert all(question not in a for a in audits)
    assert reponse.status_code == 200
