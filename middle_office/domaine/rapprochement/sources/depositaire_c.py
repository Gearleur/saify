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


def lire_depositaire_c(
    nom: str, contenu: bytes, param: Parametrage, date_arrete: date | None
) -> Lecture:
    """XML à namespace ; les lots distincts d'un même (compte, ISIN) sont additionnés, un lot répété bloque."""
    lecture = Lecture(nom)
    if _dtd_present(contenu):  # avant tout parsing : entités externes, « billion laughs »
        lecture.bloquer(
            "FORMAT",
            0,
            "",
            "DOCTYPE ou ENTITY interdit dans le XML conservateur : fichier refusé par sécurité",
        )
        return lecture
    racine = ET.fromstring(contenu)
    brut_date = racine.findtext(".//c:DateArrete", "", NS_C).strip()
    try:
        lue = date(int(brut_date[4:8]), int(brut_date[2:4]), int(brut_date[0:2]))
    except ValueError:
        lue = None
    controler_date(lecture, 0, lue, date_arrete, brut_date)

    items = racine.findall(".//c:Item", NS_C)
    nb_items = racine.findtext(".//c:NbItems", "", NS_C).strip()
    if nb_items != str(len(items)):  # NbItems compte aussi les annulations
        lecture.bloquer(
            "TOTAL_CONTROLE",
            0,
            nb_items,
            f"NbItems {nb_items!r} ≠ {len(items)} Item lus",
            retenu=len(items),
        )

    for num, item in enumerate(items, start=1):
        dims = {dim.get("prop"): (dim.text or "").strip() for dim in item.iterfind("c:Dim", NS_C)}
        manquants = [p for p in PROPS_C if p not in dims or (p != "LIBELLE_TITRE" and not dims[p])]
        if manquants:
            lecture.bloquer(
                "CHAMP_MANQUANT", num, dims, f"Dim manquant ou vide : {', '.join(manquants)}"
            )
            continue
        if dims["ACTION"] == "S":
            lecture.exclure(
                "ANNULATION_S", num, dims, "item annulé (ACTION=S), ni ajouté ni soustrait"
            )
            continue
        if dims["ACTION"] not in ACTIONS_C:
            # Ni additionné (il pourrait combler un écart) ni écarté (il pourrait en créer un) : refusé.
            lecture.bloquer(
                "ACTION_INCONNUE",
                num,
                dims["ACTION"],
                f"ACTION « {dims['ACTION']} » inconnue (attendu : C ou S)",
            )
            continue
        if dims["COMPTE"] not in param.comptes_c:
            lecture.transco_absente(num, dims["COMPTE"], "TRANSCO_DEPOSITAIRE_C")
            continue
        brut = dims["QUANTITE"]
        qte = lire_decimal(brut.replace(",", "."))
        signaler_separateur_ambigu(lecture, num, brut)
        if qte is None:
            lecture.bloquer("QUANTITE_ILLISIBLE", num, brut, "quantité non numérique")
            continue
        if "," in brut:
            lecture.normaliser("VIRGULE_DECIMALE", num, brut, qte, "virgule décimale")
        lecture.ajouter(
            "C",
            param.comptes_c[dims["COMPTE"]],
            normaliser_isin(lecture, num, dims["CODE_ISIN"]),
            "C",
            qte,
            dims["LIBELLE_TITRE"],
            num,
            compte=f"{dims['COMPTE']} lot {dims['LOT']}",
        )
    return lecture
