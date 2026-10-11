"""Conservateur B (Euroclear) : fichier à largeur fixe, décimales implicites, total de contrôle."""

from datetime import date
from decimal import Decimal

from middle_office.domaine.rapprochement.sources.commun import (
    Lecture,
    controler_date,
    decoder_texte,
    normaliser_isin,
)
from middle_office.domaine.rapprochement.sources.parametrage import Parametrage


def lire_depositaire_b(
    nom: str, contenu: bytes, param: Parametrage, date_arrete: date | None
) -> Lecture:
    """Largeur fixe : H+date, D + desk(3) + ISIN(12) + quantité(15, 2 décimales implicites), T+nb."""
    lecture = Lecture(nom)
    lignes = decoder_texte(lecture, contenu).splitlines()
    entete = next((ligne for ligne in lignes if ligne.startswith("H")), "")
    try:
        lue = date(int(entete[1:5]), int(entete[5:7]), int(entete[7:9]))
    except ValueError:
        lue = None
    controler_date(lecture, 1, lue, date_arrete, entete)

    details = 0
    controle = None
    for num, ligne in enumerate(lignes, start=1):
        if not ligne.strip():
            continue
        if ligne[0] not in "HDT":
            lecture.bloquer(
                "TYPE_LIGNE_INCONNU", num, ligne, f"enregistrement de type « {ligne[0]} »"
            )
            continue
        if ligne.startswith("T"):
            controle = ligne
        if not ligne.startswith("D"):
            continue
        details += 1
        desk, isin, brut = ligne[1:4], ligne[4:16], ligne[16:31]
        if len(ligne) != 31:
            lecture.bloquer("FORMAT", num, ligne, "ligne de détail de longueur ≠ 31")
            continue
        if desk not in param.desks_b:
            lecture.transco_absente(num, desk, "TRANSCO_DEPOSITAIRE_B")
            continue
        if not brut.isdigit():
            lecture.bloquer("QUANTITE_ILLISIBLE", num, brut, "quantité non numérique")
            continue
        qte = Decimal(brut).scaleb(-2)
        lecture.normaliser("DECIMALES_IMPLICITES", num, brut, qte, "2 décimales implicites")
        lecture.ajouter(
            "B",
            param.desks_b[desk],
            normaliser_isin(lecture, num, isin),
            "B",
            qte,
            "",
            num,
            compte=desk,
        )

    if controle is None or not controle[1:].isdigit() or int(controle[1:]) != details:
        lecture.bloquer(
            "TOTAL_CONTROLE",
            len(lignes),
            controle,
            f"total de contrôle {controle!r} ≠ {details} lignes de détail",
            retenu=details,
        )
    return lecture
