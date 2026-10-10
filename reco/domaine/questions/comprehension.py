"""Comprendre la question d'un gérant : quelle entrée du catalogue, avec quels paramètres.

Le LLM (Claude Haiku 5.5) ne reçoit que la question, jamais de données de la base, et ne renvoie
qu'une intention typée, validée par pydantic. Sans clé, en panne ou en cas de refus : repli par
mots-clés. Sous le seuil de confiance : aucun chiffre, un « Attention » et des reformulations.
"""

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Literal

import anthropic
from pydantic import BaseModel, ValidationError

from reco.domaine.questions import catalogue
from reco.domaine.questions.base import connexion_lecture_seule
from reco.domaine.questions.modeles import Reponse

log = logging.getLogger("reco.questions")

MODELE = "claude-haiku-5-5"
SEUIL_CONFIANCE = 0.7
FONDS = {"PAT": "ORSAY PATRIMOINE", "OBL": "ORSAY OBLIGATIONS", "ACT": "ORSAY ACTIONS EUROPE"}
Intention = Literal["ENCOURS", "ECHEANCES", "CONCENTRATION", "NON_DENOUEES", "ORIGINE_SUSPENS", "HORS_CATALOGUE"]  # fmt: skip

SYSTEME = """Tu classes les questions des gérants et du contrôle d'Orsay Gestion (société de gestion) \
pour un outil qui interroge leur base de gestion. Tu ne réponds jamais à la question et tu ne \
produis aucun chiffre : tu choisis seulement l'entrée du catalogue et ses paramètres.

Catalogue :
- ENCOURS : encours valorisé (au cours de clôture) d'un fonds ou de tous les fonds.
- ECHEANCES : tombées d'échéances à venir (titres qui arrivent à maturité), horizon en mois facultatif.
- CONCENTRATION : concentration par émetteur d'un fonds (le fonds est obligatoire).
- NON_DENOUEES : opérations non dénouées (en attente de règlement-livraison).
- ORIGINE_SUSPENS : origine d'un suspens de rapprochement sur un titre (donne le nom du titre ou son ISIN).
- HORS_CATALOGUE : tout le reste.

Fonds : PAT = Orsay Patrimoine (diversifié), OBL = Orsay Obligations (taux), ACT = Orsay Actions Europe.
`confiance` entre 0 et 1 : baisse-la si la question est ambiguë, mélange plusieurs demandes ou sort du \
catalogue. Dans ces cas, propose 2 ou 3 `reformulations` courtes, en français, qui correspondent \
exactement à des entrées du catalogue."""


class IntentionLLM(BaseModel):
    """Sortie structurée attendue de Claude, validée par pydantic avant tout usage."""

    intention: Intention
    fonds: Literal["PAT", "OBL", "ACT"] | None
    horizon_mois: int | None
    titre: str | None
    confiance: float
    reformulations: list[str]


@dataclass
class Comprehension:
    intention: str
    fonds: str | None = None
    horizon_mois: int | None = None
    isin: str | None = None
    source: str = "mots_cles"  # llm ou mots_cles
    confiance: float = 0.0
    reformulations: list[str] = field(default_factory=list)
    detail: str = ""  # pourquoi le LLM n'a pas été utilisé, le cas échéant

    def trace(self) -> dict:
        return {"intention": self.intention, "fonds": self.fonds, "horizon_mois": self.horizon_mois,
                "isin": self.isin, "source": self.source, "confiance": self.confiance, "detail": self.detail}  # fmt: skip


def _normaliser(texte: str) -> str:
    sans_accents = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    return sans_accents.lower()


def resoudre_titre(base: Path, texte: str | None) -> str | None:
    """ISIN écrit tel quel, sinon le libellé du référentiel le plus long contenu dans le texte."""
    if not texte:
        return None
    isin = re.search(r"\b[A-Z]{2}[A-Z0-9]{9}\d\b", texte.upper())
    if isin:
        return isin.group()
    cible = _normaliser(texte)
    with connexion_lecture_seule(base) as db:
        titres = db.execute("SELECT isin, libelle FROM titres").fetchall()
    trouves = [(len(libelle), isin) for isin, libelle in titres if _normaliser(libelle) in cible]
    return max(trouves)[1] if trouves else None


MOTS_CLES = {
    "ENCOURS": r"encours|valoris|\baum\b|actif net",
    "ECHEANCES": r"echeance|tombee|maturite|rembours",
    "CONCENTRATION": r"concentration|emetteur",
    "NON_DENOUEES": r"denoue|denouement|en attente|reglement.livraison",
    "ORIGINE_SUSPENS": r"suspens",
}
MOTS_FONDS = {
    "PAT": r"\bpat\b|patrimoine",
    "OBL": r"\bobl\b|orsay obligations|fonds obligataire",
    "ACT": r"\bact\b|actions europe|fonds actions",
}


def _par_mots_cles(question: str, base: Path, detail: str = "") -> Comprehension:
    texte = _normaliser(question)
    intentions = [i for i, motif in MOTS_CLES.items() if re.search(motif, texte)]
    fonds = [f for f, motif in MOTS_FONDS.items() if re.search(motif, texte)]
    horizon = None
    if duree := re.search(r"(\d+)\s*(mois|ans?\b)", texte):
        horizon = int(duree.group(1)) * (1 if duree.group(2) == "mois" else 12)
    nette = len(intentions) == 1 and len(fonds) <= 1
    return Comprehension(
        intention=intentions[0] if nette else "HORS_CATALOGUE",
        fonds=fonds[0] if len(fonds) == 1 else None,
        horizon_mois=horizon,
        isin=resoudre_titre(base, question),
        source="mots_cles",
        confiance=0.8 if nette else 0.3,
        detail=detail,
    )


def _systeme(date_ref: date | None) -> str:
    if date_ref is None:
        return SYSTEME
    # Une date, pas une donnée client : sans elle, « d'ici la fin de l'année » ne se convertit pas en mois.
    return (f"{SYSTEME}\n\nDate de référence : {date_ref:%d/%m/%Y}. Convertis toute échéance relative "
            "(« d'ici la fin de l'année », « au prochain trimestre ») en `horizon_mois` entier compté depuis "
            "cette date, arrondi au mois supérieur.")  # fmt: skip


def _par_llm(
    question: str, base: Path, client, date_ref: date | None = None
) -> Comprehension | str:
    """Une Comprehension, ou la raison pour laquelle le LLM n'est pas exploitable."""
    try:
        reponse = client.messages.parse(
            model=MODELE,
            max_tokens=1024,
            system=_systeme(date_ref),
            messages=[{"role": "user", "content": question}],
            output_format=IntentionLLM,
        )
    except anthropic.APIConnectionError as exc:
        return f"LLM indisponible (connexion : {type(exc).__name__})"
    except anthropic.RateLimitError:
        return "LLM indisponible (limite de débit)"
    except anthropic.APIStatusError as exc:
        return f"LLM indisponible (HTTP {exc.status_code})"
    except ValidationError:
        return "LLM indisponible (sortie non conforme au schéma)"
    if reponse.stop_reason == "refusal" or reponse.parsed_output is None:
        return f"LLM sans réponse exploitable ({reponse.stop_reason})"
    sortie: IntentionLLM = reponse.parsed_output
    horizon = (
        sortie.horizon_mois if sortie.horizon_mois and 1 <= sortie.horizon_mois <= 120 else None
    )
    return Comprehension(
        intention=sortie.intention,
        fonds=sortie.fonds,
        horizon_mois=horizon,
        isin=resoudre_titre(base, sortie.titre) or resoudre_titre(base, question),
        source="llm",
        confiance=max(0.0, min(1.0, sortie.confiance)),
        reformulations=sortie.reformulations[:3],
    )


def comprendre(
    question: str, base: Path, client=None, date_ref: date | None = None
) -> Comprehension:
    if client is None:
        return _par_mots_cles(question, base)
    resultat = _par_llm(question, base, client, date_ref)
    if isinstance(resultat, str):
        log.warning("comprehension : repli par mots-clés, %s", resultat)
        return _par_mots_cles(question, base, detail=resultat)
    return resultat


ECRITURE = r"\b(supprim|modifi|ajout|effac|corrig|insere|annul|change|mets? a jour|mettre a jour)"
CATALOGUE_PAR_DEFAUT = ["Encours valorisé du fonds OBL", "Tombées d'échéances à venir dans les 12 mois",
                        "Opérations non dénouées"]  # fmt: skip


def _blocage(c: Comprehension, question: str) -> tuple[str, list[str]] | None:
    """Raison de ne pas répondre et reformulations proposées ; None si on peut répondre."""
    if c.intention == "HORS_CATALOGUE" and re.search(ECRITURE, _normaliser(question)):
        return ("cet outil est en lecture seule : il ne modifie jamais l'inventaire (ni positions, ni "
                "opérations). Une correction se saisit dans le PMS.", CATALOGUE_PAR_DEFAUT)  # fmt: skip
    if c.intention == "CONCENTRATION" and c.fonds is None:
        return ("la concentration par émetteur se lit fonds par fonds : précisez le fonds.",
                [f"Concentration par émetteur du fonds {code}" for code in ("OBL", "PAT", "ACT")])  # fmt: skip
    if c.intention == "ORIGINE_SUSPENS" and c.isin is None:
        return ("je n'ai pas reconnu le titre : précisez son nom ou son ISIN.",
                ["D'où vient le suspens sur SCHNEIDER ?", "D'où vient le suspens sur FR0000051641 ?"])  # fmt: skip
    if c.intention == "HORS_CATALOGUE":
        return ("je ne sais pas répondre à cette question de façon fiable. Je sais calculer : encours "
                "valorisé, tombées d'échéances, concentration par émetteur, opérations non dénouées, "
                "origine d'un suspens.", CATALOGUE_PAR_DEFAUT)  # fmt: skip
    if c.confiance < SEUIL_CONFIANCE:
        return ("je ne suis pas sûr d'avoir compris la question, et je ne donne pas de chiffre sans en être sûr.",
                CATALOGUE_PAR_DEFAUT)  # fmt: skip
    return None


def repondre(question: str, base: Path, date_ref: date, client=None,
             suspens: list[dict] | None = None, id_rapprochement: str | None = None) -> Reponse:  # fmt: skip
    c = comprendre(question, base, client, date_ref)
    log.info(
        "question comprise : intention=%s source=%s confiance=%.2f",
        c.intention,
        c.source,
        c.confiance,
    )
    if blocage := _blocage(c, question):
        motif, par_defaut = blocage
        # Une reformulation du LLM n'est proposée que si elle mène vraiment au catalogue.
        sures = [
            r for r in c.reformulations if _par_mots_cles(r, base).intention != "HORS_CATALOGUE"
        ]
        reponse = Reponse(f"Attention : {motif}", [], "", {}, [], confiance="basse",
                          reformulations=(sures or par_defaut)[:3])  # fmt: skip
    elif c.intention == "ENCOURS":
        reponse = catalogue.encours_valorise(base, c.fonds, date_ref)
    elif c.intention == "ECHEANCES":
        reponse = catalogue.echeances(base, c.fonds, date_ref, c.horizon_mois)
    elif c.intention == "CONCENTRATION":
        reponse = catalogue.concentration_emetteurs(base, c.fonds, date_ref)
    elif c.intention == "NON_DENOUEES":
        reponse = catalogue.operations_non_denouees(base, c.fonds, date_ref)
    else:
        reponse = catalogue.origine_suspens(base, c.isin, suspens, id_rapprochement)
    reponse.question = question
    reponse.comprehension = c.trace()
    return reponse
