"""La date d'arrêté n'est plus codée en dur : elle est lue dans les fichiers déposés (PMS de référence)."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from middle_office import reconcile
from middle_office.api import create_app
from middle_office.domain.management_db import latest_position_date
from middle_office.domain.reconciliation.business_days import previous_business_day
from tests.factory import DATA_DIR, PMS, A, B, C, files, replace_in, rules, xlsx_a

CLIENT_CONFIG = DATA_DIR / "parametrage.xlsx"
DB_PATH = DATA_DIR / "orsay.db"


def _next_day() -> dict[str, bytes]:
    """Les mêmes fichiers, datés du 26/09 : le scénario « demain matin »."""
    pms = (DATA_DIR / PMS).read_bytes().decode().replace("2026-09-25;", "2026-09-26;").encode()
    return {
        PMS: pms,
        A: xlsx_a(security="RELEVE DE POSITIONS - DEPOSITAIRE A - ARRETE DU 26/09/2026"),
        B: replace_in(B, ("H20260925", "H20260926")),
        C: replace_in(C, ("<DateArrete>25092026", "<DateArrete>26092026")),
    }


def test_date_lue_dans_les_fichiers():
    result = reconcile(files(), CLIENT_CONFIG, DB_PATH)
    assert result.status == "OK" and result.as_of_date == date(2026, 9, 25)
    assert len(result.breaks) == 7


def test_fichiers_du_lendemain_acceptes_et_csdr_detecte():
    result = reconcile(_next_day(), CLIENT_CONFIG, DB_PATH)
    assert result.status == "OK" and result.as_of_date == date(2026, 9, 26)
    # L'achat SCHNEIDER (op. n°19) devait se dénouer le 26/09 : encore en attente, c'est un risque CSDR.
    schneider = next(s for s in result.breaks if s.isin == "FR0000012965")
    assert schneider.priority == "critique"
    assert "DENOUEMENT_DEPASSE" in rules(result, "SIGNALE")


def test_pms_avec_plusieurs_dates_bloquant():
    pms = replace_in(
        PMS, ("2026-09-25;SC-ACT-01; fr0000014078", "2026-09-24;SC-ACT-01; fr0000014078")
    )
    result = reconcile(files(pms=pms), CLIENT_CONFIG, DB_PATH)
    assert result.status == "BLOQUE" and result.as_of_date is None
    assert any(
        a.rule == "DATE_ARRETE" and "plusieurs dates" in a.reason for a in result.cleaning_log
    )


def test_conservateur_d_une_autre_date_bloquant():
    result = reconcile(files(b=replace_in(B, ("H20260925", "H20260926"))), CLIENT_CONFIG, DB_PATH)
    assert result.status == "BLOQUE" and "DATE_ARRETE" in rules(result, "BLOQUANT")


def test_date_attendue_refuse_les_fichiers_perimes():
    result = reconcile(files(), CLIENT_CONFIG, DB_PATH, expected_date=date(2026, 9, 28))
    assert result.status == "BLOQUE"
    blocking = next(a for a in result.cleaning_log if a.rule == "DATE_ARRETE")
    assert "25/09/2026" in blocking.reason and "28/09/2026" in blocking.reason


def test_pms_manquant_pas_de_date():
    upload = files()
    del upload[PMS]
    result = reconcile(upload, CLIENT_CONFIG, DB_PATH)
    assert result.status == "BLOQUE" and result.as_of_date is None
    assert "FICHIER_MANQUANT" in rules(result, "BLOQUANT")


def test_date_de_reference_des_questions_lue_dans_la_base():
    assert latest_position_date(DB_PATH) == date(2026, 9, 25)


def test_api_dates_venues_des_donnees():
    client = TestClient(create_app(history_file=None, llm_client=None))
    assert (
        client.get("/api/health").json()["as_of_date"] == "2026-09-25"
    )  # date de la base de gestion
    import base64

    upload = [
        {"name": name, "content_b64": base64.b64encode(content).decode()}
        for name, content in _next_day().items()
    ]
    body = client.post("/api/reconciliations", json={"files": upload}).json()
    assert body["as_of_date"] == "2026-09-26" and body["summary"]["by_priority"]["critique"] == 1
    assert (
        "26/09/2026"
        in client.get(f"/api/reconciliations/{body['id']}/status-report").json()["text"]
    )


def test_api_date_attendue_configurable():
    client = TestClient(
        create_app(history_file=None, llm_client=None, expected_as_of_date=date(2026, 9, 28))
    )
    body = client.post("/api/reconciliations/sample").json()
    assert body["status"] == "BLOQUE"


def test_date_attendue_auto_suit_le_jour_ouvre_precedent(monkeypatch):
    monkeypatch.setenv("EXPECTED_AS_OF_DATE", "auto")
    settings = create_app(history_file=None, llm_client=None).state.settings
    assert settings.expected_date(date(2026, 9, 28)) == date(2026, 9, 25)  # lundi → vendredi
    assert settings.expected_date(date(2026, 9, 26)) == date(2026, 9, 25)


def test_date_attendue_auto_refuse_les_fichiers_d_avant_hier(monkeypatch):
    """Reproduit en revue : relancer les fichiers de la veille passait sans alerte."""
    monkeypatch.setenv("EXPECTED_AS_OF_DATE", "auto")
    client = TestClient(create_app(history_file=None, llm_client=None))
    body = client.post(
        "/api/reconciliations/sample"
    ).json()  # arrêté du 25/09, nous sommes plus tard
    assert body["status"] == "BLOQUE"
    assert any(a["rule"] == "DATE_ARRETE" for a in body["cleaning_log"])


@pytest.mark.parametrize("value", ["", "  "])
def test_date_attendue_vide_lit_le_pms(monkeypatch, value):
    monkeypatch.setenv("EXPECTED_AS_OF_DATE", value)
    client = TestClient(create_app(history_file=None, llm_client=None))
    assert client.post("/api/reconciliations/sample").json()["status"] == "OK"


def test_date_attendue_invalide_refuse_le_demarrage(monkeypatch):
    monkeypatch.setenv("EXPECTED_AS_OF_DATE", "25/09/2026")
    with pytest.raises(ValueError, match="EXPECTED_AS_OF_DATE"):
        create_app(history_file=None, llm_client=None)


@pytest.mark.parametrize(
    ("day", "expected_previous"),
    [
        (date(2026, 4, 7), date(2026, 4, 2)),  # lundi de Pâques et vendredi saint fermés
        (date(2026, 12, 28), date(2026, 12, 24)),  # 25 et 26 décembre
        (date(2027, 1, 4), date(2026, 12, 31)),  # 1er janvier, puis week-end
        (date(2026, 5, 4), date(2026, 4, 30)),  # 1er mai
    ],
)
def test_jour_ouvre_precedent_target2(day, expected_previous):
    assert previous_business_day(day) == expected_previous


def test_questions_sans_base_503(tmp_path):
    client = TestClient(create_app(history_file=None, llm_client=None, data_dir=tmp_path))
    for route in ("/api/questions", "/api/questions/stream"):
        answer = client.post(route, json={"question": "Encours valorisé du fonds OBL"})
        assert answer.status_code == 503 and answer.json()["error"]["code"] == "BASE_INDISPONIBLE"
