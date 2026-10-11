"""La date d'arrêté n'est plus codée en dur : elle est lue dans les fichiers déposés (PMS de référence)."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from middle_office import rapprocher
from middle_office.api import create_app
from middle_office.domaine.base_gestion import date_reference
from middle_office.domaine.rapprochement.calendrier import jour_ouvre_precedent
from tests.fabrique import DONNEES, PMS, A, B, C, fichiers, regles, remplacer, xlsx_a

PARAM = DONNEES / "parametrage.xlsx"
BASE = DONNEES / "orsay.db"


def _lendemain() -> dict[str, bytes]:
    """Les mêmes fichiers, datés du 26/09 : le scénario « demain matin »."""
    pms = (DONNEES / PMS).read_bytes().decode().replace("2026-09-25;", "2026-09-26;").encode()
    return {
        PMS: pms,
        A: xlsx_a(titre="RELEVE DE POSITIONS - DEPOSITAIRE A - ARRETE DU 26/09/2026"),
        B: remplacer(B, ("H20260925", "H20260926")),
        C: remplacer(C, ("<DateArrete>25092026", "<DateArrete>26092026")),
    }


def test_date_lue_dans_les_fichiers():
    resultat = rapprocher(fichiers(), PARAM, BASE)
    assert resultat.statut == "OK" and resultat.date_arrete == date(2026, 9, 25)
    assert len(resultat.suspens) == 7


def test_fichiers_du_lendemain_acceptes_et_csdr_detecte():
    resultat = rapprocher(_lendemain(), PARAM, BASE)
    assert resultat.statut == "OK" and resultat.date_arrete == date(2026, 9, 26)
    # L'achat SCHNEIDER (op. n°19) devait se dénouer le 26/09 : encore en attente, c'est un risque CSDR.
    schneider = next(s for s in resultat.suspens if s.isin == "FR0000012965")
    assert schneider.priorite == "critique"
    assert "DENOUEMENT_DEPASSE" in regles(resultat, "SIGNALE")


def test_pms_avec_plusieurs_dates_bloquant():
    pms = remplacer(
        PMS, ("2026-09-25;SC-ACT-01; fr0000014078", "2026-09-24;SC-ACT-01; fr0000014078")
    )
    resultat = rapprocher(fichiers(pms=pms), PARAM, BASE)
    assert resultat.statut == "BLOQUE" and resultat.date_arrete is None
    assert any(a.regle == "DATE_ARRETE" and "plusieurs dates" in a.motif for a in resultat.journal)


def test_conservateur_d_une_autre_date_bloquant():
    resultat = rapprocher(fichiers(b=remplacer(B, ("H20260925", "H20260926"))), PARAM, BASE)
    assert resultat.statut == "BLOQUE" and "DATE_ARRETE" in regles(resultat, "BLOQUANT")


def test_date_attendue_refuse_les_fichiers_perimes():
    resultat = rapprocher(fichiers(), PARAM, BASE, date_attendue=date(2026, 9, 28))
    assert resultat.statut == "BLOQUE"
    bloquant = next(a for a in resultat.journal if a.regle == "DATE_ARRETE")
    assert "25/09/2026" in bloquant.motif and "28/09/2026" in bloquant.motif


def test_pms_manquant_pas_de_date():
    depot = fichiers()
    del depot[PMS]
    resultat = rapprocher(depot, PARAM, BASE)
    assert resultat.statut == "BLOQUE" and resultat.date_arrete is None
    assert "FICHIER_MANQUANT" in regles(resultat, "BLOQUANT")


def test_date_de_reference_des_questions_lue_dans_la_base():
    assert date_reference(BASE) == date(2026, 9, 25)


def test_api_dates_venues_des_donnees():
    client = TestClient(create_app(fichier_historique=None, client_llm=None))
    assert (
        client.get("/api/sante").json()["date_arrete"] == "2026-09-25"
    )  # date de la base de gestion
    import base64

    depot = [
        {"nom": nom, "contenu_b64": base64.b64encode(contenu).decode()}
        for nom, contenu in _lendemain().items()
    ]
    corps = client.post("/api/rapprochements", json={"fichiers": depot}).json()
    assert (
        corps["date_arrete"] == "2026-09-26" and corps["synthese"]["par_priorite"]["critique"] == 1
    )
    assert (
        "26/09/2026"
        in client.get(f"/api/rapprochements/{corps['id']}/point-de-situation").json()["texte"]
    )


def test_api_date_attendue_configurable():
    client = TestClient(
        create_app(fichier_historique=None, client_llm=None, date_arrete_attendue=date(2026, 9, 28))
    )
    corps = client.post("/api/rapprochements/exemple").json()
    assert corps["statut"] == "BLOQUE"


def test_date_attendue_auto_suit_le_jour_ouvre_precedent(monkeypatch):
    monkeypatch.setenv("DATE_ARRETE_ATTENDUE", "auto")
    reglages = create_app(fichier_historique=None, client_llm=None).state.reglages
    assert reglages.date_attendue(date(2026, 9, 28)) == date(2026, 9, 25)  # lundi → vendredi
    assert reglages.date_attendue(date(2026, 9, 26)) == date(2026, 9, 25)


def test_date_attendue_auto_refuse_les_fichiers_d_avant_hier(monkeypatch):
    """Reproduit en revue : relancer les fichiers de la veille passait sans alerte."""
    monkeypatch.setenv("DATE_ARRETE_ATTENDUE", "auto")
    client = TestClient(create_app(fichier_historique=None, client_llm=None))
    corps = client.post(
        "/api/rapprochements/exemple"
    ).json()  # arrêté du 25/09, nous sommes plus tard
    assert corps["statut"] == "BLOQUE"
    assert any(a["regle"] == "DATE_ARRETE" for a in corps["journal"])


@pytest.mark.parametrize("valeur", ["", "  "])
def test_date_attendue_vide_lit_le_pms(monkeypatch, valeur):
    monkeypatch.setenv("DATE_ARRETE_ATTENDUE", valeur)
    client = TestClient(create_app(fichier_historique=None, client_llm=None))
    assert client.post("/api/rapprochements/exemple").json()["statut"] == "OK"


def test_date_attendue_invalide_refuse_le_demarrage(monkeypatch):
    monkeypatch.setenv("DATE_ARRETE_ATTENDUE", "25/09/2026")
    with pytest.raises(ValueError, match="DATE_ARRETE_ATTENDUE"):
        create_app(fichier_historique=None, client_llm=None)


@pytest.mark.parametrize(
    ("jour", "veille_ouvree"),
    [
        (date(2026, 4, 7), date(2026, 4, 2)),  # lundi de Pâques et vendredi saint fermés
        (date(2026, 12, 28), date(2026, 12, 24)),  # 25 et 26 décembre
        (date(2027, 1, 4), date(2026, 12, 31)),  # 1er janvier, puis week-end
        (date(2026, 5, 4), date(2026, 4, 30)),  # 1er mai
    ],
)
def test_jour_ouvre_precedent_target2(jour, veille_ouvree):
    assert jour_ouvre_precedent(jour) == veille_ouvree


def test_questions_sans_base_503(tmp_path):
    client = TestClient(
        create_app(fichier_historique=None, client_llm=None, dossier_donnees=tmp_path)
    )
    for route in ("/api/questions", "/api/questions/flux"):
        reponse = client.post(route, json={"question": "Encours valorisé du fonds OBL"})
        assert (
            reponse.status_code == 503 and reponse.json()["erreur"]["code"] == "BASE_INDISPONIBLE"
        )
