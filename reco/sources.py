"""Lecture des sources (PMS, conservateurs A/B/C, paramétrage) en positions normalisées.

Chaque parseur rend des `Position` en `Decimal` et ajoute au journal ce qu'il a écarté.
"""

import csv
import io
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

import openpyxl

SOUS_COMPTES_EXCLUS = {"P3G"}
NS_C = {"c": "urn:orsay:depositaire-c:positions:2026"}


@dataclass(frozen=True)
class Position:
    source: str  # PMS, A, B, C
    entite: str  # nom d'entité du paramétrage, ex. ORSAY OBLIGATIONS
    isin: str
    conservateur: str  # A, B, C
    quantite: Decimal
    libelle: str
    ref: str  # fichier:ligne


@dataclass(frozen=True)
class Anomalie:
    fichier: str
    ligne: int
    niveau: str  # NORMALISE, EXCLU, SIGNALE, BLOQUANT
    regle: str
    brut: str
    retenu: str
    motif: str


@dataclass
class Parametrage:
    sous_comptes: dict[str, str]
    comptes_a: dict[str, str]
    desks_b: dict[str, str]
    comptes_c: dict[str, str]
    types_ecarts: dict[str, tuple[str, str]]  # code -> (libellé, action attendue)


@dataclass
class Lecture:
    positions: list[Position] = field(default_factory=list)
    journal: list[Anomalie] = field(default_factory=list)


def lire_parametrage(chemin: Path) -> Parametrage:
    wb = openpyxl.load_workbook(chemin, read_only=True, data_only=True)

    def table(nom: str) -> list[tuple]:
        lignes = list(wb[nom].iter_rows(values_only=True))
        return [ligne for ligne in lignes[1:] if ligne[0] is not None]

    def transco(nom: str) -> dict[str, str]:
        return {str(cle).strip(): str(entite).strip() for cle, entite, *_ in table(nom)}

    return Parametrage(
        sous_comptes=transco("TRANSCO_SOUS_COMPTES"),
        comptes_a=transco("TRANSCO_DEPOSITAIRE_A"),
        desks_b=transco("TRANSCO_DEPOSITAIRE_B"),
        comptes_c=transco("TRANSCO_DEPOSITAIRE_C"),
        types_ecarts={
            code: (libelle, action) for code, libelle, action, *_ in table("TYPES_ECARTS")
        },
    )


def code_conservateur(libelle: str) -> str:
    """CACEIS -> A, EUROCLEAR -> B, BNP/BP2S -> C (insensible à la casse)."""
    haut = libelle.upper()
    if "CACEIS" in haut:
        return "A"
    if "EUROCLEAR" in haut:
        return "B"
    if "BNP" in haut or "BP2S" in haut:
        return "C"
    raise ValueError(f"libellé de conservateur inconnu : {libelle!r}")


def _texte(contenu: bytes) -> str:
    try:
        return contenu.decode("utf-8-sig")
    except UnicodeDecodeError:
        return contenu.decode("latin-1")


def lire_pms(nom: str, contenu: bytes, param: Parametrage) -> Lecture:
    lecture = Lecture()
    lignes = csv.DictReader(io.StringIO(_texte(contenu), newline=""), delimiter=";")
    for num, ligne in enumerate(lignes, start=2):
        sous_compte = (ligne["sous_compte"] or "").strip()
        brut = ";".join(v or "" for v in ligne.values())
        if not sous_compte:
            lecture.journal.append(
                Anomalie(
                    nom,
                    num,
                    "EXCLU",
                    "SANS_SOUS_COMPTE",
                    brut,
                    "",
                    "ligne sans sous-compte : anomalie de saisie",
                )
            )
            continue
        if sous_compte in SOUS_COMPTES_EXCLUS:
            lecture.journal.append(
                Anomalie(nom, num, "EXCLU", "P3G", brut, "", "compte technique de passage exclu")
            )
            continue
        lecture.positions.append(
            Position(
                source="PMS",
                entite=param.sous_comptes[sous_compte],
                isin=ligne["isin"].strip().upper(),
                conservateur=code_conservateur(ligne["depositaire"]),
                quantite=Decimal(ligne["quantite"].strip()),
                libelle=ligne["libelle"].strip(),
                ref=f"{nom}:{num}",
            )
        )
    return lecture


def lire_depositaire_a(nom: str, contenu: bytes, param: Parametrage) -> Lecture:
    lecture = Lecture()
    wb = openpyxl.load_workbook(io.BytesIO(contenu), read_only=True, data_only=True)
    lignes = list(wb.worksheets[0].iter_rows(values_only=True))
    entete = next(i for i, ligne in enumerate(lignes) if ligne[0] == "Compte")
    for num, (compte, isin, designation, quantite, *_) in enumerate(
        lignes[entete + 1 :], start=entete + 2
    ):
        if compte is None:
            continue
        lecture.positions.append(
            Position(
                source="A",
                entite=param.comptes_a[str(compte).strip()],
                isin=str(isin).strip().upper(),
                conservateur="A",
                quantite=Decimal(re.sub(r"\s", "", str(quantite))),
                libelle=str(designation).strip(),
                ref=f"{nom}:{num}",
            )
        )
    return lecture


def lire_depositaire_b(nom: str, contenu: bytes, param: Parametrage) -> Lecture:
    """Largeur fixe : D + desk(3) + ISIN(12) + quantité(15, 2 décimales implicites)."""
    lecture = Lecture()
    for num, ligne in enumerate(_texte(contenu).splitlines(), start=1):
        if not ligne.startswith("D"):
            continue
        lecture.positions.append(
            Position(
                source="B",
                entite=param.desks_b[ligne[1:4]],
                isin=ligne[4:16].upper(),
                conservateur="B",
                quantite=Decimal(ligne[16:31]).scaleb(-2),
                libelle="",
                ref=f"{nom}:{num}",
            )
        )
    return lecture


def lire_depositaire_c(nom: str, contenu: bytes, param: Parametrage) -> Lecture:
    """XML à namespace ; les lots d'un même (compte, ISIN) sont additionnés au rapprochement."""
    lecture = Lecture()
    racine = ET.fromstring(contenu)
    for num, item in enumerate(racine.iterfind(".//c:Item", NS_C), start=1):
        dims = {dim.get("prop"): (dim.text or "").strip() for dim in item.iterfind("c:Dim", NS_C)}
        if dims["ACTION"] == "S":
            lecture.journal.append(
                Anomalie(
                    nom,
                    num,
                    "EXCLU",
                    "ANNULATION_S",
                    str(dims),
                    "",
                    "item annulé (ACTION=S), ni ajouté ni soustrait",
                )
            )
            continue
        lecture.positions.append(
            Position(
                source="C",
                entite=param.comptes_c[dims["COMPTE"]],
                isin=dims["CODE_ISIN"].upper(),
                conservateur="C",
                quantite=Decimal(dims["QUANTITE"].replace(",", ".")),
                libelle=dims["LIBELLE_TITRE"],
                ref=f"{nom}:item {num}",
            )
        )
    return lecture
