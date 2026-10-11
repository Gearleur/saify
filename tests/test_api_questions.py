"""Besoin 2, étape 2.4 : POST /api/questions (JSON et flux SSE) et encadrement de l'usage du LLM."""

import base64
import json
import threading

import pytest
from fastapi.testclient import TestClient

from middle_office.api import create_app
from middle_office.api.services.llm import GuardedClient
from middle_office.domain.questions.understanding import MODEL, LlmIntent, LlmUnavailable
from tests.factory import FakeClient, files


def _client(**overrides) -> TestClient:
    overrides.setdefault("history_file", None)
    overrides.setdefault("llm_client", None)
    return TestClient(create_app(**overrides))


def _intent(intent="ENCOURS", fund="OBL", confidence=0.95) -> LlmIntent:
    # model_validate : les littéraux (intention, fonds) sont vérifiés comme pour une vraie sortie du LLM.
    return LlmIntent.model_validate(
        {
            "intent": intent,
            "fund": fund,
            "horizon_months": None,
            "security": None,
            "confidence": confidence,
            "suggestions": [],
        }
    )


def _ask(client: TestClient, question: str):
    return client.post("/api/questions", json={"question": question})


def test_question_encours_json():
    answer = _ask(_client(), "Encours valorisé du fonds OBL")
    assert answer.status_code == 200
    body = answer.json()
    assert body["figures"][0] == {
        "label": "Encours valorisé",
        "value": "724836.00",
        "unit": "EUR",
    }
    assert body["sql_query"].startswith("SELECT") and body["sql_params"]["fund"] == "OBL"
    assert body["understanding"]["source"] == "mots_cles"
    assert body["question"] == "Encours valorisé du fonds OBL"
    assert len(body["source_rows"]) == 10 and body["confidence"] == "haute"


def test_vigilances_exposees():
    body = _ask(_client(), "Concentration par émetteur du fonds PAT").json()
    assert body["vigilances"][0]["issuers"] == ["Kering"]
    assert body["vigilances"][0]["value"] == "87.54"


def test_hors_catalogue_et_lecture_seule():
    body = _ask(_client(), "Supprime la position LVMH").json()
    assert body["figures"] == [] and "lecture seule" in body["answer"]
    assert 2 <= len(body["suggestions"]) <= 3


def test_origine_suspens_lit_le_dernier_rapprochement():
    client = _client()
    assert "lancez" in _ask(client, "D'où vient le suspens sur SCHNEIDER ?").json()["answer"]
    id_ = client.post("/api/reconciliations/sample").json()["id"]
    body = _ask(client, "D'où vient le suspens sur SCHNEIDER ?").json()
    assert id_ in body["answer"] and body["figures"][0]["value"] == "25000"


def test_origine_suspens_apres_un_rapprochement_bloque():
    """Reproduit en revue : le dernier rapprochement bloqué faisait répondre « aucun suspens »."""
    client = _client()
    ok_id = client.post("/api/reconciliations/sample").json()["id"]
    without_c = [
        {"name": n, "content_b64": base64.b64encode(b).decode()}
        for n, b in files().items()
        if not n.startswith("depositaire_C")
    ]
    blocked_id = client.post("/api/reconciliations", json={"files": without_c}).json()["id"]
    body = _ask(client, "D'où vient le suspens sur FR0000051641 ?").json()
    assert "aucun suspens" not in body["answer"].lower()
    assert ok_id in body["answer"] and "SFIL" in body["answer"]
    assert body["confidence"] == "basse"
    assert any(blocked_id in a for a in body["warnings"])


@pytest.mark.parametrize(
    "body",
    [
        {"question": "a"},
        {"question": "x" * 501},
        {"question": "Encours OBL", "model": "claude-opus-5-5"},
        {},
    ],
)
def test_entree_invalide_422(body):
    answer = _client().post("/api/questions", json=body)
    assert answer.status_code == 422 and answer.json()["error"]["code"] == "VALIDATION"


def test_rate_limit_dedie_aux_questions():
    client = _client(question_limit=2)
    assert [_ask(client, "Encours OBL").status_code for _ in range(3)] == [200, 200, 429]
    assert (
        client.post("/api/reconciliations/sample").status_code == 201
    )  # les autres routes ne sont pas touchées


def _events(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def test_flux_sse_etapes_puis_reponse():
    client = _client()
    answer = client.post(
        "/api/questions/stream", json={"question": "Encours valorisé du fonds OBL"}
    )
    assert answer.status_code == 200
    assert answer.headers["content-type"].startswith("text/event-stream")
    assert answer.headers["cache-control"] == "no-cache"
    events = _events(answer.text)
    assert [name for name, _ in events] == ["step", "understanding", "step", "answer", "end"]
    assert events[1][1]["intent"] == "ENCOURS"
    assert events[3][1] == _ask(client, "Encours valorisé du fonds OBL").json()


def test_flux_valide_l_entree_avant_de_streamer():
    assert _client().post("/api/questions/stream", json={"question": ""}).status_code == 422


# Encadrement de la clé API : budget, cache, concurrence, modèle imposé.
def test_llm_utilise_quand_disponible():
    fake = FakeClient(_intent())
    body = _ask(_client(llm_client=fake), "Combien pèse le fonds obligataire ?").json()
    assert body["understanding"]["source"] == "llm" and body["figures"][0]["value"] == "724836.00"


def test_question_identique_servie_par_le_cache():
    fake = FakeClient(_intent())
    client = _client(llm_client=fake)
    for _ in range(3):
        assert (
            _ask(client, "Combien pèse le fonds obligataire ?").json()["understanding"]["source"]
            == "llm"
        )
    assert len(fake.calls) == 1


def test_budget_quotidien_epuise_repli_mots_cles():
    fake = FakeClient(_intent())
    client = _client(llm_client=fake, llm_daily_budget=1)
    _ask(client, "Combien pèse le fonds obligataire ?")
    body = _ask(client, "Encours valorisé du fonds OBL").json()
    assert (
        body["understanding"]["source"] == "mots_cles"
        and "budget" in body["understanding"]["detail"]
    )
    assert len(fake.calls) == 1


def test_concurrence_bornee():
    guarded = GuardedClient(FakeClient(_intent()), daily_budget=10, concurrency=1)
    busy = threading.Event()
    guarded._slots.acquire()  # une question déjà en cours
    with pytest.raises(LlmUnavailable, match="simultanées"):
        guarded.messages.parse(
            model=MODEL,
            max_tokens=1024,
            system="s",
            messages=[{"role": "user", "content": "q"}],
            output_format=LlmIntent,
        )
    guarded._slots.release()
    assert not busy.is_set()


def test_modele_impose():
    guarded = GuardedClient(FakeClient(_intent()), daily_budget=10, concurrency=1)
    with pytest.raises(LlmUnavailable, match="modèle"):
        guarded.messages.parse(
            model="claude-opus-5-5",
            max_tokens=1024,
            system="s",
            messages=[],
            output_format=LlmIntent,
        )


def test_sante_expose_l_etat_du_llm_jamais_la_cle(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "cle-factice-de-test-0000")
    fake = FakeClient(_intent())
    client = _client(llm_client=fake, llm_daily_budget=50)
    _ask(client, "Combien pèse le fonds obligataire ?")
    health = client.get("/api/health")
    llm = health.json()["llm"]
    assert llm == {"enabled": True, "model": MODEL, "calls_today": 1, "daily_budget": 50}
    for route in ("/api/health", "/api/client-config"):
        assert "cle-factice-de-test-0000" not in client.get(route).text
    assert "cle-factice-de-test-0000" not in _ask(client, "Encours OBL").text


def test_sans_llm_sante_le_dit():
    assert _client().get("/api/health").json()["llm"]["enabled"] is False


def test_chaque_question_laisse_une_ligne_d_audit_sans_la_question(caplog):
    caplog.set_level("INFO", logger="middle_office.api")
    client = _client()
    question = "Encours valorisé du fonds OBL"
    answer = client.post(
        "/api/questions", json={"question": question}, headers={"X-Request-ID": "rid-audit-1"}
    )
    client.post(
        "/api/questions/stream",
        json={"question": question},
        headers={"X-Request-ID": "rid-audit-2"},
    )
    audits = [r.getMessage() for r in caplog.records if r.getMessage().startswith("audit question")]
    assert len(audits) == 2
    assert "rid=rid-audit-1" in audits[0] and "rid=rid-audit-2" in audits[1]
    assert (
        "intention=ENCOURS source=mots_cles" in audits[0]
        and "reponse=haute chiffres=1" in audits[0]
    )
    assert all(question not in a for a in audits)
    assert answer.status_code == 200
