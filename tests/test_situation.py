"""Priorité métier, tri, point de situation et export CSV (étape 3)."""

from decimal import Decimal

from middle_office import rapprocher_dossier
from middle_office.domaine.rapprochement.situation import (
    COLONNES_CSV,
    point_de_situation,
    quantite_texte,
    suspens_csv,
)
from middle_office.domaine.rapprochement.suspens import Signalement, Suspens, priorite
from tests.fabrique import DONNEES, PMS, C, db_modifiee, fichiers, lancer, remplacer

ISINS = {
    "FR0000011488",
    "FR0000012966",
    "FR0000999914",
    "FR0000015927",
    "FR0000051641",
    "FR0000012965",
    "FR0000016297",
}


def _suspens(type_="QTE", explication="aucune", alertes=None) -> Suspens:
    return Suspens(
        "ORSAY OBLIGATIONS",
        "FR0000051641",
        "C",
        type_,
        Decimal(10),
        Decimal(5),
        "SFIL",
        [],
        explication=explication,
        signalements=[Signalement(code, code) for code in alertes or ()],
    )


def test_priorite_critique_si_risque_csdr():
    assert priorite(_suspens(explication="totale", alertes={"CSDR"})) == "critique"


def test_priorite_en_attente_si_qte_entierement_expliquee_sans_signalement():
    assert priorite(_suspens(explication="totale")) == "en_attente"


def test_priorite_a_relever_sinon():
    assert priorite(_suspens()) == "a_relever"
    assert priorite(_suspens(explication="partielle")) == "a_relever"
    assert priorite(_suspens(explication="contraire")) == "a_relever"
    expliquee_mais_signalee = _suspens(explication="totale", alertes={"PISTE_MULTI_CONSERVATEURS"})
    assert priorite(expliquee_mais_signalee) == "a_relever"
    assert priorite(_suspens("DEP", explication="totale")) == "a_relever"


def test_absences_entierement_expliquees_en_attente():
    """Achat d'une ligne nouvelle non dénoué (ABS_DEP), vente totale non dénouée (ABS_INT)."""
    assert priorite(_suspens("ABS_DEP", explication="totale")) == "en_attente"
    assert priorite(_suspens("ABS_INT", explication="totale")) == "en_attente"


def test_tri_priorite_puis_entite_type_isin():
    resultat = rapprocher_dossier(DONNEES)
    ordre = [(s.priorite, s.entite, s.type, s.isin) for s in resultat.suspens]
    assert [o[0] for o in ordre] == ["a_relever"] * 5 + ["en_attente"] * 2
    assert ordre[:5] == sorted(ordre[:5]) and ordre[5:] == sorted(ordre[5:])


def test_csdr_remonte_en_tete(tmp_path):
    db = db_modifiee(tmp_path, "UPDATE mouvements SET date_denouement = '2026-09-24' WHERE id = 20")
    resultat = lancer(fichiers(), db=db)
    assert resultat.suspens[0].isin == "FR0000016297"
    assert resultat.suspens[0].priorite == "critique"


def test_quantite_texte_sans_float_ni_exposant():
    assert quantite_texte(Decimal("25000000").scaleb(-2)) == "250000"
    assert quantite_texte(Decimal("-1000.00")) == "-1000"
    assert quantite_texte(Decimal("5000.50")) == "5000.5"
    assert quantite_texte(Decimal("0.00")) == "0"
    assert quantite_texte(None) is None


def test_point_de_situation_complet():
    texte = point_de_situation(rapprocher_dossier(DONNEES))
    assert texte.startswith("Point de situation · rapprochement du 25/09/2026")
    assert "Statut : OK" in texte
    for isin in ISINS:
        assert isin in texte
    for regle in ("SANS_SOUS_COMPTE", "P3G", "ANNULATION_S"):
        assert regle in texte
    assert "25 000" in texte  # formater_quantite
    assert "Contacter le dépositaire" in texte
    assert "op. n°19 ACHAT 25 000" in texte
    assert "ISIN à clé invalide" in texte
    assert texte.index("À RELEVER") < texte.index("EN ATTENTE")


def test_point_de_situation_bloque_donne_le_remede():
    c = remplacer(C, ("<NbItems>9</NbItems>", "<NbItems>8</NbItems>"))
    texte = point_de_situation(lancer(fichiers(c=c)))
    assert "BLOQUÉ" in texte
    assert "TOTAL_CONTROLE" in texte
    assert "redemander au conservateur" in texte


def test_csv_suspens():
    contenu = suspens_csv(rapprocher_dossier(DONNEES).suspens)
    assert contenu.startswith(b"\xef\xbb\xbf")
    lignes = contenu.decode("utf-8-sig").splitlines()
    assert lignes[0] == ";".join(COLONNES_CSV)
    assert lignes[0] == (
        "priorite;fonds;entite;isin;titre;conservateur;type;libelle_type;"
        "qte_pms;qte_conservateur;ecart;action;piste;signalements;sources"
    )
    assert len(lignes) == 8
    safran = next(ligne for ligne in lignes if "FR0000016297" in ligne).split(";")
    assert safran[0] == "en_attente"
    assert safran[8:11] == ["40000", "41000", "-1000"]


def test_csv_neutralise_les_formules_mais_pas_les_ecarts_negatifs():
    """Reproduit en revue : un libellé PMS « =1+2 » ressortait tel quel, et Excel l'exécutait."""
    pms = remplacer(PMS, (";EDF 4% 2031;", ";=1+2;"))
    lignes = suspens_csv(lancer(fichiers(pms=pms)).suspens).decode("utf-8-sig").splitlines()
    edf = next(ligne for ligne in lignes if "FR0000011488" in ligne).split(";")
    assert edf[4] == "'=1+2"
    lvmh = next(ligne for ligne in lignes if "FR0000999914" in ligne).split(";")
    assert lvmh[10] == "-30000"  # nombre, pas texte


def test_xml_avec_doctype_bloque():
    c = remplacer(
        C,
        ("<RelevePositions", '<!DOCTYPE RelevePositions [<!ENTITY e "x">]>\n<RelevePositions'),
    )
    resultat = lancer(fichiers(c=c))
    assert resultat.statut == "BLOQUE"
    (refus,) = [a for a in resultat.journal if a.regle == "FORMAT"]
    assert refus.niveau == "BLOQUANT" and "DOCTYPE" in refus.motif and refus.remede
    # Un seul blocage : « AUCUNE_LIGNE » en plus serait du bruit pour l'opérateur.
    assert [a.regle for a in resultat.journal if a.niveau == "BLOQUANT"] == ["FORMAT"]
