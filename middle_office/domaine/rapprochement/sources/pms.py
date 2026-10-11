"""PMS (positions_internes.csv) : la source interne du rapprochement, par sous-compte."""

import csv
import io
from datetime import date

from middle_office.domaine.rapprochement.sources.commun import (
    Lecture,
    controler_date,
    decoder_texte,
    est_vide,
    lire_decimal,
    normaliser_isin,
    signaler_separateur_ambigu,
)
from middle_office.domaine.rapprochement.sources.parametrage import Parametrage

SOUS_COMPTES_EXCLUS = {"P3G"}
COLONNES_PMS = ("date_arrete", "sous_compte", "isin", "libelle", "quantite", "depositaire")


def code_conservateur(libelle: str) -> str | None:
    """CACEIS -> A, EUROCLEAR -> B, BNP/BP2S -> C (insensible à la casse) ; None si inconnu."""
    haut = libelle.upper()
    if "CACEIS" in haut:
        return "A"
    if "EUROCLEAR" in haut:
        return "B"
    if "BNP" in haut or "BP2S" in haut:
        return "C"
    return None


def dates_pms(contenu: bytes) -> set[str]:
    """Dates d'arrêté distinctes du PMS : la source interne fixe la date du rapprochement."""
    texte = decoder_texte(Lecture(""), contenu)
    lignes = csv.DictReader(io.StringIO(texte, newline=""), delimiter=";")
    return {(ligne.get("date_arrete") or "").strip() for ligne in lignes}


def lire_pms(nom: str, contenu: bytes, param: Parametrage, date_arrete: date | None) -> Lecture:
    lecture = Lecture(nom)
    lignes = csv.DictReader(io.StringIO(decoder_texte(lecture, contenu), newline=""), delimiter=";")
    absentes = [c for c in COLONNES_PMS if c not in (lignes.fieldnames or [])]
    if absentes:
        lecture.bloquer(
            "FORMAT",
            1,
            ";".join(lignes.fieldnames or []),
            f"colonne(s) absente(s) : {', '.join(absentes)}",
        )
        return lecture

    for num, ligne in enumerate(lignes, start=2):
        brut = ";".join(str(v or "") for v in ligne.values())
        try:
            lue = date.fromisoformat((ligne["date_arrete"] or "").strip())
        except ValueError:
            lue = None
        controler_date(lecture, num, lue, date_arrete, brut)

        sous_compte = (ligne["sous_compte"] or "").strip()
        if not sous_compte:
            lecture.exclure(
                "SANS_SOUS_COMPTE", num, brut, "ligne sans sous-compte : anomalie de saisie"
            )
            continue
        if sous_compte in SOUS_COMPTES_EXCLUS:
            lecture.exclure("P3G", num, brut, "compte technique de passage exclu")
            continue
        if sous_compte not in param.sous_comptes:
            lecture.transco_absente(num, sous_compte, "TRANSCO_SOUS_COMPTES")
            continue
        if est_vide(ligne["isin"]):
            lecture.bloquer("LIGNE_INCOMPLETE", num, brut, "ISIN vide")
            continue

        libelle_cons = (ligne["depositaire"] or "").strip()
        conservateur = code_conservateur(libelle_cons)
        if conservateur is None:
            lecture.bloquer(
                "CONSERVATEUR_INCONNU", num, libelle_cons, "libellé de conservateur inconnu"
            )
            continue
        lecture.normaliser(
            "LIBELLE_CONSERVATEUR", num, libelle_cons, conservateur, "libellé → code conservateur"
        )

        quantite = lire_decimal((ligne["quantite"] or "").strip())
        signaler_separateur_ambigu(lecture, num, ligne["quantite"] or "")
        if quantite is None:
            lecture.bloquer("QUANTITE_ILLISIBLE", num, ligne["quantite"], "quantité non numérique")
            continue

        isin = normaliser_isin(lecture, num, ligne["isin"])
        lecture.ajouter(
            "PMS",
            param.sous_comptes[sous_compte],
            isin,
            conservateur,
            quantite,
            (ligne["libelle"] or "").strip(),
            num,
            compte=sous_compte,
        )
    return lecture
