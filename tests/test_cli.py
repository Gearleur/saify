"""Ligne de commande : sortie lisible et code de sortie exploitable par une tâche planifiée."""

import shutil

from middle_office.__main__ import main
from tests.factory import DATA_DIR


def test_cli_rapprochement_fait(capsys):
    assert main([str(DATA_DIR)]) == 0
    output = capsys.readouterr().out
    assert "Statut : OK · 7 suspens" in output and "FR0000051641" in output


def test_cli_rapprochement_bloque_sort_en_erreur(tmp_path, capsys):
    for file in DATA_DIR.iterdir():
        if not file.name.startswith("depositaire_C"):
            shutil.copy(file, tmp_path)
    assert main([str(tmp_path)]) == 1
    assert "FICHIER_MANQUANT" in capsys.readouterr().out
