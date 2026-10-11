"""Un test par piège : fichiers altérés en mémoire, niveau attendu dans le journal."""

import io
import zipfile

import pytest

from middle_office.domain.reconciliation import engine
from middle_office.domain.reconciliation.sources import is_valid_isin
from tests.factory import (
    PMS,
    B,
    C,
    files,
    modified_client_config,
    replace_in,
    rules,
    run,
    xlsx_a,
)


def test_fichiers_du_jour_non_bloques():
    result = run(files())
    assert result.status == "OK"
    assert rules(result, "BLOQUANT") == set()


def test_normalisations_tracees():
    result = run(files())
    assert {
        "ISIN_FORMAT",
        "LIBELLE_CONSERVATEUR",
        "SEPARATEUR_MILLIERS",
        "DECIMALES_IMPLICITES",
        "VIRGULE_DECIMALE",
    } <= rules(result, "NORMALISE")
    isin = next(a for a in result.cleaning_log if a.rule == "ISIN_FORMAT")
    assert isin.raw == " fr0000014078 " and isin.kept == "FR0000014078"


def test_isin_cle_invalide_signale():
    assert is_valid_isin("FR0000012965")
    assert not is_valid_isin("FR0000012966")
    result = run(files())
    flagged = [a for a in result.cleaning_log if a.rule == "ISIN_CLE_INVALIDE"]
    assert [a.kept for a in flagged] == ["FR0000012966"]
    breaks = next(s for s in result.breaks if s.isin == "FR0000012966")
    assert any("clé invalide" in g.message for g in breaks.flags)


def test_isin_hors_referentiel_signale():
    result = run(files())
    outside = {a.kept for a in result.cleaning_log if a.rule == "ISIN_HORS_REFERENTIEL"}
    assert "FR0000012966" in outside


@pytest.mark.parametrize(
    "file, before, after, rule",
    [
        (
            "pms",
            "2026-09-25;SC-ACT-01; fr0000014078",
            "2026-09-24;SC-ACT-01; fr0000014078",
            "DATE_ARRETE",
        ),
        ("pms", "SC-OBL-01;FR0000011488", "SC-XXX-01;FR0000011488", "TRANSCO"),
        ("pms", ";40000;CACEIS BANK", ";4O000;CACEIS BANK", "QUANTITE_ILLISIBLE"),
        ("pms", ";5000;Euroclear\r\n", ";5000;SOCIETE GENERALE\r\n", "CONSERVATEUR_INCONNU"),
        ("b", "H20260925", "H20260924", "DATE_ARRETE"),
        ("b", "T000013", "T000012", "TOTAL_CONTROLE"),
        ("b", "DOROFR0000010373", "DXXXFR0000010373", "TRANSCO"),
        ("c", "<DateArrete>25092026", "<DateArrete>24092026", "DATE_ARRETE"),
        ("c", "<NbItems>9</NbItems>", "<NbItems>8</NbItems>", "TOTAL_CONTROLE"),
        (
            "c",
            'xmlns="urn:orsay:depositaire-c:positions:2026"',
            'xmlns="urn:autre"',
            "DATE_ARRETE",  # rien n'est lu hors namespace : date introuvable, donc pas AUCUNE_LIGNE
        ),
        ("c", '<Dim prop="COMPTE">ORS-PAT</Dim>', "", "CHAMP_MANQUANT"),
        ("c", "ORS-OBL", "ORS-XXX", "TRANSCO"),
    ],
)
def test_piege_bloquant(file, before, after, rule):
    name = {"pms": PMS, "b": B, "c": C}[file]
    result = run(files(**{file: replace_in(name, (before, after))}))
    assert result.status == "BLOQUE"
    assert rule in rules(result, "BLOQUANT")
    assert result.breaks == []
    assert all(a.remedy for a in result.cleaning_log if a.level == "BLOQUANT")


def test_a_date_arrete_bloquante():
    result = run(files(a=xlsx_a(security="RELEVE - ARRETE DU 24/09/2026")))
    assert "DATE_ARRETE" in rules(result, "BLOQUANT")


def test_a_quantite_illisible_bloquante():
    result = run(files(a=xlsx_a(quantity="dix mille")))
    assert "QUANTITE_ILLISIBLE" in rules(result, "BLOQUANT")


def test_fichier_manquant_bloquant():
    upload = files()
    del upload[B]
    result = run(upload)
    assert "FICHIER_MANQUANT" in rules(result, "BLOQUANT")


def test_libelle_different_signale_sans_bloquer():
    content = replace_in(C, ("DASSAULT SYSTEMES", "DASSAULT AVIATION"))
    result = run(files(c=content))
    assert result.status == "OK"
    assert "LIBELLE_DIFFERENT" in rules(result, "SIGNALE")


# Revue étape 2 : une donnée ne sort pas de nulle part, et ne disparaît pas sans trace.
def test_ligne_a_vide_ignoree():
    result = run(files(a=xlsx_a(add=[None, None, " ", None])))
    assert result.status == "OK"


def test_ligne_a_incomplete_bloquante():
    result = run(files(a=xlsx_a(add=[None, "FR0000010001", "OAT 2.5% 2030", "1 000"])))
    assert "LIGNE_INCOMPLETE" in rules(result, "BLOQUANT")


def test_ligne_b_vide_ignoree():
    result = run(files(b=replace_in(B, ("T000013", "\r\nT000013"))))
    assert result.status == "OK"


def test_ligne_b_type_inconnu_bloquante():
    result = run(files(b=replace_in(B, ("T000013", "XORAFR0000014078000000001000000\r\nT000013"))))
    assert "TYPE_LIGNE_INCONNU" in rules(result, "BLOQUANT")


def test_isin_vide_pms_bloquant():
    result = run(files(pms=replace_in(PMS, (" fr0000014078 ", ""))))
    assert "LIGNE_INCOMPLETE" in rules(result, "BLOQUANT")


def test_valeur_vide_c_bloquante():
    result = run(files(c=replace_in(C, ('"CODE_ISIN">FR0000050007', '"CODE_ISIN">'))))
    assert "CHAMP_MANQUANT" in rules(result, "BLOQUANT")


@pytest.mark.parametrize("quantity", ["10.000", "-10000"])
def test_quantite_non_entiere_ou_negative_signalee(quantity):
    result = run(files(pms=replace_in(PMS, (";VINCI;10000;", f";VINCI;{quantity};"))))
    assert result.status == "OK"
    assert "QUANTITE_SUSPECTE" in rules(result, "SIGNALE")


def test_parametrage_type_manquant_bloquant(tmp_path):
    def remove_dep(ws):
        ws.delete_rows(next(c.row for c in ws["A"] if c.value == "DEP"))

    config = modified_client_config(tmp_path, "TYPES_ECARTS", remove_dep)
    result = run(files(), config=config)
    assert result.status == "BLOQUE"
    assert "PARAMETRAGE" in rules(result, "BLOQUANT")


def test_parametrage_transco_contradictoire_bloquante(tmp_path):
    config = modified_client_config(
        tmp_path, "TRANSCO_SOUS_COMPTES", lambda ws: ws.append(["SC-PAT-01", "ORSAY OBLIGATIONS"])
    )
    result = run(files(), config=config)
    assert "PARAMETRAGE" in rules(result, "BLOQUANT")


@pytest.mark.parametrize("key", ["a", "c"])
@pytest.mark.parametrize(
    "corruption", [b"", b"bonjour", bytes(range(256)) * 4, b"PK\x03\x04tronque"]
)
def test_fichier_corrompu_refuse_avec_remede(key, corruption):
    result = run(files(**{key: corruption}))
    assert result.status == "BLOQUE"
    (refusal,) = [a for a in result.cleaning_log if a.rule == "FORMAT_ILLISIBLE"]
    assert refusal.remedy


def test_zip_qui_n_est_pas_un_classeur_refuse():
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("autre.txt", "pas un classeur")
    assert "FORMAT_ILLISIBLE" in rules(run(files(a=output.getvalue())), "BLOQUANT")


def test_bug_de_l_outil_n_est_pas_deguise_en_fichier_illisible(monkeypatch):
    """Une erreur de programmation doit remonter (500 tracé), pas dire « redéposez le fichier »."""

    def buggy_reader(*_):
        raise TypeError("bug")

    monkeypatch.setitem(engine.READERS, "B", ("depositaire_B", buggy_reader))
    with pytest.raises(TypeError):
        run(files())


def test_parametrage_action_vide_bloquante(tmp_path):
    def clear_action(ws):
        ws.cell(next(c.row for c in ws["A"] if c.value == "QTE"), 3).value = None

    result = run(files(), config=modified_client_config(tmp_path, "TYPES_ECARTS", clear_action))
    assert "PARAMETRAGE" in rules(result, "BLOQUANT")


def test_bloquant_dit_quoi_faire():
    result = run(files(pms=replace_in(PMS, ("SC-OBL-01;FR0000011488", "SC-XXX-01;FR0000011488"))))
    (mapping,) = [a for a in result.cleaning_log if a.rule == "TRANSCO"]
    assert "SC-XXX-01" in mapping.remedy and "TRANSCO_SOUS_COMPTES" in mapping.remedy


def test_encodage_latin1_trace():
    text = (replace_in(PMS, (";VINCI;", ";VINCI É;"))).decode()
    result = run(files(pms=text.encode("latin-1")))
    assert result.status == "OK"
    assert "ENCODAGE" in rules(result, "NORMALISE")


def test_entete_csv_incomplete_bloquante():
    result = run(files(pms=replace_in(PMS, (";quantite;", ";qte;"))))
    (format_,) = [a for a in result.cleaning_log if a.rule == "FORMAT"]
    assert "quantite" in format_.reason
