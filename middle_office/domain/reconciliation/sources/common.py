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
FORMAT_ERRORS = (
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
REMEDIES = {
    "DATE_ARRETE": "Redemander le fichier arrêté à la bonne date à son émetteur, puis relancer",
    "TOTAL_CONTROLE": "Fichier tronqué ou altéré : le redemander au conservateur, puis relancer",
    "QUANTITE_ILLISIBLE": "Corriger la quantité de la ligne citée à la source, puis relancer",
    "CONSERVATEUR_INCONNU": "Corriger le libellé de dépositaire « {raw} » dans le PMS, puis relancer",
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
    entity: str  # nom d'entité du paramétrage, ex. ORSAY OBLIGATIONS
    isin: str
    custodian: str  # A, B, C
    quantity: Decimal
    label: str
    file: str
    line: int  # numéro de ligne (n° d'Item pour le XML C)

    @property
    def ref(self) -> str:
        return f"{self.file}:{self.line}"


@dataclass(frozen=True)
class Anomaly:
    file: str
    line: int
    level: str  # NORMALISE, EXCLU, SIGNALE, BLOQUANT
    rule: str
    raw: str
    kept: str
    reason: str
    remedy: str = ""  # renseigné pour tout BLOQUANT : quoi faire pour débloquer


def anomaly(
    file: str,
    line: int,
    level: str,
    rule: str,
    raw,
    kept,
    reason: str,
    remedy: str | None = None,
) -> Anomaly:
    if remedy is None and level == "BLOQUANT":
        remedy = REMEDIES[rule].format(raw=raw)
    return Anomaly(file, line, level, rule, str(raw), str(kept), reason, remedy or "")


@dataclass
class SourceReading:
    file: str
    positions: list[Position] = field(default_factory=list)
    cleaning_log: list[Anomaly] = field(default_factory=list)
    _seen: set[tuple] = field(default_factory=set)

    def note(
        self,
        level: str,
        rule: str,
        line: int,
        raw,
        kept,
        reason: str,
        remedy: str | None = None,
    ) -> None:
        self.cleaning_log.append(anomaly(self.file, line, level, rule, raw, kept, reason, remedy))

    # Un raccourci par niveau : l'appel dit d'emblée s'il refuse, écarte, corrige ou signale.
    def block(
        self,
        rule: str,
        line: int,
        raw,
        reason: str,
        *,
        kept: object = "",
        remedy: str | None = None,
    ) -> None:
        self.note("BLOQUANT", rule, line, raw, kept, reason, remedy)

    def exclude(self, rule: str, line: int, raw, reason: str) -> None:
        self.note("EXCLU", rule, line, raw, "", reason)

    def normalize(self, rule: str, line: int, raw, kept, reason: str) -> None:
        self.note("NORMALISE", rule, line, raw, kept, reason)

    def flag(self, rule: str, line: int, raw, kept, reason: str) -> None:
        self.note("SIGNALE", rule, line, raw, kept, reason)

    def missing_mapping(self, line: int, value: str, table: str) -> None:
        self.note(
            "BLOQUANT",
            "TRANSCO",
            line,
            value,
            "",
            f"« {value} » absent de {table}",
            f"Ajouter « {value} » à la table {table} de parametrage.xlsx, puis relancer",
        )

    def add(
        self,
        source: str,
        entity: str,
        isin: str,
        custodian: str,
        quantity: Decimal,
        label: str,
        line: int,
        account: str,
    ) -> None:
        """`compte` : identifiant de ligne côté source (pour C : compte et numéro de lot). Deux lignes
        au même (compte, ISIN) bloquent : additionnées, elles pourraient égaler le PMS et masquer
        un écart ; en garder une, ce serait deviner laquelle est la bonne."""
        key = (account, isin, custodian)
        if key in self._seen:
            self.note(
                "BLOQUANT",
                "DOUBLON",
                line,
                f"{account} {isin}",
                "",
                "ligne en double (même compte et ISIN) : laquelle est la bonne ?",
            )
            return
        self._seen.add(key)
        if quantity < 0 or quantity != quantity.to_integral_value():
            self.note(
                "SIGNALE",
                "QUANTITE_SUSPECTE",
                line,
                quantity,
                quantity,
                "quantité négative ou non entière : à confirmer",
            )
        self.positions.append(
            Position(source, entity, isin, custodian, quantity, label, self.file, line)
        )


def is_valid_isin(isin: str) -> bool:
    """Format ISO 6166 et clé de Luhn (lettres converties en nombres, A=10 … Z=35)."""
    if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", isin):
        return False
    figures = "".join(str(int(c, 36)) for c in isin)
    total = 0
    for i, c in enumerate(reversed(figures)):
        n = int(c) * (2 if i % 2 else 1)
        total += n - 9 if n > 9 else n
    return total % 10 == 0


def parse_decimal(text: str) -> Decimal | None:
    try:
        value = Decimal(text)
    except InvalidOperation:
        return None
    return value if value.is_finite() else None


def flag_ambiguous_separator(reading: SourceReading, line: int, raw: str) -> None:
    """« 10.000 » se lit 10 mais veut sans doute dire 10 000 : la valeur est gardée, un humain confirme."""
    if re.search(r"\d[.,]\d{3}$", raw.strip()):
        reading.flag(
            "QUANTITE_SUSPECTE",
            line,
            raw,
            raw,
            "séparateur suivi de 3 chiffres : séparateur de milliers probable",
        )


def is_blank(value) -> bool:
    return value is None or str(value).strip() == ""


def normalize_isin(reading: SourceReading, line: int, raw: str) -> str:
    isin = re.sub(r"\s", "", raw).upper()
    if isin != raw:
        reading.normalize("ISIN_FORMAT", line, raw, isin, "espaces et casse retirés")
    return isin


def check_date(
    reading: SourceReading, line: int, read_date: date | None, expected: date | None, raw
) -> None:
    """`attendue` None : la date de référence n'a pas pu être établie, ce blocage est déjà tracé."""
    if expected is not None and read_date != expected:
        reading.block(
            "DATE_ARRETE",
            line,
            raw,
            f"date d'arrêté {read_date or 'introuvable'} ≠ {expected:%d/%m/%Y}",
        )


def decode_text(reading: SourceReading, content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError:
        reading.normalize("ENCODAGE", 0, "non UTF-8", "latin-1", "fichier décodé en latin-1")
        return content.decode("latin-1")
