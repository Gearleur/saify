"""Ligne de commande : sortie lisible et code de sortie exploitable par une tâche planifiée."""

import shutil

from middle_office.__main__ import main
from tests.fabrique import DONNEES


def test_cli_rapprochement_fait(capsys):
    assert main([str(DONNEES)]) == 0
    sortie = capsys.readouterr().out
    assert "Statut : OK · 7 suspens" in sortie and "FR0000051641" in sortie


def test_cli_rapprochement_bloque_sort_en_erreur(tmp_path, capsys):
    for fichier in DONNEES.iterdir():
        if not fichier.name.startswith("depositaire_C"):
            shutil.copy(fichier, tmp_path)
    assert main([str(tmp_path)]) == 1
    assert "FICHIER_MANQUANT" in capsys.readouterr().out
