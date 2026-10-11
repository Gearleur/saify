"""Conservateur A (CACEIS) : classeur Excel, titre daté, quantités parfois en texte."""

import io
import re
from contextlib import closing
from datetime import date

import openpyxl

from middle_office.domaine.rapprochement.sources.commun import (
    Lecture,
    controler_date,
    est_vide,
    lire_decimal,
    normaliser_isin,
    signaler_separateur_ambigu,
)
from middle_office.domaine.rapprochement.sources.parametrage import Parametrage


def _lire_ligne(lecture: Lecture, num: int, cellules: tuple, param: Parametrage) -> None:
    compte, isin, designation, quantite = (list(cellules) + [None] * 4)[:4]
    if all(est_vide(v) for v in cellules):
        return
    if est_vide(compte) or est_vide(isin) or est_vide(quantite):
        lecture.bloquer("LIGNE_INCOMPLETE", num, cellules, "compte, ISIN ou quantité vide")
        return
    compte = str(compte).strip()
    if compte not in param.comptes_a:
        lecture.transco_absente(num, compte, "TRANSCO_DEPOSITAIRE_A")
        return
    brut = str(quantite)
    qte = lire_decimal(re.sub(r"\s", "", brut))
    signaler_separateur_ambigu(lecture, num, brut)
    if qte is None:
        lecture.bloquer("QUANTITE_ILLISIBLE", num, brut, "quantité non numérique")
        return
    if brut != str(qte):
        lecture.normaliser("SEPARATEUR_MILLIERS", num, brut, qte, "quantité texte → nombre")
    isin, libelle = normaliser_isin(lecture, num, str(isin)), str(designation or "").strip()
    lecture.ajouter("A", param.comptes_a[compte], isin, "A", qte, libelle, num, compte=compte)


def lire_depositaire_a(
    nom: str, contenu: bytes, param: Parametrage, date_arrete: date | None
) -> Lecture:
    """Classeur : titre daté (JJ/MM/AAAA), puis un tableau sous l'en-tête « Compte »."""
    lecture = Lecture(nom)
    with closing(openpyxl.load_workbook(io.BytesIO(contenu), read_only=True, data_only=True)) as wb:
        lignes = list(wb.worksheets[0].iter_rows(values_only=True))

    titre = str(lignes[0][0] or "") if lignes else ""
    trouvee = re.search(r"(\d{2})/(\d{2})/(\d{4})", titre)
    lue = date(int(trouvee[3]), int(trouvee[2]), int(trouvee[1])) if trouvee else None
    controler_date(lecture, 1, lue, date_arrete, titre)

    entete = next((i for i, ligne in enumerate(lignes) if ligne and ligne[0] == "Compte"), None)
    if entete is None:
        lecture.bloquer("FORMAT", 0, "", "en-tête « Compte » introuvable")
        return lecture
    for num, cellules in enumerate(lignes[entete + 1 :], start=entete + 2):
        _lire_ligne(lecture, num, cellules, param)
    return lecture
