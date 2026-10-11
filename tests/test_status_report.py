"""Priorité métier, tri, point de situation et export CSV (étape 3)."""

from decimal import Decimal

from middle_office import reconcile_folder
from middle_office.domain.reconciliation.breaks import Break, Flag, priority
from middle_office.domain.reconciliation.status_report import (
    CSV_COLUMNS,
    breaks_csv,
    build_status_report,
    quantity_text,
)
from tests.factory import DATA_DIR, PMS, C, files, modified_db, replace_in, run

ISINS = {
    "FR0000011488",
    "FR0000012966",
    "FR0000999914",
    "FR0000015927",
    "FR0000051641",
    "FR0000012965",
    "FR0000016297",
}


def _breaks(type_="QTE", explanation="aucune", alerts=None) -> Break:
    return Break(
        "ORSAY OBLIGATIONS",
        "FR0000051641",
        "C",
        type_,
        Decimal(10),
        Decimal(5),
        "SFIL",
        [],
        explanation=explanation,
        flags=[Flag(code, code) for code in alerts or ()],
    )


def test_priorite_critique_si_risque_csdr():
    assert priority(_breaks(explanation="totale", alerts={"CSDR"})) == "critique"


def test_priorite_en_attente_si_qte_entierement_expliquee_sans_signalement():
    assert priority(_breaks(explanation="totale")) == "en_attente"


def test_priorite_a_relever_sinon():
    assert priority(_breaks()) == "a_relever"
    assert priority(_breaks(explanation="partielle")) == "a_relever"
    assert priority(_breaks(explanation="contraire")) == "a_relever"
    explained_but_flagged = _breaks(explanation="totale", alerts={"PISTE_MULTI_CONSERVATEURS"})
    assert priority(explained_but_flagged) == "a_relever"
    assert priority(_breaks("DEP", explanation="totale")) == "a_relever"


def test_absences_entierement_expliquees_en_attente():
    """Achat d'une ligne nouvelle non dénoué (ABS_DEP), vente totale non dénouée (ABS_INT)."""
    assert priority(_breaks("ABS_DEP", explanation="totale")) == "en_attente"
    assert priority(_breaks("ABS_INT", explanation="totale")) == "en_attente"


def test_tri_priorite_puis_entite_type_isin():
    result = reconcile_folder(DATA_DIR)
    order = [(s.priority, s.entity, s.type, s.isin) for s in result.breaks]
    assert [o[0] for o in order] == ["a_relever"] * 5 + ["en_attente"] * 2
    assert order[:5] == sorted(order[:5]) and order[5:] == sorted(order[5:])


def test_csdr_remonte_en_tete(tmp_path):
    db = modified_db(tmp_path, "UPDATE mouvements SET date_denouement = '2026-09-24' WHERE id = 20")
    result = run(files(), db=db)
    assert result.breaks[0].isin == "FR0000016297"
    assert result.breaks[0].priority == "critique"


def test_quantite_texte_sans_float_ni_exposant():
    assert quantity_text(Decimal("25000000").scaleb(-2)) == "250000"
    assert quantity_text(Decimal("-1000.00")) == "-1000"
    assert quantity_text(Decimal("5000.50")) == "5000.5"
    assert quantity_text(Decimal("0.00")) == "0"
    assert quantity_text(None) is None


def test_point_de_situation_complet():
    text = build_status_report(reconcile_folder(DATA_DIR))
    assert text.startswith("Point de situation · rapprochement du 25/09/2026")
    assert "Statut : OK" in text
    for isin in ISINS:
        assert isin in text
    for rule in ("SANS_SOUS_COMPTE", "P3G", "ANNULATION_S"):
        assert rule in text
    assert "25 000" in text  # formater_quantite
    assert "Contacter le dépositaire" in text
    assert "op. n°19 ACHAT 25 000" in text
    assert "ISIN à clé invalide" in text
    assert text.index("À RELEVER") < text.index("EN ATTENTE")


def test_point_de_situation_bloque_donne_le_remede():
    c = replace_in(C, ("<NbItems>9</NbItems>", "<NbItems>8</NbItems>"))
    text = build_status_report(run(files(c=c)))
    assert "BLOQUÉ" in text
    assert "TOTAL_CONTROLE" in text
    assert "redemander au conservateur" in text


def test_csv_suspens():
    content = breaks_csv(reconcile_folder(DATA_DIR).breaks)
    assert content.startswith(b"\xef\xbb\xbf")
    lines = content.decode("utf-8-sig").splitlines()
    assert lines[0] == ";".join(CSV_COLUMNS)
    assert lines[0] == (
        "priorite;fonds;entite;isin;titre;conservateur;type;libelle_type;"
        "qte_pms;qte_conservateur;ecart;action;piste;signalements;sources"
    )
    assert len(lines) == 8
    safran = next(line for line in lines if "FR0000016297" in line).split(";")
    assert safran[0] == "en_attente"
    assert safran[8:11] == ["40000", "41000", "-1000"]


def test_csv_neutralise_les_formules_mais_pas_les_ecarts_negatifs():
    """Reproduit en revue : un libellé PMS « =1+2 » ressortait tel quel, et Excel l'exécutait."""
    pms = replace_in(PMS, (";EDF 4% 2031;", ";=1+2;"))
    lines = breaks_csv(run(files(pms=pms)).breaks).decode("utf-8-sig").splitlines()
    edf = next(line for line in lines if "FR0000011488" in line).split(";")
    assert edf[4] == "'=1+2"
    lvmh = next(line for line in lines if "FR0000999914" in line).split(";")
    assert lvmh[10] == "-30000"  # nombre, pas texte


def test_xml_avec_doctype_bloque():
    c = replace_in(
        C,
        ("<RelevePositions", '<!DOCTYPE RelevePositions [<!ENTITY e "x">]>\n<RelevePositions'),
    )
    result = run(files(c=c))
    assert result.status == "BLOQUE"
    (refusal,) = [a for a in result.cleaning_log if a.rule == "FORMAT"]
    assert refusal.level == "BLOQUANT" and "DOCTYPE" in refusal.reason and refusal.remedy
    # Un seul blocage : « AUCUNE_LIGNE » en plus serait du bruit pour l'opérateur.
    assert [a.rule for a in result.cleaning_log if a.level == "BLOQUANT"] == ["FORMAT"]
