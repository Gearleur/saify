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


def lire_depositaire_a(
    nom: str, contenu: bytes, param: Parametrage, date_arrete: date | None
) -> Lecture:
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
        compte, isin, designation, quantite = (list(cellules) + [None] * 4)[:4]
        if all(est_vide(v) for v in cellules):
            continue
        if est_vide(compte) or est_vide(isin) or est_vide(quantite):
            lecture.bloquer("LIGNE_INCOMPLETE", num, cellules, "compte, ISIN ou quantité vide")
            continue
        compte = str(compte).strip()
        if compte not in param.comptes_a:
            lecture.transco_absente(num, compte, "TRANSCO_DEPOSITAIRE_A")
            continue
        brut = str(quantite)
        qte = lire_decimal(re.sub(r"\s", "", brut))
        signaler_separateur_ambigu(lecture, num, brut)
        if qte is None:
            lecture.bloquer("QUANTITE_ILLISIBLE", num, brut, "quantité non numérique")
            continue
        if brut != str(qte):
            lecture.normaliser("SEPARATEUR_MILLIERS", num, brut, qte, "quantité texte → nombre")
        lecture.ajouter(
            "A",
            param.comptes_a[compte],
            normaliser_isin(lecture, num, str(isin)),
            "A",
            qte,
            str(designation or "").strip(),
            num,
            compte=compte,
        )
    return lecture
