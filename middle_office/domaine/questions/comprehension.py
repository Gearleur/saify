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

from middle_office.domaine.questions import catalogue
from middle_office.domaine.questions.base import connexion_lecture_seule
from middle_office.domaine.questions.modeles import ContexteRapprochement, Reponse

log = logging.getLogger("middle_office.questions")

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
exactement à des entrées du catalogue.
`date_demandee` : si la question vise une date précise ou passée pour un encours, une concentration ou \
des opérations (« hier », « au 31/12/2025 », « la semaine dernière »), donne-la au format AAAA-MM-JJ ; \
sinon null. Une échéance à venir se traduit en `horizon_mois`, pas en `date_demandee`."""


class LLMIndisponible(Exception):
    """Levée par l'encadrement de l'API (budget, concurrence, modèle) : on se replie sur les mots-clés."""


class IntentionLLM(BaseModel):
    """Sortie structurée attendue de Claude, validée par pydantic avant tout usage."""

    intention: Intention
    fonds: Literal["PAT", "OBL", "ACT"] | None
    horizon_mois: int | None
    titre: str | None
    confiance: float
    reformulations: list[str]
    date_demandee: str | None = (
        None  # AAAA-MM-JJ si la question vise une autre date que la référence
    )


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
    # Ce que la question cite et que le catalogue ne sait pas toujours traiter : on refuse plutôt que
    # de répondre à côté (un vrai chiffre, mais d'une autre question).
    date_demandee: str | None = None  # AAAA-MM-JJ, ou l'expression relative trouvée (« hier »)
    titres_candidats: list[tuple[str, str]] = field(
        default_factory=list
    )  # (isin, libellé), si ambigu

    def trace(self) -> dict:
        return {"intention": self.intention, "fonds": self.fonds, "horizon_mois": self.horizon_mois,
                "isin": self.isin, "source": self.source, "confiance": self.confiance, "detail": self.detail,
                "date_demandee": self.date_demandee}  # fmt: skip


def _normaliser(texte: str) -> str:
    sans_accents = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    return sans_accents.lower()


def _pour_titres(texte: str) -> str:
    return _normaliser(texte).replace(",", ".")


def _alias(libelle: str, emetteur: str | None) -> set[str]:
    """Façons de citer un titre : libellé complet, libellé sans coupon ni échéance (« SFIL 3% 2033 »
    → « SFIL »), émetteur. Trois lettres au moins (EDF, RTE, OAT)."""
    court = re.sub(r"\s+\d[\d.,]*\s*%.*$", "", libelle)
    return {a for a in map(_pour_titres, (libelle, court, emetteur or "")) if len(a) >= 3}


def titres_cites(base: Path, texte: str | None) -> list[tuple[str, str]]:
    """(isin, libellé) des titres cités : un ISIN écrit tel quel, sinon les alias trouvés en mots
    entiers. Un alias inclus dans un alias plus long trouvé lui aussi est ignoré (« OAT » dans
    « OAT 2.5% 2030 »). Plusieurs résultats : la question est ambiguë, on ne choisit pas."""
    if not texte:
        return []
    with connexion_lecture_seule(base) as db:
        titres = db.execute("SELECT isin, libelle, emetteur FROM titres").fetchall()
    libelles = {isin: libelle for isin, libelle, _ in titres}
    if isin := re.search(r"\b[A-Z]{2}[A-Z0-9]{9}\d\b", texte.upper()):
        return [(isin.group(), libelles.get(isin.group(), isin.group()))]
    cible = _pour_titres(texte)
    trouves: dict[str, set[str]] = {}
    for isin, libelle, emetteur in titres:
        for alias in _alias(libelle, emetteur):
            if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", cible):
                trouves.setdefault(alias, set()).add(isin)
    retenus = [a for a in trouves if not any(a != b and a in b for b in trouves)]
    isins = set().union(*(trouves[a] for a in retenus))
    return sorted((isin, libelles[isin]) for isin in isins)


def resoudre_titre(base: Path, texte: str | None) -> str | None:
    """L'ISIN du titre cité, s'il n'y en a qu'un."""
    cites = titres_cites(base, texte)
    return cites[0][0] if len(cites) == 1 else None


MOIS = ("janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout", "septembre",
        "octobre", "novembre", "decembre")  # fmt: skip
RELATIVES = r"avant.hier|\bhier\b|la veille|semaine (derniere|passee)|mois (dernier|passe)|trimestre (dernier|passe)|annee (derniere|passee)|an (dernier|passe)"


def date_citee(question: str) -> str | None:
    """Une date explicite (AAAA-MM-JJ) ou une expression relative passée, trouvée dans la question."""
    texte = _normaliser(question)
    for motif, ordre in (
        (r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", "amj"),
        (r"\b(\d{1,2})[/.](\d{1,2})[/.](\d{2,4})\b", "jma"),
    ):
        if m := re.search(motif, texte):
            valeurs = dict(zip(ordre, map(int, m.groups()), strict=True))
            annee = valeurs["a"] + (2000 if valeurs["a"] < 100 else 0)
            try:
                return date(annee, valeurs["m"], valeurs["j"]).isoformat()
            except ValueError:
                return m.group()
    if m := re.search(rf"\b(1er|\d{{1,2}}) ({'|'.join(MOIS)}) (\d{{4}})\b", texte):
        jour = 1 if m[1] == "1er" else int(m[1])
        try:
            return date(int(m[3]), MOIS.index(m[2]) + 1, jour).isoformat()
        except ValueError:
            return m.group()
    if m := re.search(RELATIVES, texte):
        return m.group()
    return None


def fin_citee(date_ref: date, cible: str | None) -> date | None:
    """La date de fin citée pour des échéances (« d'ici le 31/12/2026 »), si elle est future."""
    try:
        fin = date.fromisoformat(cible or "")
    except ValueError:
        return None
    return fin if fin > date_ref else None


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
    titres = titres_cites(base, question)
    return Comprehension(
        intention=intentions[0] if nette else "HORS_CATALOGUE",
        fonds=fonds[0] if len(fonds) == 1 else None,
        horizon_mois=horizon,
        isin=titres[0][0] if len(titres) == 1 else None,
        source="mots_cles",
        confiance=0.8 if nette else 0.3,
        detail=detail,
        date_demandee=date_citee(question),
        titres_candidats=titres if len(titres) > 1 else [],
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
    except LLMIndisponible as exc:
        return f"LLM indisponible ({exc})"
    if reponse.stop_reason == "refusal" or reponse.parsed_output is None:
        return f"LLM sans réponse exploitable ({reponse.stop_reason})"
    sortie: IntentionLLM = reponse.parsed_output
    horizon = (
        sortie.horizon_mois if sortie.horizon_mois and 1 <= sortie.horizon_mois <= 120 else None
    )
    titres = titres_cites(base, sortie.titre) or titres_cites(base, question)
    try:  # la date du LLM n'est retenue que valide ; la lecture déterministe sert de filet
        date_llm = date.fromisoformat(sortie.date_demandee or "").isoformat()
    except ValueError:
        date_llm = None
    return Comprehension(
        intention=sortie.intention,
        fonds=sortie.fonds,
        horizon_mois=horizon,
        isin=titres[0][0] if len(titres) == 1 else None,
        source="llm",
        confiance=max(0.0, min(1.0, sortie.confiance)),
        reformulations=sortie.reformulations[:3],
        date_demandee=date_llm or date_citee(question),
        titres_candidats=titres if len(titres) > 1 else [],
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
# Une demande d'écriture formulée comme un ordre, quel que soit le sujet (« corrige l'encours d'OBL ») ;
# « opérations annulées ? » reste une lecture.
ORDRE_ECRITURE = (r"^(peux.tu |pouvez.vous |merci de |il faut |je veux )?"
                  r"(supprim|modifi|ajout|efface|corrig|insere|annule|change|mets? a jour|mettre a jour|remplac)")  # fmt: skip
DATE_UNIQUE = ("ENCOURS", "CONCENTRATION", "NON_DENOUEES")  # chiffres à la seule date de référence
PAR_TITRE = (
    "ECHEANCES",
    "NON_DENOUEES",
    "ORIGINE_SUSPENS",
)  # intentions qui savent filtrer un titre
CATALOGUE_PAR_DEFAUT = ["Encours valorisé du fonds OBL", "Tombées d'échéances à venir dans les 12 mois",
                        "Opérations non dénouées"]  # fmt: skip


def _question_type(intention: str, fonds: str | None, titre: str | None = None) -> str:
    """Une question du catalogue, formulée pour être reconnue telle quelle (reformulation proposée)."""
    sur = f" sur {titre}" if titre else ""
    return {
        "ENCOURS": f"Encours valorisé du fonds {fonds or 'OBL'}",
        "CONCENTRATION": f"Concentration par émetteur du fonds {fonds or 'OBL'}",
        "NON_DENOUEES": f"Opérations non dénouées{sur}",
        "ECHEANCES": f"Tombées d'échéances à venir{sur}",
        "ORIGINE_SUSPENS": f"D'où vient le suspens{sur} ?",
    }[intention]


def _blocage(c: Comprehension, question: str, date_ref: date) -> tuple[str, list[str]] | None:
    """Raison de ne pas répondre et reformulations proposées ; None si on peut répondre."""
    texte = _normaliser(question).strip()
    if re.search(ORDRE_ECRITURE, texte) or (
        c.intention == "HORS_CATALOGUE" and re.search(ECRITURE, texte)
    ):
        return ("cet outil est en lecture seule : il ne modifie jamais l'inventaire (ni positions, ni "
                "opérations). Une correction se saisit dans le PMS.", CATALOGUE_PAR_DEFAUT)  # fmt: skip
    if c.intention == "CONCENTRATION" and c.fonds is None:
        return ("la concentration par émetteur se lit fonds par fonds : précisez le fonds.",
                [f"Concentration par émetteur du fonds {code}" for code in ("OBL", "PAT", "ACT")])  # fmt: skip
    if c.intention in DATE_UNIQUE and c.date_demandee and c.date_demandee != date_ref.isoformat():
        try:
            visee = f"le {date.fromisoformat(c.date_demandee):%d/%m/%Y}"
        except ValueError:
            visee = f"« {c.date_demandee} »"
        return (f"la base de gestion ne contient que les positions au {date_ref:%d/%m/%Y}, et la question "
                f"vise {visee}. Je ne donne pas le chiffre d'une autre date à la place.",
                [_question_type(c.intention, c.fonds)])  # fmt: skip
    if c.intention == "ENCOURS" and (c.isin or c.titres_candidats):
        return ("l'encours valorisé se calcule par fonds, pas pour un titre seul : je ne réponds pas "
                "à côté de la question.", [f"Encours valorisé du fonds {code}" for code in FONDS])  # fmt: skip
    if c.intention in PAR_TITRE and c.titres_candidats:
        noms = ", ".join(libelle for _, libelle in c.titres_candidats)
        return (f"plusieurs titres correspondent ({noms}) : précisez lequel.",
                [_question_type(c.intention, c.fonds, libelle) for _, libelle in c.titres_candidats[:3]])  # fmt: skip
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


def executer(c: Comprehension, question: str, base: Path, date_ref: date,
             contexte: ContexteRapprochement | None = None) -> Reponse:  # fmt: skip
    """Second temps : à partir de l'intention comprise, la requête du catalogue (ou un refus motivé)."""
    if blocage := _blocage(c, question, date_ref):
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
        fin = None if c.horizon_mois else fin_citee(date_ref, c.date_demandee)
        reponse = catalogue.echeances(base, c.fonds, date_ref, c.horizon_mois, c.isin, fin)
    elif c.intention == "CONCENTRATION":
        reponse = catalogue.concentration_emetteurs(base, c.fonds, date_ref)
    elif c.intention == "NON_DENOUEES":
        reponse = catalogue.operations_non_denouees(base, c.fonds, date_ref, c.isin)
    else:
        reponse = catalogue.origine_suspens(base, c.isin, contexte)
    reponse.question = question
    reponse.comprehension = c.trace()
    return reponse


def repondre(question: str, base: Path, date_ref: date, client=None,
             contexte: ContexteRapprochement | None = None) -> Reponse:  # fmt: skip
    c = comprendre(question, base, client, date_ref)
    return executer(c, question, base, date_ref, contexte)
