"""API HTTP (docs/API.md) : contrat, garde-fous, erreurs uniformes."""

import base64
import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from middle_office.api import create_app as _create_app
from middle_office.api.config import ROOT, Settings
from tests.factory import DATA_DIR, PMS, A, B, C, files, replace_in


def create_app(**settings):
    """Historique en mémoire par défaut : les tests n'écrivent jamais dans var/."""
    return _create_app(**{"history_file": None, **settings})


SAMPLE = json.loads(
    (Path(__file__).resolve().parents[1] / "docs" / "sample_reconciliation.json").read_text()
)
ISINS = {s["isin"] for s in SAMPLE["breaks"]}


def _body(upload: dict[str, bytes] | None = None) -> dict:
    upload = files() if upload is None else upload
    return {
        "files": [
            {"name": name, "content_b64": base64.b64encode(content).decode()}
            for name, content in upload.items()
        ]
    }


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def created(client) -> dict:
    answer = client.post("/api/reconciliations", json=_body())
    assert answer.status_code == 201
    return answer.json()


def _without_id(reconciliation: dict) -> dict:
    return {k: v for k, v in reconciliation.items() if k not in ("id", "created_at")}


def _error(answer, status: int, code: str) -> dict:
    assert answer.status_code == status, answer.text
    error = answer.json()["error"]
    assert error["code"] == code
    assert set(error) == {"code", "message", "details"}
    return error


# Contrat nominal


def test_post_quatre_fichiers_egal_a_l_exemple(created):
    assert created["id"].startswith("r_") and len(created["id"]) == 8
    assert created["created_at"].endswith("Z")
    assert len(created["breaks"]) == 7
    assert _without_id(created) == _without_id(SAMPLE)


def test_exemple_sans_corps(client):
    answer = client.post("/api/reconciliations/sample")
    assert answer.status_code == 201
    assert _without_id(answer.json()) == _without_id(SAMPLE)


def test_quantites_en_chaines(created):
    for s in created["breaks"]:
        for field in ("pms_qty", "custodian_qty", "difference"):
            assert s[field] is None or isinstance(s[field], str)


def test_get_par_id_liste_et_404(client, created):
    assert client.get(f"/api/reconciliations/{created['id']}").json() == created
    second = client.post("/api/reconciliations/sample").json()
    listing = client.get("/api/reconciliations").json()
    assert [r["id"] for r in listing] == [second["id"], created["id"]]
    assert listing[1] == {
        "id": created["id"],
        "created_at": created["created_at"],
        "as_of_date": "2026-09-25",
        "status": "OK",
        "break_count": 7,
        "open_count": 5,
    }
    _error(client.get("/api/reconciliations/r_000000"), 404, "INTROUVABLE")
    _error(client.get("/api/reconciliations/r_000000/breaks.csv"), 404, "INTROUVABLE")
    _error(client.get("/api/nimporte"), 404, "INTROUVABLE")


def test_historique_borne():
    client = TestClient(create_app(history_size=2))
    ids = [client.post("/api/reconciliations/sample").json()["id"] for _ in range(3)]
    assert [r["id"] for r in client.get("/api/reconciliations").json()] == ids[:0:-1]
    _error(client.get(f"/api/reconciliations/{ids[0]}"), 404, "INTROUVABLE")


def test_csv(client, created):
    answer = client.get(f"/api/reconciliations/{created['id']}/breaks.csv")
    assert answer.status_code == 200
    assert answer.headers["content-type"].startswith("text/csv")
    assert answer.headers["content-disposition"] == 'attachment; filename="suspens_2026-09-25.csv"'
    assert answer.content.startswith(b"\xef\xbb\xbf")
    lines = answer.content.decode("utf-8-sig").splitlines()
    assert lines[0].startswith("priorite;fonds;entite;isin;titre;")
    assert len(lines) == 8


def test_point_de_situation(client, created):
    answer = client.get(f"/api/reconciliations/{created['id']}/status-report")
    assert answer.status_code == 200
    text = answer.json()["text"]
    assert text.startswith("Point de situation · rapprochement du 25/09/2026")
    assert all(isin in text for isin in ISINS)
    assert all(rule in text for rule in ("SANS_SOUS_COMPTE", "P3G", "ANNULATION_S"))


def test_sante_et_parametrage(client):
    health = client.get("/api/health").json()
    assert {k: health[k] for k in ("status", "version", "as_of_date", "db_available")} == {
        "status": "ok",
        "version": "0.3.0",
        "as_of_date": "2026-09-25",
        "db_available": True,
    }
    assert health["llm"]["enabled"] is False  # coupé dans les tests (conftest.py)
    config = client.get("/api/client-config").json()
    assert {"entity": "ORSAY OBLIGATIONS", "code": "OBL"} in config["fund"]
    assert len(config["fund"]) == 3
    assert [c["code"] for c in config["custodians"]] == ["A", "B", "C"]
    assert {t["code"] for t in config["break_types"]} == {"QTE", "ABS_DEP", "ABS_INT", "DEP"}
    assert {"key": "SC-PAT-01", "entity": "ORSAY PATRIMOINE"} in config["mappings"][
        "TRANSCO_SOUS_COMPTES"
    ]
    assert set(config["mappings"]) == {
        "TRANSCO_SOUS_COMPTES",
        "TRANSCO_DEPOSITAIRE_A",
        "TRANSCO_DEPOSITAIRE_B",
        "TRANSCO_DEPOSITAIRE_C",
    }
    assert len(config["exclusions"]) == 3


# Refus métier : 200 + BLOQUE


def test_fichier_bloquant_200_avec_remede(client):
    c = replace_in(C, ("<NbItems>9</NbItems>", "<NbItems>8</NbItems>"))
    answer = client.post("/api/reconciliations", json=_body(files(c=c)))
    assert answer.status_code == 200  # refus métier : pas une erreur HTTP (docs/API.md)
    body = answer.json()
    assert body["status"] == "BLOQUE"
    assert body["breaks"] == []
    assert body["summary"]["break_count"] == 0
    assert body["summary"]["by_priority"] == {"critique": 0, "a_relever": 0, "en_attente": 0}
    blocking = [a for a in body["cleaning_log"] if a["level"] == "BLOQUANT"]
    assert blocking and all(a["remedy"] for a in blocking)


def test_xml_doctype_bloque(client):
    c = replace_in(
        C, ("<RelevePositions", '<!DOCTYPE RelevePositions [<!ENTITY e "x">]>\n<RelevePositions')
    )
    body = client.post("/api/reconciliations", json=_body(files(c=c))).json()
    assert body["status"] == "BLOQUE"
    assert any(a["rule"] == "FORMAT" and a["level"] == "BLOQUANT" for a in body["cleaning_log"])


# Validation des entrées


def test_base64_invalide(client):
    body = _body()
    body["files"][0]["content_b64"] = "pas du base64 !"
    _error(client.post("/api/reconciliations", json=body), 422, "VALIDATION")


@pytest.mark.parametrize(
    "name",
    [
        "../positions_internes.csv",
        "dossier/depositaire_B.txt",
        "a\\b.csv",
        "positions_internes.exe",
        "",
    ],
)
def test_nom_refuse(client, name):
    body = _body({name: b"x"})
    _error(client.post("/api/reconciliations", json=body), 422, "VALIDATION")


def test_trop_de_fichiers_ou_aucun(client):
    body = _body({f"positions_internes_{i}.csv": b"x" for i in range(9)})
    _error(client.post("/api/reconciliations", json=body), 422, "VALIDATION")
    _error(client.post("/api/reconciliations", json={"files": []}), 422, "VALIDATION")


def test_validation_ne_renvoie_pas_le_contenu(client):
    error = _error(client.post("/api/reconciliations", json={"x": "SECRET"}), 422, "VALIDATION")
    assert "SECRET" not in json.dumps(error)


def test_json_illisible(client):
    answer = client.post(
        "/api/reconciliations", content=b"{pas json", headers={"content-type": "application/json"}
    )
    _error(answer, 422, "VALIDATION")


def test_fichier_non_reconnu(client):
    upload = files()
    upload["releve_inconnu.csv"] = b"x"
    error = _error(
        client.post("/api/reconciliations", json=_body(upload)), 422, "FICHIER_NON_RECONNU"
    )
    assert "depositaire_C" in error["message"]


def test_nom_de_fichier_reconnu_quelle_que_soit_la_casse(client):
    """Reproduit en revue : le front acceptait « Depositaire_A… », le back répondait 422."""
    upload = {
        name.replace("depositaire_A", "Depositaire_a").upper() if "_A_" in name else name: content
        for name, content in files().items()
    }
    answer = client.post("/api/reconciliations", json=_body(upload))
    assert answer.status_code == 201 and answer.json()["status"] == "OK"
    assert len(answer.json()["breaks"]) == 7


def test_corps_trop_gros():
    client = TestClient(create_app(max_body_size=1000))
    _error(client.post("/api/reconciliations", json=_body()), 413, "CORPS_TROP_GROS")


def test_corps_trop_gros_sans_content_length():
    client = TestClient(create_app(max_body_size=1000))

    def chunks():
        yield b'{"fichiers": ['
        yield b"x" * 2000
        yield b"]}"

    answer = client.post(
        "/api/reconciliations", content=chunks(), headers={"content-type": "application/json"}
    )
    _error(answer, 413, "CORPS_TROP_GROS")


def test_fichier_trop_gros():
    client = TestClient(create_app(max_file_size=1000))
    _error(client.post("/api/reconciliations", json=_body()), 413, "FICHIER_TROP_GROS")


# Garde-fous transverses


def test_rate_limit_post():
    client = TestClient(create_app(post_limit=2))
    for _ in range(2):
        assert client.post("/api/reconciliations", json={}).status_code == 422
    answer = client.post("/api/reconciliations", json={})
    _error(answer, 429, "RATE_LIMIT")
    assert 1 <= int(answer.headers["retry-after"]) <= 60
    assert client.get("/api/health").status_code == 200  # compteur GET séparé


def test_rate_limit_get():
    client = TestClient(create_app(get_limit=3))
    for _ in range(3):
        assert client.get("/api/health").status_code == 200
    _error(client.get("/api/health"), 429, "RATE_LIMIT")


def test_en_tetes_de_securite_et_request_id(client):
    answer = client.get("/api/health")
    assert answer.headers["content-security-policy"] == (
        "default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; "
        "img-src 'self' data:; connect-src 'self'; "
        "frame-ancestors 'none'"
    )
    assert answer.headers["x-content-type-options"] == "nosniff"
    assert answer.headers["x-frame-options"] == "DENY"
    assert answer.headers["referrer-policy"] == "no-referrer"
    assert len(answer.headers["x-request-id"]) >= 8
    reused = client.get("/api/health", headers={"X-Request-ID": "abc-123"})
    assert reused.headers["x-request-id"] == "abc-123"
    assert "x-request-id" in client.get("/api/nimporte").headers


def test_erreur_interne_sans_trace(monkeypatch):
    def failure(*_args, **_kwargs):
        raise RuntimeError("détail interne secret")

    monkeypatch.setattr("middle_office.api.services.reconciliations.reconcile", failure)
    client = TestClient(create_app(), raise_server_exceptions=False)
    answer = client.post("/api/reconciliations/sample")
    error = _error(answer, 500, "ERREUR_INTERNE")
    assert "secret" not in answer.text and "Traceback" not in answer.text
    assert error["details"] is None
    assert "x-request-id" in answer.headers


# Page et fichiers statiques


def test_page_et_static(tmp_path):
    # Même forme que le build Vite : index.html + assets/ servis sous /static/.
    (tmp_path / "index.html").write_text("<!doctype html><title>Middle office</title>")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "index-abc123.css").write_text("body{}")
    client = TestClient(create_app(web_dir=tmp_path))
    page = client.get("/")
    assert page.status_code == 200 and "<title>Middle office</title>" in page.text
    assert "content-security-policy" in page.headers
    assert client.get("/static/assets/index-abc123.css").text == "body{}"
    _error(client.get("/static/absent.js"), 404, "INTROUVABLE")


def test_page_absente_503(tmp_path):
    client = TestClient(create_app(web_dir=tmp_path))
    _error(client.get("/"), 503, "PAGE_INDISPONIBLE")


def test_noms_de_l_exemple_coherents():
    assert [f["name"] for f in SAMPLE["files"]] == [PMS, A, B, C]
    assert (DATA_DIR / PMS).stat().st_size == SAMPLE["files"][0]["size"]


def test_static_sans_dossier_web_404(tmp_path):
    client = TestClient(create_app(web_dir=tmp_path / "absent"))
    _error(client.get("/static/assets/index.js"), 404, "INTROUVABLE")


def test_logs_requete_et_audit_sans_contenu(client, caplog):
    caplog.set_level("INFO", logger="middle_office.api")
    body = client.post("/api/reconciliations", json=_body()).json()
    text = caplog.text
    assert f"audit rapprochement id={body['id']} statut=OK nb_suspens=7" in text
    assert SAMPLE["files"][0]["sha256"] in text
    assert "POST /api/reconciliations 201" in text
    assert "SC-PAT-01" not in text and _body()["files"][0]["content_b64"][:40] not in text


# Historique persistant (traçabilité RCCI) : il survit au redémarrage, hors de orsay.db


def test_historique_par_defaut_dans_var_hors_git():
    assert Settings().history_file == ROOT.parent / "var" / "history.db"
    ignored = (ROOT.parent / ".gitignore").read_text().splitlines()
    assert "var/" in ignored


def test_historique_survit_au_redemarrage(tmp_path):
    file = tmp_path / "h.db"
    before = TestClient(create_app(history_file=file))
    created = before.post("/api/reconciliations", json=_body()).json()
    csv = before.get(f"/api/reconciliations/{created['id']}/breaks.csv")
    text = before.get(f"/api/reconciliations/{created['id']}/status-report").json()
    blocked = before.post("/api/reconciliations", json=_body(files(c=b"<x/>"))).json()

    after = TestClient(create_app(history_file=file))  # redémarrage
    assert after.get(f"/api/reconciliations/{created['id']}").json() == created
    reread = after.get(f"/api/reconciliations/{created['id']}/breaks.csv")
    assert reread.content == csv.content and reread.headers == csv.headers | {
        "x-request-id": reread.headers["x-request-id"]
    }
    assert after.get(f"/api/reconciliations/{created['id']}/status-report").json() == text
    assert [r["id"] for r in after.get("/api/reconciliations").json()] == [
        blocked["id"],
        created["id"],
    ]
    assert after.get(f"/api/reconciliations/{blocked['id']}").json()["status"] == "BLOQUE"


def test_historique_persistant_liste_bornee_mais_tout_relisible(tmp_path):
    client = TestClient(create_app(history_file=tmp_path / "h.db", history_size=2))
    ids = [client.post("/api/reconciliations/sample").json()["id"] for _ in range(3)]
    assert [r["id"] for r in client.get("/api/reconciliations").json()] == ids[:0:-1]
    assert client.get(f"/api/reconciliations/{ids[0]}").json()["id"] == ids[0]


def test_historique_n_ecrit_jamais_dans_orsay_db(tmp_path, monkeypatch):
    connections = []
    connect = sqlite3.connect

    def spy(db_path, *args, **kwargs):
        connections.append(str(db_path))
        return connect(db_path, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", spy)
    fingerprint = (DATA_DIR / "orsay.db").read_bytes()
    client = TestClient(create_app(history_file=tmp_path / "h.db"))
    id_ = client.post("/api/reconciliations/sample").json()["id"]
    client.get(f"/api/reconciliations/{id_}/breaks.csv")
    client.get("/api/reconciliations")
    assert any(c.endswith("h.db") for c in connections)
    assert all("mode=ro" in c for c in connections if "orsay.db" in c)
    assert (DATA_DIR / "orsay.db").read_bytes() == fingerprint
    with pytest.raises(ValueError, match="orsay.db"):
        create_app(history_file=DATA_DIR / "orsay.db")


# Statut de traitement partagé (il ne vivait que dans le navigateur de l'opérateur)
def test_statut_de_traitement_partage_et_journalise(tmp_path, caplog):
    caplog.set_level("INFO", logger="middle_office.api")
    file = tmp_path / "history.db"
    client = TestClient(create_app(history_file=file, llm_client=None))
    first = client.post("/api/reconciliations/sample").json()
    assert client.get(f"/api/reconciliations/{first['id']}/statuses").json() == {"statuses": {}}

    answer = client.put(
        f"/api/reconciliations/{first['id']}/breaks/S1/status",
        json={"status": "en_cours"},
        headers={"X-Request-ID": "rid-statut"},
    )
    assert answer.status_code == 200 and answer.json()["status"] == "en_cours"
    assert "audit statut rid=rid-statut" in caplog.text

    # Un autre poste (autre processus, même base) et un nouveau rapprochement du même jour le voient.
    other_desk = TestClient(create_app(history_file=file, llm_client=None))
    second = other_desk.post("/api/reconciliations/sample").json()
    assert other_desk.get(f"/api/reconciliations/{second['id']}/statuses").json() == {
        "statuses": {"S1": "en_cours"}
    }
    with sqlite3.connect(file) as db:
        assert db.execute("SELECT status, request_id FROM status_log").fetchall() == [
            ("en_cours", "rid-statut")
        ]


def test_retour_a_traiter_n_est_plus_renvoye(client):
    id_ = client.post("/api/reconciliations/sample").json()["id"]
    for status in ("traite", "a_traiter"):
        client.put(f"/api/reconciliations/{id_}/breaks/S2/status", json={"status": status})
    assert client.get(f"/api/reconciliations/{id_}/statuses").json() == {"statuses": {}}


@pytest.mark.parametrize(
    ("breaks", "body", "status", "code"),
    [
        ("S99", {"status": "traite"}, 404, "INTROUVABLE"),
        ("S1", {"status": "fini"}, 422, "VALIDATION"),
        ("S1", {"status": "traite", "par": "moi"}, 422, "VALIDATION"),
    ],
)
def test_statut_invalide(client, breaks, body, status, code):
    id_ = client.post("/api/reconciliations/sample").json()["id"]
    _error(
        client.put(f"/api/reconciliations/{id_}/breaks/{breaks}/status", json=body), status, code
    )


def test_changer_des_statuts_ne_consomme_pas_le_quota_des_depots():
    client = TestClient(create_app(history_file=None, llm_client=None, post_limit=2))
    id_ = client.post("/api/reconciliations/sample").json()["id"]
    for status in ("en_cours", "traite", "en_cours", "traite"):
        assert (
            client.put(
                f"/api/reconciliations/{id_}/breaks/S1/status", json={"status": status}
            ).status_code
            == 200
        )
    assert client.post("/api/reconciliations/sample").status_code == 201
