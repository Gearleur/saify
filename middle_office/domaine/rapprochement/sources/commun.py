"""Ce que partagent les lecteurs : positions normalisées, journal de nettoyage, lecture des champs.

Une donnée n'apparaît ni ne disparaît sans trace : chaque transformation est notée à l'un des quatre
niveaux NORMALISE (sens inchangé), EXCLU (règle client), SIGNALE (douteux, conservé), BLOQUANT (refusé).
"""

import csv
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation

from openpyxl.utils.exceptions import InvalidFileException

# Ce qu'un fichier mal formé peut lever à la lecture (vérifié sur des fichiers vides, binaires,
# tronqués, en UTF-16). Le reste est un bug de l'outil : il doit remonter, pas devenir « fichier illisible ».
ERREURS_DE_FORMAT = (
    ValueError,
    KeyError,
    IndexError,
    EOFError,
    csv.Error,
    ET.ParseError,
    zipfile.BadZipFile,
    InvalidFileException,
)
# Ce que l'opérateur doit faire quand un fichier est refusé : un blocage doit être actionnable.
REMEDES = {
    "DATE_ARRETE": "Redemander le fichier arrêté à la bonne date à son émetteur, puis relancer",
    "TOTAL_CONTROLE": "Fichier tronqué ou altéré : le redemander au conservateur, puis relancer",
    "QUANTITE_ILLISIBLE": "Corriger la quantité de la ligne citée à la source, puis relancer",
    "CONSERVATEUR_INCONNU": "Corriger le libellé de dépositaire « {brut} » dans le PMS, puis relancer",
    "LIGNE_INCOMPLETE": "Compléter ou supprimer la ligne citée à la source, puis relancer",
    "TYPE_LIGNE_INCONNU": "Type d'enregistrement inconnu : vérifier le format avec le conservateur",
    "CHAMP_MANQUANT": "Item incomplet : redemander le fichier au conservateur, puis relancer",
    "DOUBLON": "Ligne en double : faire confirmer la position par son émetteur, supprimer le doublon, puis relancer",
    "ACTION_INCONNUE": "Code ACTION inconnu : vérifier sa signification avec le conservateur avant de relancer",
    "FORMAT": "Le format du fichier a changé : le vérifier avec son émetteur avant de relancer",
    "FORMAT_ILLISIBLE": "Redéposer le fichier d'origine, sans l'ouvrir ni le réenregistrer",
    "AUCUNE_LIGNE": "Aucune position lue : vérifier qu'il s'agit du bon fichier et du bon format",
    "FICHIER_MANQUANT": "Déposer le fichier manquant, puis relancer",
    "FICHIERS_MULTIPLES": "Ne déposer qu'un fichier par source, puis relancer",
    "PARAMETRAGE": "Corriger parametrage.xlsx comme indiqué, puis relancer",
}


@dataclass(frozen=True)
class Position:
    source: str  # PMS, A, B, C
    entite: str  # nom d'entité du paramétrage, ex. ORSAY OBLIGATIONS
    isin: str
    conservateur: str  # A, B, C
    quantite: Decimal
    libelle: str
    fichier: str
    ligne: int  # numéro de ligne (n° d'Item pour le XML C)

    @property
    def ref(self) -> str:
        return f"{self.fichier}:{self.ligne}"


@dataclass(frozen=True)
class Anomalie:
    fichier: str
    ligne: int
    niveau: str  # NORMALISE, EXCLU, SIGNALE, BLOQUANT
    regle: str
    brut: str
    retenu: str
    motif: str
    remede: str = ""  # renseigné pour tout BLOQUANT : quoi faire pour débloquer


def anomalie(
    fichier: str,
    ligne: int,
    niveau: str,
    regle: str,
    brut,
    retenu,
    motif: str,
    remede: str | None = None,
) -> Anomalie:
    if remede is None and niveau == "BLOQUANT":
        remede = REMEDES[regle].format(brut=brut)
    return Anomalie(fichier, ligne, niveau, regle, str(brut), str(retenu), motif, remede or "")


@dataclass
class Lecture:
    fichier: str
    positions: list[Position] = field(default_factory=list)
    journal: list[Anomalie] = field(default_factory=list)
    _vues: set[tuple] = field(default_factory=set)

    def noter(
        self,
        niveau: str,
        regle: str,
        ligne: int,
        brut,
        retenu,
        motif: str,
        remede: str | None = None,
    ) -> None:
        self.journal.append(
            anomalie(self.fichier, ligne, niveau, regle, brut, retenu, motif, remede)
        )

    # Un raccourci par niveau : l'appel dit d'emblée s'il refuse, écarte, corrige ou signale.
    def bloquer(
        self,
        regle: str,
        ligne: int,
        brut,
        motif: str,
        *,
        retenu: object = "",
        remede: str | None = None,
    ) -> None:
        self.noter("BLOQUANT", regle, ligne, brut, retenu, motif, remede)

    def exclure(self, regle: str, ligne: int, brut, motif: str) -> None:
        self.noter("EXCLU", regle, ligne, brut, "", motif)

    def normaliser(self, regle: str, ligne: int, brut, retenu, motif: str) -> None:
        self.noter("NORMALISE", regle, ligne, brut, retenu, motif)

    def signaler(self, regle: str, ligne: int, brut, retenu, motif: str) -> None:
        self.noter("SIGNALE", regle, ligne, brut, retenu, motif)

    def transco_absente(self, ligne: int, valeur: str, table: str) -> None:
        self.noter(
            "BLOQUANT",
            "TRANSCO",
            ligne,
            valeur,
            "",
            f"« {valeur} » absent de {table}",
            f"Ajouter « {valeur} » à la table {table} de parametrage.xlsx, puis relancer",
        )

    def ajouter(
        self,
        source: str,
        entite: str,
        isin: str,
        conservateur: str,
        quantite: Decimal,
        libelle: str,
        ligne: int,
        compte: str,
    ) -> None:
        """`compte` : identifiant de ligne côté source (pour C : compte et numéro de lot). Deux lignes
        au même (compte, ISIN) bloquent : additionnées, elles pourraient égaler le PMS et masquer
        un écart ; en garder une, ce serait deviner laquelle est la bonne."""
        cle = (compte, isin, conservateur)
        if cle in self._vues:
            self.noter(
                "BLOQUANT",
                "DOUBLON",
                ligne,
                f"{compte} {isin}",
                "",
                "ligne en double (même compte et ISIN) : laquelle est la bonne ?",
            )
            return
        self._vues.add(cle)
        if quantite < 0 or quantite != quantite.to_integral_value():
            self.noter(
                "SIGNALE",
                "QUANTITE_SUSPECTE",
                ligne,
                quantite,
                quantite,
                "quantité négative ou non entière : à confirmer",
            )
        self.positions.append(
            Position(source, entite, isin, conservateur, quantite, libelle, self.fichier, ligne)
        )


def isin_valide(isin: str) -> bool:
    """Format ISO 6166 et clé de Luhn (lettres converties en nombres, A=10 … Z=35)."""
    if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", isin):
        return False
    chiffres = "".join(str(int(c, 36)) for c in isin)
    total = 0
    for i, c in enumerate(reversed(chiffres)):
        n = int(c) * (2 if i % 2 else 1)
        total += n - 9 if n > 9 else n
    return total % 10 == 0


def lire_decimal(texte: str) -> Decimal | None:
    try:
        valeur = Decimal(texte)
    except InvalidOperation:
        return None
    return valeur if valeur.is_finite() else None


def signaler_separateur_ambigu(lecture: Lecture, ligne: int, brut: str) -> None:
    """« 10.000 » se lit 10 mais veut sans doute dire 10 000 : la valeur est gardée, un humain confirme."""
    if re.search(r"\d[.,]\d{3}$", brut.strip()):
        lecture.signaler(
            "QUANTITE_SUSPECTE",
            ligne,
            brut,
            brut,
            "séparateur suivi de 3 chiffres : séparateur de milliers probable",
        )


def est_vide(valeur) -> bool:
    return valeur is None or str(valeur).strip() == ""


def normaliser_isin(lecture: Lecture, ligne: int, brut: str) -> str:
    isin = re.sub(r"\s", "", brut).upper()
    if isin != brut:
        lecture.normaliser("ISIN_FORMAT", ligne, brut, isin, "espaces et casse retirés")
    return isin


def controler_date(
    lecture: Lecture, ligne: int, lue: date | None, attendue: date | None, brut
) -> None:
    """`attendue` None : la date de référence n'a pas pu être établie, ce blocage est déjà tracé."""
    if attendue is not None and lue != attendue:
        lecture.bloquer(
            "DATE_ARRETE",
            ligne,
            brut,
            f"date d'arrêté {lue or 'introuvable'} ≠ {attendue:%d/%m/%Y}",
        )


def decoder_texte(lecture: Lecture, contenu: bytes) -> str:
    try:
        return contenu.decode("utf-8-sig")
    except UnicodeDecodeError:
        lecture.normaliser("ENCODAGE", 0, "non UTF-8", "latin-1", "fichier décodé en latin-1")
        return contenu.decode("latin-1")
