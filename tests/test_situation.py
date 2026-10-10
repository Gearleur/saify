"""Priorité métier, tri, point de situation et export CSV (étape 3)."""

from decimal import Decimal

from reco import rapprocher_dossier
from reco.domaine.rapprochement import Suspens, priorite
from reco.domaine.situation import COLONNES_CSV, point_de_situation, quantite_texte, suspens_csv
from tests.fabrique import DONNEES, C, db_modifiee, fichiers, lancer, remplacer

ISINS = {
    "FR0000011488",
    "FR0000012966",
    "FR0000999914",
    "FR0000015927",
    "FR0000051641",
    "FR0000012965",
    "FR0000016297",
}


def _suspens(type_="QTE", piste="", signalements=None) -> Suspens:
    return Suspens("ORSAY OBLIGATIONS", "FR0000051641", "C", type_, Decimal(10), Decimal(5), "SFIL",
                   [], piste=piste, signalements=signalements or [])  # fmt: skip


def test_priorite_critique_si_risque_csdr():
    s = _suspens(
        piste="op. n°1 ACHAT 5 dén. 24/09/2026 → écart entièrement expliqué",
        signalements=[
            "op. n°1 non dénouée au 24/09/2026 : défaut de règlement-livraison, risque CSDR"
        ],
    )
    assert priorite(s) == "critique"


def test_priorite_en_attente_si_qte_entierement_expliquee_sans_signalement():
    assert priorite(_suspens(piste="op. n°1 ACHAT 5 → écart entièrement expliqué")) == "en_attente"


def test_priorite_a_relever_sinon():
    assert priorite(_suspens()) == "a_relever"
    assert (
        priorite(_suspens(piste="op. n°1 → écart partiellement expliqué, reste 2")) == "a_relever"
    )
    expliquee_mais_signalee = _suspens(
        piste="op. n°1 → écart entièrement expliqué", signalements=["piste à vérifier"]
    )
    assert priorite(expliquee_mais_signalee) == "a_relever"
    assert priorite(_suspens("ABS_DEP", piste="→ écart entièrement expliqué")) == "a_relever"


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


def test_xml_avec_doctype_bloque():
    c = remplacer(
        C,
        ("<RelevePositions", '<!DOCTYPE RelevePositions [<!ENTITY e "x">]>\n<RelevePositions'),
    )
    resultat = lancer(fichiers(c=c))
    assert resultat.statut == "BLOQUE"
    (refus,) = [a for a in resultat.journal if a.regle == "FORMAT"]
    assert refus.niveau == "BLOQUANT" and "DOCTYPE" in refus.motif and refus.remede
