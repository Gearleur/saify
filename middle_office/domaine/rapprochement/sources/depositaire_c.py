"""Conservateur C (BNP Paribas, BP2S) : XML à namespace, lots, annulations, NbItems de contrôle."""

import xml.etree.ElementTree as ET
from datetime import date

from middle_office.domaine.rapprochement.sources.commun import (
    Lecture,
    controler_date,
    lire_decimal,
    normaliser_isin,
    signaler_separateur_ambigu,
)
from middle_office.domaine.rapprochement.sources.parametrage import Parametrage

NS_C = {"c": "urn:orsay:depositaire-c:positions:2026"}
PROPS_C = ("ACTION", "COMPTE", "CODE_ISIN", "LIBELLE_TITRE", "QUANTITE", "LOT")


ACTIONS_C = {"C", "S"}  # C : position, S : annulation


def _dtd_present(contenu: bytes) -> bool:
    """Cherche aussi dans la version UTF-16, qu'expat accepterait avec un BOM."""
    textes = [contenu.upper()]
    if contenu[:2] in (b"\xff\xfe", b"\xfe\xff"):
        textes.append(contenu.decode("utf-16", errors="replace").upper().encode())
    return any(b"<!DOCTYPE" in t or b"<!ENTITY" in t for t in textes)


def _controler_entete(
    lecture: Lecture, racine: ET.Element, nb_lus: int, date_arrete: date | None
) -> None:
    """Date d'arrêté (JJMMAAAA) et NbItems, qui compte aussi les annulations."""
    brut_date = racine.findtext(".//c:DateArrete", "", NS_C).strip()
    try:
        lue = date(int(brut_date[4:8]), int(brut_date[2:4]), int(brut_date[0:2]))
    except ValueError:
        lue = None
    controler_date(lecture, 0, lue, date_arrete, brut_date)
    nb_items = racine.findtext(".//c:NbItems", "", NS_C).strip()
    if nb_items != str(nb_lus):
        lecture.bloquer(
            "TOTAL_CONTROLE",
            0,
            nb_items,
            f"NbItems {nb_items!r} ≠ {nb_lus} Item lus",
            retenu=nb_lus,
        )


def _lire_item(lecture: Lecture, num: int, dims: dict, param: Parametrage) -> None:
    manquants = [p for p in PROPS_C if p not in dims or (p != "LIBELLE_TITRE" and not dims[p])]
    if manquants:
        lecture.bloquer(
            "CHAMP_MANQUANT", num, dims, f"Dim manquant ou vide : {', '.join(manquants)}"
        )
        return
    if dims["ACTION"] == "S":
        lecture.exclure("ANNULATION_S", num, dims, "item annulé (ACTION=S), ni ajouté ni soustrait")
        return
    if dims["ACTION"] not in ACTIONS_C:
        # Ni additionné (il pourrait combler un écart) ni écarté (il pourrait en créer un) : refusé.
        motif = f"ACTION « {dims['ACTION']} » inconnue (attendu : C ou S)"
        lecture.bloquer("ACTION_INCONNUE", num, dims["ACTION"], motif)
        return
    if dims["COMPTE"] not in param.comptes_c:
        lecture.transco_absente(num, dims["COMPTE"], "TRANSCO_DEPOSITAIRE_C")
        return
    brut = dims["QUANTITE"]
    qte = lire_decimal(brut.replace(",", "."))
    signaler_separateur_ambigu(lecture, num, brut)
    if qte is None:
        lecture.bloquer("QUANTITE_ILLISIBLE", num, brut, "quantité non numérique")
        return
    if "," in brut:
        lecture.normaliser("VIRGULE_DECIMALE", num, brut, qte, "virgule décimale")
    isin = normaliser_isin(lecture, num, dims["CODE_ISIN"])
    entite, compte = param.comptes_c[dims["COMPTE"]], f"{dims['COMPTE']} lot {dims['LOT']}"
    lecture.ajouter("C", entite, isin, "C", qte, dims["LIBELLE_TITRE"], num, compte=compte)


def lire_depositaire_c(
    nom: str, contenu: bytes, param: Parametrage, date_arrete: date | None
) -> Lecture:
    """XML à namespace ; les lots distincts d'un même (compte, ISIN) sont additionnés, un lot répété bloque."""
    lecture = Lecture(nom)
    if _dtd_present(contenu):  # avant tout parsing : entités externes, « billion laughs »
        motif = "DOCTYPE ou ENTITY interdit dans le XML conservateur : fichier refusé par sécurité"
        lecture.bloquer("FORMAT", 0, "", motif)
        return lecture
    racine = ET.fromstring(contenu)
    items = racine.findall(".//c:Item", NS_C)
    _controler_entete(lecture, racine, len(items), date_arrete)
    for num, item in enumerate(items, start=1):
        dims = {dim.get("prop"): (dim.text or "").strip() for dim in item.iterfind("c:Dim", NS_C)}
        _lire_item(lecture, num, dims, param)
    return lecture
