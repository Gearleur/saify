"""Règles de rapprochement issues de la revue de l'étape 1 (NOTES.md, « Revue étape 1 »)."""

from decimal import Decimal

from middle_office.domaine.rapprochement import moteur as rapprochement
from middle_office.domaine.rapprochement.moteur import Suspens
from tests.fabrique import (
    DONNEES,
    PMS,
    A,
    B,
    C,
    db_modifiee,
    fichiers,
    lancer,
    regles,
    remplacer,
    xlsx_a,
)

AFD = "FR0000015927"
SCHNEIDER = "FR0000012965"
SAFRAN = "FR0000016297"


def _item_c(compte: str, isin: str, libelle: str, quantite: str) -> str:
    return (
        f'    <Item><Dim prop="ACTION">C</Dim><Dim prop="COMPTE">{compte}</Dim>'
        f'<Dim prop="CODE_ISIN">{isin}</Dim><Dim prop="LIBELLE_TITRE">{libelle}</Dim>'
        f'<Dim prop="QUANTITE">{quantite}</Dim><Dim prop="LOT">1</Dim></Item>\r\n'
    )


def _c_avec(item: str) -> bytes:
    return remplacer(
        C,
        ("<NbItems>9</NbItems>", "<NbItems>10</NbItems>"),
        ("  </Positions>", item + "  </Positions>"),
    )


def _suspens(resultat, isin: str):
    return [s for s in resultat.suspens if s.isin == isin]


# 1. Un titre livré chez un autre conservateur = un seul suspens, même avec un écart de quantité.
def test_dep_avec_ecart_reste_un_seul_suspens():
    b = remplacer(B, ("DOROFR0000015927000000025000000", "DOROFR0000015927000000020000000"))
    resultat = lancer(fichiers(b=b))
    (dep,) = _suspens(resultat, AFD)
    assert dep.type == "DEP"
    assert dep.ecart == Decimal(50000)  # PMS − conservateur
    assert "Corriger le référentiel dépositaire" in dep.action
    assert "Vérifier les opérations de la veille non dénouées" in dep.action


def test_dep_sans_ecart_une_seule_action():
    (dep,) = _suspens(lancer(fichiers()), AFD)
    assert dep.ecart == 0
    assert dep.action == "Corriger le référentiel dépositaire"


# 2. Plusieurs candidats : on ne devine pas, on garde les suspens et on le signale sur chacun.
def test_dep_ambigu_signale_sur_chaque_suspens():
    resultat = lancer(fichiers(c=_c_avec(_item_c("ORS-OBL", AFD, "AFD 3.5% 2035", "250000,00"))))
    afd = _suspens(resultat, AFD)
    assert sorted((s.type, s.conservateur) for s in afd) == [
        ("ABS_DEP", "A"),
        ("ABS_INT", "B"),
        ("ABS_INT", "C"),
    ]
    assert all(any("ambigu" in m for m in s.signalements) for s in afd)
    assert all("DEP_AMBIGU" in s.alertes for s in afd)


# 3. orsay.db n'est qu'une source d'information : sans elle, le rapprochement tourne quand même.
def test_sans_base_les_suspens_sont_produits(tmp_path):
    resultat = lancer(fichiers(), db=tmp_path / "absente.db")
    assert resultat.statut == "OK"
    assert len(resultat.suspens) == 7
    assert {s.entite for s in resultat.suspens} == {"ORSAY ACTIONS EUROPE", "ORSAY OBLIGATIONS"}
    assert "BASE_INDISPONIBLE" in regles(resultat, "SIGNALE")


# 4. La piste cite l'opération et dit, calcul signé à l'appui, si elle explique l'écart.
def test_piste_ecart_entierement_explique():
    resultat = lancer(fichiers())
    (schneider,) = _suspens(resultat, SCHNEIDER)
    assert "op. n°19" in schneider.piste and "entièrement expliqué" in schneider.piste
    (safran,) = _suspens(resultat, SAFRAN)  # vente en attente : écart négatif
    assert "op. n°20" in safran.piste and "entièrement expliqué" in safran.piste
    assert (schneider.explication, safran.explication) == ("totale", "totale")
    (sfil,) = _suspens(resultat, "FR0000051641")
    assert sfil.explication == "aucune"


def test_piste_ecart_partiellement_explique(tmp_path):
    db = db_modifiee(tmp_path, "UPDATE mouvements SET quantite = 10000 WHERE id = 19")
    (schneider,) = _suspens(lancer(fichiers(), db=db), SCHNEIDER)
    assert "partiellement expliqué" in schneider.piste and "reste 15 000" in schneider.piste
    assert schneider.explication == "partielle" and schneider.priorite == "a_relever"


def test_piste_operation_en_sens_contraire(tmp_path):
    db = db_modifiee(tmp_path, "UPDATE mouvements SET sens = 'VENTE' WHERE id = 19")
    (schneider,) = _suspens(lancer(fichiers(), db=db), SCHNEIDER)
    assert "n'explique pas l'écart" in schneider.piste
    assert schneider.explication == "contraire" and schneider.priorite == "a_relever"


def test_piste_seulement_possible_si_plusieurs_conservateurs():
    # mouvements n'a pas de colonne conservateur : si le fonds détient le titre chez A et C,
    # on ne sait pas lequel des deux l'opération concerne.
    pms = (
        DONNEES / PMS
    ).read_bytes() + b"2026-09-25;SC-ACT-01;FR0000012965;SCHNEIDER;1000;BP2S\r\n"
    c = _c_avec(_item_c("ORS-ACT", SCHNEIDER, "SCHNEIDER", "1000,00"))
    (schneider,) = _suspens(lancer(fichiers(pms=pms, c=c)), SCHNEIDER)
    assert "explication possible" in schneider.piste
    # Un vrai signalement, pour que l'opérateur n'oublie pas de vérifier le conservateur concerné.
    assert any("à vérifier" in m and "plusieurs conservateurs" in m for m in schneider.signalements)
    assert schneider.alertes == {"PISTE_MULTI_CONSERVATEURS"}
    assert schneider.priorite == "a_relever"


def test_pas_de_signalement_si_un_seul_conservateur():
    (schneider,) = _suspens(lancer(fichiers()), SCHNEIDER)
    assert schneider.signalements == []


# A. Opération non dénouée à sa date prévue : défaut de règlement-livraison, risque CSDR.
def test_denouement_depasse_signale(tmp_path):
    db = db_modifiee(tmp_path, "UPDATE mouvements SET date_denouement = '2026-09-24' WHERE id = 19")
    resultat = lancer(fichiers(), db=db)
    assert "DENOUEMENT_DEPASSE" in regles(resultat, "SIGNALE")
    (schneider,) = _suspens(resultat, SCHNEIDER)
    assert any("CSDR" in m for m in schneider.signalements)
    assert "CSDR" in schneider.alertes and schneider.priorite == "critique"


# B. Une position nulle est une absence : pas de suspens pour 0 titre.
def test_position_nulle_ne_cree_pas_de_suspens():
    pms = (DONNEES / PMS).read_bytes() + b"2026-09-25;SC-ACT-01;FR0000120271;TOTAL;0;CACEIS\r\n"
    resultat = lancer(fichiers(pms=pms))
    assert len(resultat.suspens) == 7


# C. Une ligne en double chez A ou B est additionnée (on ne devine pas), mais signalée.
def test_doublon_b_signale():
    ligne = "DORAFR0000014078000000001000000\r\n"
    b = remplacer(B, (ligne, ligne + ligne), ("T000013", "T000014"))
    resultat = lancer(fichiers(b=b))
    assert "DOUBLON" in regles(resultat, "SIGNALE")
    (vinci,) = _suspens(resultat, "FR0000014078")
    assert vinci.type == "QTE"


def test_doublon_a_signale():
    resultat = lancer(fichiers(a=xlsx_a(dupliquer=4)))
    assert "DOUBLON" in regles(resultat, "SIGNALE")


# Deux fichiers pour une même source : lequel est le bon ? On refuse.
def test_deux_fichiers_meme_source_bloquant():
    depot = fichiers()
    depot["depositaire_A_20260925_v2.xlsx"] = depot[A]
    resultat = lancer(depot)
    assert resultat.statut == "BLOQUE"
    assert "FICHIERS_MULTIPLES" in regles(resultat, "BLOQUANT")


# La priorité se lit dans des champs structurés, jamais dans le texte des messages (libellés humains).
def test_isin_invalide_alerte():
    (edf_invalide,) = _suspens(lancer(fichiers()), "FR0000012966")
    assert edf_invalide.alertes == {"ISIN_INVALIDE"}


def _qte(**champs) -> Suspens:
    return Suspens("ORSAY ACTIONS EUROPE", SCHNEIDER, "A", "QTE", Decimal(250000), Decimal(225000),
                   "SCHNEIDER", [], **champs)  # fmt: skip


def test_priorite_independante_des_libelles():
    assert _qte(piste="tout est couvert", explication="totale").priorite == "en_attente"
    assert _qte(signalements=["livraison en retard"], alertes={"CSDR"}).priorite == "critique"
    # Les anciens mots-clés dans le texte, sans le champ structuré, ne décident plus rien.
    assert _qte(piste="écart entièrement expliqué").priorite == "a_relever"
    assert _qte(signalements=["risque CSDR"]).priorite == "a_relever"
    assert _qte(explication="totale", alertes={"ISIN_INVALIDE"}).priorite == "a_relever"
    dep = _qte(explication="totale")
    dep.type = "DEP"
    assert dep.priorite == "a_relever"


def test_reformuler_les_messages_ne_change_pas_la_priorite(monkeypatch):
    attendu = {(s.isin, s.conservateur): s.priorite for s in lancer(fichiers()).suspens}
    piste = rapprochement._piste

    def piste_reformulee(*args):
        _, explication = piste(*args)
        return "libellé reformulé", explication

    monkeypatch.setattr(rapprochement, "_piste", piste_reformulee)
    resultat = lancer(fichiers())
    assert {s.piste for s in resultat.suspens} <= {"", "libellé reformulé"}
    assert {(s.isin, s.conservateur): s.priorite for s in resultat.suspens} == attendu
