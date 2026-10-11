"""Règles de rapprochement issues de la revue de l'étape 1 (NOTES.md, « Revue étape 1 »)."""

from decimal import Decimal

from middle_office.domain.reconciliation import db_context
from middle_office.domain.reconciliation.breaks import Break, Flag
from tests.factory import (
    DATA_DIR,
    PMS,
    A,
    B,
    C,
    files,
    modified_db,
    replace_in,
    rules,
    run,
    xlsx_a,
)

AFD = "FR0000015927"
SCHNEIDER = "FR0000012965"
SAFRAN = "FR0000016297"


def _item_c(account: str, isin: str, label: str, quantity: str) -> str:
    return (
        f'    <Item><Dim prop="ACTION">C</Dim><Dim prop="COMPTE">{account}</Dim>'
        f'<Dim prop="CODE_ISIN">{isin}</Dim><Dim prop="LIBELLE_TITRE">{label}</Dim>'
        f'<Dim prop="QUANTITE">{quantity}</Dim><Dim prop="LOT">1</Dim></Item>\r\n'
    )


def _c_with(item: str) -> bytes:
    return replace_in(
        C,
        ("<NbItems>9</NbItems>", "<NbItems>10</NbItems>"),
        ("  </Positions>", item + "  </Positions>"),
    )


def _breaks(result, isin: str):
    return [s for s in result.breaks if s.isin == isin]


# 1. Un titre livré chez un autre conservateur = un seul suspens, même avec un écart de quantité.
def test_dep_avec_ecart_reste_un_seul_suspens():
    b = replace_in(B, ("DOROFR0000015927000000025000000", "DOROFR0000015927000000020000000"))
    result = run(files(b=b))
    (custodian_positions,) = _breaks(result, AFD)
    assert custodian_positions.type == "DEP"
    assert custodian_positions.difference == Decimal(50000)  # PMS − conservateur
    assert "Corriger le référentiel dépositaire" in custodian_positions.action
    assert "Vérifier les opérations de la veille non dénouées" in custodian_positions.action


def test_dep_sans_ecart_une_seule_action():
    (custodian_positions,) = _breaks(run(files()), AFD)
    assert custodian_positions.difference == 0
    assert custodian_positions.action == "Corriger le référentiel dépositaire"


# 2. Plusieurs candidats : on ne devine pas, on garde les suspens et on le signale sur chacun.
def test_dep_ambigu_signale_sur_chaque_suspens():
    result = run(files(c=_c_with(_item_c("ORS-OBL", AFD, "AFD 3.5% 2035", "250000,00"))))
    afd = _breaks(result, AFD)
    assert sorted((s.type, s.custodian) for s in afd) == [
        ("ABS_DEP", "A"),
        ("ABS_INT", "B"),
        ("ABS_INT", "C"),
    ]
    assert all(any("ambigu" in g.message for g in s.flags) for s in afd)
    assert all("DEP_AMBIGU" in s.alerts for s in afd)


# 3. orsay.db n'est qu'une source d'information : sans elle, le rapprochement tourne quand même.
def test_sans_base_les_suspens_sont_produits(tmp_path):
    result = run(files(), db=tmp_path / "absente.db")
    assert result.status == "OK"
    assert len(result.breaks) == 7
    assert {s.entity for s in result.breaks} == {"ORSAY ACTIONS EUROPE", "ORSAY OBLIGATIONS"}
    assert "BASE_INDISPONIBLE" in rules(result, "SIGNALE")


# 4. La piste cite l'opération et dit, calcul signé à l'appui, si elle explique l'écart.
def test_piste_ecart_entierement_explique():
    result = run(files())
    (schneider,) = _breaks(result, SCHNEIDER)
    assert "op. n°19" in schneider.lead and "entièrement expliqué" in schneider.lead
    (safran,) = _breaks(result, SAFRAN)  # vente en attente : écart négatif
    assert "op. n°20" in safran.lead and "entièrement expliqué" in safran.lead
    assert (schneider.explanation, safran.explanation) == ("totale", "totale")
    (sfil,) = _breaks(result, "FR0000051641")
    assert sfil.explanation == "aucune"


def test_piste_ecart_partiellement_explique(tmp_path):
    db = modified_db(tmp_path, "UPDATE mouvements SET quantite = 10000 WHERE id = 19")
    (schneider,) = _breaks(run(files(), db=db), SCHNEIDER)
    assert "partiellement expliqué" in schneider.lead and "reste 15 000" in schneider.lead
    assert schneider.explanation == "partielle" and schneider.priority == "a_relever"


def test_piste_operation_en_sens_contraire(tmp_path):
    db = modified_db(tmp_path, "UPDATE mouvements SET sens = 'VENTE' WHERE id = 19")
    (schneider,) = _breaks(run(files(), db=db), SCHNEIDER)
    assert "n'explique pas l'écart" in schneider.lead
    assert schneider.explanation == "contraire" and schneider.priority == "a_relever"


def test_piste_seulement_possible_si_plusieurs_conservateurs():
    # mouvements n'a pas de colonne conservateur : si le fonds détient le titre chez A et C,
    # on ne sait pas lequel des deux l'opération concerne.
    pms = (
        DATA_DIR / PMS
    ).read_bytes() + b"2026-09-25;SC-ACT-01;FR0000012965;SCHNEIDER;1000;BP2S\r\n"
    c = _c_with(_item_c("ORS-ACT", SCHNEIDER, "SCHNEIDER", "1000,00"))
    (schneider,) = _breaks(run(files(pms=pms, c=c)), SCHNEIDER)
    assert "explication possible" in schneider.lead
    # Un vrai signalement, pour que l'opérateur n'oublie pas de vérifier le conservateur concerné.
    assert any("plusieurs conservateurs" in g.message for g in schneider.flags)
    assert schneider.alerts == {"PISTE_MULTI_CONSERVATEURS"}
    assert schneider.priority == "a_relever"


def test_pas_de_signalement_si_un_seul_conservateur():
    (schneider,) = _breaks(run(files()), SCHNEIDER)
    assert schneider.flags == []


# A. Opération non dénouée à sa date prévue : défaut de règlement-livraison, risque CSDR.
def test_denouement_depasse_signale(tmp_path):
    db = modified_db(tmp_path, "UPDATE mouvements SET date_denouement = '2026-09-24' WHERE id = 19")
    result = run(files(), db=db)
    assert "DENOUEMENT_DEPASSE" in rules(result, "SIGNALE")
    (schneider,) = _breaks(result, SCHNEIDER)
    assert any("CSDR" in g.message for g in schneider.flags)
    assert "CSDR" in schneider.alerts and schneider.priority == "critique"


# B. Une position nulle est une absence : pas de suspens pour 0 titre.
def test_position_nulle_ne_cree_pas_de_suspens():
    pms = (DATA_DIR / PMS).read_bytes() + b"2026-09-25;SC-ACT-01;FR0000120271;TOTAL;0;CACEIS\r\n"
    result = run(files(pms=pms))
    assert len(result.breaks) == 7


# C. Une ligne en double bloque : additionnée, elle pourrait égaler le PMS et masquer un écart.
def test_doublon_b_bloquant():
    line = "DORAFR0000014078000000001000000\r\n"
    b = replace_in(B, (line, line + line), ("T000013", "T000014"))
    result = run(files(b=b))
    assert result.status == "BLOQUE"
    assert "DOUBLON" in rules(result, "BLOQUANT")


def test_doublon_a_bloquant():
    result = run(files(a=xlsx_a(duplicate=4)))
    assert result.status == "BLOQUE"
    assert "DOUBLON" in rules(result, "BLOQUANT")


SFIL_LOT_1 = (
    '<Dim prop="CODE_ISIN">FR0000051641</Dim><Dim prop="LIBELLE_TITRE">SFIL 3% 2033</Dim>'
    '<Dim prop="QUANTITE">50000,00</Dim><Dim prop="LOT">1</Dim></Item>'
)


def _sfil_bis(action: str) -> bytes:
    """Un second item SFIL (même lot) qui, additionné, égalerait le PMS (100 000) : l'écart disparaîtrait."""
    bis = f'<Item><Dim prop="ACTION">{action}</Dim><Dim prop="COMPTE">ORS-OBL</Dim>{SFIL_LOT_1}'
    return replace_in(
        C, (SFIL_LOT_1, SFIL_LOT_1 + bis), ("<NbItems>9</NbItems>", "<NbItems>10</NbItems>")
    )


def test_lot_c_en_double_bloquant_plutot_que_masquer_l_ecart():
    result = run(files(c=_sfil_bis("C")))
    assert result.status == "BLOQUE"
    assert "DOUBLON" in rules(result, "BLOQUANT")


def test_lots_c_distincts_additionnes():
    (hermes,) = [p for p in run(files()).breaks if p.isin == "FR0000052052"] or [None]
    assert hermes is None  # 10 000 (lot 1) + 15 000 (lot 2) = 25 000, comme le PMS


def test_action_c_inconnue_bloquante_plutot_que_masquer_l_ecart():
    result = run(files(c=_sfil_bis("X")))
    assert result.status == "BLOQUE"
    assert "ACTION_INCONNUE" in rules(result, "BLOQUANT")


# Deux fichiers pour une même source : lequel est le bon ? On refuse.
def test_deux_fichiers_meme_source_bloquant():
    upload = files()
    upload["depositaire_A_20260925_v2.xlsx"] = upload[A]
    result = run(upload)
    assert result.status == "BLOQUE"
    assert "FICHIERS_MULTIPLES" in rules(result, "BLOQUANT")


# La priorité se lit dans des champs structurés, jamais dans le texte des messages (libellés humains).
def test_isin_invalide_alerte():
    (edf_invalid,) = _breaks(run(files()), "FR0000012966")
    assert edf_invalid.alerts == {"ISIN_INVALIDE"}


def _qty(**fields) -> Break:
    return Break(
        "ORSAY ACTIONS EUROPE",
        SCHNEIDER,
        "A",
        "QTE",
        Decimal(250000),
        Decimal(225000),
        "SCHNEIDER",
        [],
        **fields,
    )


def test_priorite_independante_des_libelles():
    assert _qty(lead="tout est couvert", explanation="totale").priority == "en_attente"
    assert _qty(flags=[Flag("CSDR", "livraison en retard")]).priority == "critique"
    # Les anciens mots-clés dans le texte, sans le champ structuré, ne décident plus rien.
    assert _qty(lead="écart entièrement expliqué").priority == "a_relever"
    assert _qty(flags=[Flag("ISIN_INVALIDE", "risque CSDR")]).priority == "a_relever"
    assert _qty(explanation="totale", flags=[Flag("ISIN_INVALIDE", "")]).priority == "a_relever"
    custodian_positions = _qty(explanation="totale")
    custodian_positions.type = "DEP"
    assert custodian_positions.priority == "a_relever"


def test_reformuler_les_messages_ne_change_pas_la_priorite(monkeypatch):
    expected = {(s.isin, s.custodian): s.priority for s in run(files()).breaks}
    lead = db_context.lead

    def rephrased_lead(*args):
        _, explanation = lead(*args)
        return "libellé reformulé", explanation

    monkeypatch.setattr(db_context, "lead", rephrased_lead)
    result = run(files())
    assert {s.lead for s in result.breaks} <= {"", "libellé reformulé"}
    assert {(s.isin, s.custodian): s.priority for s in result.breaks} == expected


def test_achat_de_ligne_nouvelle_non_denoue_en_attente(tmp_path):
    """Reproduit en revue : EDF absent chez A, entièrement expliqué par un achat en attente."""
    db = modified_db(
        tmp_path,
        "INSERT INTO mouvements VALUES (99, '2026-09-25', '2026-09-29', 'OBL',"
        " 'FR0000011488', 'ACHAT', 40000, 100, 'X', 'EN_ATTENTE')",
    )
    (edf,) = _breaks(run(files(), db=db), "FR0000011488")
    assert (edf.type, edf.explanation, edf.priority) == ("ABS_DEP", "totale", "en_attente")
