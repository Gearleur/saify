"""API HTTP (docs/API.md) : contrat, garde-fous, erreurs uniformes."""

import base64
import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from middle_office.api import create_app as _create_app
from middle_office.api.config import RACINE, Reglages
from tests.fabrique import DONNEES, PMS, A, B, C, fichiers, remplacer


def create_app(**reglages):
    """Historique en mémoire par défaut : les tests n'écrivent jamais dans var/."""
    return _create_app(**{"fichier_historique": None, **reglages})


EXEMPLE = json.loads(
    (Path(__file__).resolve().parents[1] / "docs" / "exemple_rapprochement.json").read_text()
)
ISINS = {s["isin"] for s in EXEMPLE["suspens"]}


def _corps(depot: dict[str, bytes] | None = None) -> dict:
    depot = fichiers() if depot is None else depot
    return {
        "fichiers": [
            {"nom": nom, "contenu_b64": base64.b64encode(contenu).decode()}
            for nom, contenu in depot.items()
        ]
    }


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def cree(client) -> dict:
    reponse = client.post("/api/rapprochements", json=_corps())
    assert reponse.status_code == 201
    return reponse.json()


def _sans_id(rapprochement: dict) -> dict:
    return {k: v for k, v in rapprochement.items() if k not in ("id", "cree_le")}


def _erreur(reponse, statut: int, code: str) -> dict:
    assert reponse.status_code == statut, reponse.text
    erreur = reponse.json()["erreur"]
    assert erreur["code"] == code
    assert set(erreur) == {"code", "message", "details"}
    return erreur


# Contrat nominal


def test_post_quatre_fichiers_egal_a_l_exemple(cree):
    assert cree["id"].startswith("r_") and len(cree["id"]) == 8
    assert cree["cree_le"].endswith("Z")
    assert len(cree["suspens"]) == 7
    assert _sans_id(cree) == _sans_id(EXEMPLE)


def test_exemple_sans_corps(client):
    reponse = client.post("/api/rapprochements/exemple")
    assert reponse.status_code == 201
    assert _sans_id(reponse.json()) == _sans_id(EXEMPLE)


def test_quantites_en_chaines(cree):
    for s in cree["suspens"]:
        for champ in ("qte_pms", "qte_dep", "ecart"):
            assert s[champ] is None or isinstance(s[champ], str)


def test_get_par_id_liste_et_404(client, cree):
    assert client.get(f"/api/rapprochements/{cree['id']}").json() == cree
    second = client.post("/api/rapprochements/exemple").json()
    liste = client.get("/api/rapprochements").json()
    assert [r["id"] for r in liste] == [second["id"], cree["id"]]
    assert liste[1] == {
        "id": cree["id"],
        "cree_le": cree["cree_le"],
        "date_arrete": "2026-09-25",
        "statut": "OK",
        "nb_suspens": 7,
        "nb_a_traiter": 5,
    }
    _erreur(client.get("/api/rapprochements/r_000000"), 404, "INTROUVABLE")
    _erreur(client.get("/api/rapprochements/r_000000/suspens.csv"), 404, "INTROUVABLE")
    _erreur(client.get("/api/nimporte"), 404, "INTROUVABLE")


def test_historique_borne():
    client = TestClient(create_app(historique_max=2))
    ids = [client.post("/api/rapprochements/exemple").json()["id"] for _ in range(3)]
    assert [r["id"] for r in client.get("/api/rapprochements").json()] == ids[:0:-1]
    _erreur(client.get(f"/api/rapprochements/{ids[0]}"), 404, "INTROUVABLE")


def test_csv(client, cree):
    reponse = client.get(f"/api/rapprochements/{cree['id']}/suspens.csv")
    assert reponse.status_code == 200
    assert reponse.headers["content-type"].startswith("text/csv")
    assert reponse.headers["content-disposition"] == 'attachment; filename="suspens_2026-09-25.csv"'
    assert reponse.content.startswith(b"\xef\xbb\xbf")
    lignes = reponse.content.decode("utf-8-sig").splitlines()
    assert lignes[0].startswith("priorite;fonds;entite;isin;titre;")
    assert len(lignes) == 8


def test_point_de_situation(client, cree):
    reponse = client.get(f"/api/rapprochements/{cree['id']}/point-de-situation")
    assert reponse.status_code == 200
    texte = reponse.json()["texte"]
    assert texte.startswith("Point de situation · rapprochement du 25/09/2026")
    assert all(isin in texte for isin in ISINS)
    assert all(regle in texte for regle in ("SANS_SOUS_COMPTE", "P3G", "ANNULATION_S"))


def test_sante_et_parametrage(client):
    sante = client.get("/api/sante").json()
    assert {k: sante[k] for k in ("statut", "version", "date_arrete", "base_disponible")} == {
        "statut": "ok",
        "version": "0.3.0",
        "date_arrete": "2026-09-25",
        "base_disponible": True,
    }
    assert sante["llm"]["actif"] is False  # coupé dans les tests (conftest.py)
    param = client.get("/api/parametrage").json()
    assert {"entite": "ORSAY OBLIGATIONS", "code": "OBL"} in param["fonds"]
    assert len(param["fonds"]) == 3
    assert [c["code"] for c in param["conservateurs"]] == ["A", "B", "C"]
    assert {t["code"] for t in param["types_ecarts"]} == {"QTE", "ABS_DEP", "ABS_INT", "DEP"}
    assert {"cle": "SC-PAT-01", "entite": "ORSAY PATRIMOINE"} in param["transcos"][
        "TRANSCO_SOUS_COMPTES"
    ]
    assert set(param["transcos"]) == {
        "TRANSCO_SOUS_COMPTES",
        "TRANSCO_DEPOSITAIRE_A",
        "TRANSCO_DEPOSITAIRE_B",
        "TRANSCO_DEPOSITAIRE_C",
    }
    assert len(param["exclusions"]) == 3


# Refus métier : 200 + BLOQUE


def test_fichier_bloquant_200_avec_remede(client):
    c = remplacer(C, ("<NbItems>9</NbItems>", "<NbItems>8</NbItems>"))
    reponse = client.post("/api/rapprochements", json=_corps(fichiers(c=c)))
    assert reponse.status_code == 200  # refus métier : pas une erreur HTTP (docs/API.md)
    corps = reponse.json()
    assert corps["statut"] == "BLOQUE"
    assert corps["suspens"] == []
    assert corps["synthese"]["nb_suspens"] == 0
    assert corps["synthese"]["par_priorite"] == {"critique": 0, "a_relever": 0, "en_attente": 0}
    bloquants = [a for a in corps["journal"] if a["niveau"] == "BLOQUANT"]
    assert bloquants and all(a["remede"] for a in bloquants)


def test_xml_doctype_bloque(client):
    c = remplacer(
        C, ("<RelevePositions", '<!DOCTYPE RelevePositions [<!ENTITY e "x">]>\n<RelevePositions')
    )
    corps = client.post("/api/rapprochements", json=_corps(fichiers(c=c))).json()
    assert corps["statut"] == "BLOQUE"
    assert any(a["regle"] == "FORMAT" and a["niveau"] == "BLOQUANT" for a in corps["journal"])


# Validation des entrées


def test_base64_invalide(client):
    corps = _corps()
    corps["fichiers"][0]["contenu_b64"] = "pas du base64 !"
    _erreur(client.post("/api/rapprochements", json=corps), 422, "VALIDATION")


@pytest.mark.parametrize(
    "nom",
    [
        "../positions_internes.csv",
        "dossier/depositaire_B.txt",
        "a\\b.csv",
        "positions_internes.exe",
        "",
    ],
)
def test_nom_refuse(client, nom):
    corps = _corps({nom: b"x"})
    _erreur(client.post("/api/rapprochements", json=corps), 422, "VALIDATION")


def test_trop_de_fichiers_ou_aucun(client):
    corps = _corps({f"positions_internes_{i}.csv": b"x" for i in range(9)})
    _erreur(client.post("/api/rapprochements", json=corps), 422, "VALIDATION")
    _erreur(client.post("/api/rapprochements", json={"fichiers": []}), 422, "VALIDATION")


def test_validation_ne_renvoie_pas_le_contenu(client):
    erreur = _erreur(client.post("/api/rapprochements", json={"x": "SECRET"}), 422, "VALIDATION")
    assert "SECRET" not in json.dumps(erreur)


def test_json_illisible(client):
    reponse = client.post(
        "/api/rapprochements", content=b"{pas json", headers={"content-type": "application/json"}
    )
    _erreur(reponse, 422, "VALIDATION")


def test_fichier_non_reconnu(client):
    depot = fichiers()
    depot["releve_inconnu.csv"] = b"x"
    erreur = _erreur(
        client.post("/api/rapprochements", json=_corps(depot)), 422, "FICHIER_NON_RECONNU"
    )
    assert "depositaire_C" in erreur["message"]


def test_nom_de_fichier_reconnu_quelle_que_soit_la_casse(client):
    """Reproduit en revue : le front acceptait « Depositaire_A… », le back répondait 422."""
    depot = {
        nom.replace("depositaire_A", "Depositaire_a").upper() if "_A_" in nom else nom: contenu
        for nom, contenu in fichiers().items()
    }
    reponse = client.post("/api/rapprochements", json=_corps(depot))
    assert reponse.status_code == 201 and reponse.json()["statut"] == "OK"
    assert len(reponse.json()["suspens"]) == 7


def test_corps_trop_gros():
    client = TestClient(create_app(taille_corps_max=1000))
    _erreur(client.post("/api/rapprochements", json=_corps()), 413, "CORPS_TROP_GROS")


def test_corps_trop_gros_sans_content_length():
    client = TestClient(create_app(taille_corps_max=1000))

    def morceaux():
        yield b'{"fichiers": ['
        yield b"x" * 2000
        yield b"]}"

    reponse = client.post(
        "/api/rapprochements", content=morceaux(), headers={"content-type": "application/json"}
    )
    _erreur(reponse, 413, "CORPS_TROP_GROS")


def test_fichier_trop_gros():
    client = TestClient(create_app(taille_fichier_max=1000))
    _erreur(client.post("/api/rapprochements", json=_corps()), 413, "FICHIER_TROP_GROS")


# Garde-fous transverses


def test_rate_limit_post():
    client = TestClient(create_app(limite_post=2))
    for _ in range(2):
        assert client.post("/api/rapprochements", json={}).status_code == 422
    reponse = client.post("/api/rapprochements", json={})
    _erreur(reponse, 429, "RATE_LIMIT")
    assert 1 <= int(reponse.headers["retry-after"]) <= 60
    assert client.get("/api/sante").status_code == 200  # compteur GET séparé


def test_rate_limit_get():
    client = TestClient(create_app(limite_get=3))
    for _ in range(3):
        assert client.get("/api/sante").status_code == 200
    _erreur(client.get("/api/sante"), 429, "RATE_LIMIT")


def test_en_tetes_de_securite_et_request_id(client):
    reponse = client.get("/api/sante")
    assert reponse.headers["content-security-policy"] == (
        "default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; "
        "frame-ancestors 'none'"
    )
    assert reponse.headers["x-content-type-options"] == "nosniff"
    assert reponse.headers["x-frame-options"] == "DENY"
    assert reponse.headers["referrer-policy"] == "no-referrer"
    assert len(reponse.headers["x-request-id"]) >= 8
    repris = client.get("/api/sante", headers={"X-Request-ID": "abc-123"})
    assert repris.headers["x-request-id"] == "abc-123"
    assert "x-request-id" in client.get("/api/nimporte").headers


def test_erreur_interne_sans_trace(monkeypatch):
    def panne(*_args, **_kwargs):
        raise RuntimeError("détail interne secret")

    monkeypatch.setattr("middle_office.api.services.rapprochements.rapprocher", panne)
    client = TestClient(create_app(), raise_server_exceptions=False)
    reponse = client.post("/api/rapprochements/exemple")
    erreur = _erreur(reponse, 500, "ERREUR_INTERNE")
    assert "secret" not in reponse.text and "Traceback" not in reponse.text
    assert erreur["details"] is None
    assert "x-request-id" in reponse.headers


# Page et fichiers statiques


def test_page_et_static(tmp_path):
    # Même forme que le build Vite : index.html + assets/ servis sous /static/.
    (tmp_path / "index.html").write_text("<!doctype html><title>Middle office</title>")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "index-abc123.css").write_text("body{}")
    client = TestClient(create_app(dossier_web=tmp_path))
    page = client.get("/")
    assert page.status_code == 200 and "<title>Middle office</title>" in page.text
    assert "content-security-policy" in page.headers
    assert client.get("/static/assets/index-abc123.css").text == "body{}"
    _erreur(client.get("/static/absent.js"), 404, "INTROUVABLE")


def test_page_absente_503(tmp_path):
    client = TestClient(create_app(dossier_web=tmp_path))
    _erreur(client.get("/"), 503, "PAGE_INDISPONIBLE")


def test_noms_de_l_exemple_coherents():
    assert [f["nom"] for f in EXEMPLE["fichiers"]] == [PMS, A, B, C]
    assert (DONNEES / PMS).stat().st_size == EXEMPLE["fichiers"][0]["taille"]


def test_static_sans_dossier_web_404(tmp_path):
    client = TestClient(create_app(dossier_web=tmp_path / "absent"))
    _erreur(client.get("/static/assets/index.js"), 404, "INTROUVABLE")


def test_logs_requete_et_audit_sans_contenu(client, caplog):
    caplog.set_level("INFO", logger="middle_office.api")
    corps = client.post("/api/rapprochements", json=_corps()).json()
    texte = caplog.text
    assert f"audit rapprochement id={corps['id']} statut=OK nb_suspens=7" in texte
    assert EXEMPLE["fichiers"][0]["sha256"] in texte
    assert "POST /api/rapprochements 201" in texte
    assert "SC-PAT-01" not in texte and _corps()["fichiers"][0]["contenu_b64"][:40] not in texte


# Historique persistant (traçabilité RCCI) : il survit au redémarrage, hors de orsay.db


def test_historique_par_defaut_dans_var_hors_git():
    assert Reglages().fichier_historique == RACINE.parent / "var" / "historique.db"
    ignores = (RACINE.parent / ".gitignore").read_text().splitlines()
    assert "var/" in ignores


def test_historique_survit_au_redemarrage(tmp_path):
    fichier = tmp_path / "h.db"
    avant = TestClient(create_app(fichier_historique=fichier))
    cree = avant.post("/api/rapprochements", json=_corps()).json()
    csv = avant.get(f"/api/rapprochements/{cree['id']}/suspens.csv")
    texte = avant.get(f"/api/rapprochements/{cree['id']}/point-de-situation").json()
    bloque = avant.post("/api/rapprochements", json=_corps(fichiers(c=b"<x/>"))).json()

    apres = TestClient(create_app(fichier_historique=fichier))  # redémarrage
    assert apres.get(f"/api/rapprochements/{cree['id']}").json() == cree
    relu = apres.get(f"/api/rapprochements/{cree['id']}/suspens.csv")
    assert relu.content == csv.content and relu.headers == csv.headers | {
        "x-request-id": relu.headers["x-request-id"]
    }
    assert apres.get(f"/api/rapprochements/{cree['id']}/point-de-situation").json() == texte
    assert [r["id"] for r in apres.get("/api/rapprochements").json()] == [bloque["id"], cree["id"]]
    assert apres.get(f"/api/rapprochements/{bloque['id']}").json()["statut"] == "BLOQUE"


def test_historique_persistant_liste_bornee_mais_tout_relisible(tmp_path):
    client = TestClient(create_app(fichier_historique=tmp_path / "h.db", historique_max=2))
    ids = [client.post("/api/rapprochements/exemple").json()["id"] for _ in range(3)]
    assert [r["id"] for r in client.get("/api/rapprochements").json()] == ids[:0:-1]
    assert client.get(f"/api/rapprochements/{ids[0]}").json()["id"] == ids[0]


def test_historique_n_ecrit_jamais_dans_orsay_db(tmp_path, monkeypatch):
    connexions = []
    connect = sqlite3.connect

    def espion(base, *args, **kwargs):
        connexions.append(str(base))
        return connect(base, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", espion)
    empreinte = (DONNEES / "orsay.db").read_bytes()
    client = TestClient(create_app(fichier_historique=tmp_path / "h.db"))
    id_ = client.post("/api/rapprochements/exemple").json()["id"]
    client.get(f"/api/rapprochements/{id_}/suspens.csv")
    client.get("/api/rapprochements")
    assert any(c.endswith("h.db") for c in connexions)
    assert all("mode=ro" in c for c in connexions if "orsay.db" in c)
    assert (DONNEES / "orsay.db").read_bytes() == empreinte
    with pytest.raises(ValueError, match="orsay.db"):
        create_app(fichier_historique=DONNEES / "orsay.db")


# Statut de traitement partagé (il ne vivait que dans le navigateur de l'opérateur)
def test_statut_de_traitement_partage_et_journalise(tmp_path, caplog):
    caplog.set_level("INFO", logger="middle_office.api")
    fichier = tmp_path / "historique.db"
    client = TestClient(create_app(fichier_historique=fichier, client_llm=None))
    premier = client.post("/api/rapprochements/exemple").json()
    assert client.get(f"/api/rapprochements/{premier['id']}/statuts").json() == {"statuts": {}}

    reponse = client.put(
        f"/api/rapprochements/{premier['id']}/suspens/S1/statut",
        json={"statut": "en_cours"},
        headers={"X-Request-ID": "rid-statut"},
    )
    assert reponse.status_code == 200 and reponse.json()["statut"] == "en_cours"
    assert "audit statut rid=rid-statut" in caplog.text

    # Un autre poste (autre processus, même base) et un nouveau rapprochement du même jour le voient.
    autre_poste = TestClient(create_app(fichier_historique=fichier, client_llm=None))
    second = autre_poste.post("/api/rapprochements/exemple").json()
    assert autre_poste.get(f"/api/rapprochements/{second['id']}/statuts").json() == {
        "statuts": {"S1": "en_cours"}
    }
    with sqlite3.connect(fichier) as db:
        assert db.execute("SELECT statut, request_id FROM statuts_journal").fetchall() == [
            ("en_cours", "rid-statut")
        ]


def test_retour_a_traiter_n_est_plus_renvoye(client):
    id_ = client.post("/api/rapprochements/exemple").json()["id"]
    for statut in ("traite", "a_traiter"):
        client.put(f"/api/rapprochements/{id_}/suspens/S2/statut", json={"statut": statut})
    assert client.get(f"/api/rapprochements/{id_}/statuts").json() == {"statuts": {}}


@pytest.mark.parametrize(
    ("suspens", "corps", "statut", "code"),
    [
        ("S99", {"statut": "traite"}, 404, "INTROUVABLE"),
        ("S1", {"statut": "fini"}, 422, "VALIDATION"),
        ("S1", {"statut": "traite", "par": "moi"}, 422, "VALIDATION"),
    ],
)
def test_statut_invalide(client, suspens, corps, statut, code):
    id_ = client.post("/api/rapprochements/exemple").json()["id"]
    _erreur(
        client.put(f"/api/rapprochements/{id_}/suspens/{suspens}/statut", json=corps), statut, code
    )
