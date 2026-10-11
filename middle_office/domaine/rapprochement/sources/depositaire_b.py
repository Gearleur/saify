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


def _lire_detail(lecture: Lecture, num: int, ligne: str, param: Parametrage) -> None:
    """D + desk(3) + ISIN(12) + quantité(15, 2 décimales implicites) : 31 caractères exactement."""
    desk, isin, brut = ligne[1:4], ligne[4:16], ligne[16:31]
    if len(ligne) != 31:
        lecture.bloquer("FORMAT", num, ligne, "ligne de détail de longueur ≠ 31")
        return
    if desk not in param.desks_b:
        lecture.transco_absente(num, desk, "TRANSCO_DEPOSITAIRE_B")
        return
    if not brut.isdigit():
        lecture.bloquer("QUANTITE_ILLISIBLE", num, brut, "quantité non numérique")
        return
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


def lire_depositaire_b(
    nom: str, contenu: bytes, param: Parametrage, date_arrete: date | None
) -> Lecture:
    """Largeur fixe : H+date, lignes de détail D, puis T + nombre de lignes de détail (contrôle)."""
    lecture = Lecture(nom)
    lignes = decoder_texte(lecture, contenu).splitlines()
    entete = next((ligne for ligne in lignes if ligne.startswith("H")), "")
    try:
        lue = date(int(entete[1:5]), int(entete[5:7]), int(entete[7:9]))
    except ValueError:
        lue = None
    controler_date(lecture, 1, lue, date_arrete, entete)

    details, controle = 0, None
    for num, ligne in enumerate(lignes, start=1):
        if not ligne.strip():
            continue
        if ligne[0] not in "HDT":
            lecture.bloquer(
                "TYPE_LIGNE_INCONNU", num, ligne, f"enregistrement de type « {ligne[0]} »"
            )
        elif ligne[0] == "T":
            controle = ligne
        elif ligne[0] == "D":
            details += 1
            _lire_detail(lecture, num, ligne, param)

    if controle is None or not controle[1:].isdigit() or int(controle[1:]) != details:
        motif = f"total de contrôle {controle!r} ≠ {details} lignes de détail"
        lecture.bloquer("TOTAL_CONTROLE", len(lignes), controle, motif, retenu=details)
    return lecture
