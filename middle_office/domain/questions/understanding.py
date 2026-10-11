"""Comprendre la question d'un gérant : quelle entrée du catalogue, avec quels paramètres.

Le LLM (Claude Haiku 5.5) ne reçoit que la question, jamais de données de la base, et ne renvoie
qu'une intention typée, validée par pydantic. Sans clé, en panne ou en cas de refus : repli par
mots-clés. Sous le seuil de confiance : aucun chiffre, un « Attention » et des reformulations.
"""

import logging
import re
from datetime import date
from pathlib import Path
from typing import Literal

import anthropic
from pydantic import BaseModel, ValidationError

from middle_office.domain.questions import catalog
from middle_office.domain.questions.dates import cited_date, cited_end
from middle_office.domain.questions.intent import Understanding
from middle_office.domain.questions.models import Answer, ReconciliationContext
from middle_office.domain.questions.refusal import refusal_reason
from middle_office.domain.questions.securities import cited_securities
from middle_office.domain.questions.text import normalize

log = logging.getLogger("middle_office.questions")

MODEL = "claude-haiku-5-5"
Intent = Literal[
    "ENCOURS", "ECHEANCES", "CONCENTRATION", "NON_DENOUEES", "ORIGINE_SUSPENS", "HORS_CATALOGUE"
]

SYSTEM_PROMPT = """Tu classes les questions des gérants et du contrôle d'Orsay Gestion (société de gestion) \
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
`confidence` entre 0 et 1 : baisse-la si la question est ambiguë, mélange plusieurs demandes ou sort du \
catalogue. Dans ces cas, propose 2 ou 3 `suggestions` courtes, en français, qui correspondent \
exactement à des entrées du catalogue.
`requested_date` : si la question vise une date précise ou passée pour un encours, une concentration ou \
des opérations (« hier », « au 31/12/2025 », « la semaine dernière »), donne-la au format AAAA-MM-JJ ; \
sinon null. Une échéance à venir se traduit en `horizon_months`, pas en `requested_date`."""


class LlmUnavailable(Exception):
    """Levée par l'encadrement de l'API (budget, concurrence, modèle) : on se replie sur les mots-clés."""


class LlmIntent(BaseModel):
    """Sortie structurée attendue de Claude, validée par pydantic avant tout usage."""

    intent: Intent
    fund: Literal["PAT", "OBL", "ACT"] | None
    horizon_months: int | None
    security: str | None
    confidence: float
    suggestions: list[str]
    requested_date: str | None = (
        None  # AAAA-MM-JJ si la question vise une autre date que la référence
    )


KEYWORDS = {
    "ENCOURS": r"encours|valoris|\baum\b|actif net",
    "ECHEANCES": r"echeance|tombee|maturite|rembours",
    "CONCENTRATION": r"concentration|emetteur",
    "NON_DENOUEES": r"denoue|denouement|en attente|reglement.livraison",
    "ORIGINE_SUSPENS": r"suspens",
}
FUND_KEYWORDS = {
    "PAT": r"\bpat\b|patrimoine",
    "OBL": r"\bobl\b|orsay obligations|fonds obligataire",
    "ACT": r"\bact\b|actions europe|fonds actions",
}


def _by_keywords(question: str, db_path: Path, detail: str = "") -> Understanding:
    text = normalize(question)
    intents = [i for i, reason in KEYWORDS.items() if re.search(reason, text)]
    fund = [f for f, reason in FUND_KEYWORDS.items() if re.search(reason, text)]
    horizon = None
    if duration := re.search(r"(\d+)\s*(mois|ans?\b)", text):
        horizon = int(duration.group(1)) * (1 if duration.group(2) == "mois" else 12)
    clear = len(intents) == 1 and len(fund) <= 1
    securities = cited_securities(db_path, question)
    return Understanding(
        intent=intents[0] if clear else "HORS_CATALOGUE",
        fund=fund[0] if len(fund) == 1 else None,
        horizon_months=horizon,
        isin=securities[0][0] if len(securities) == 1 else None,
        source="mots_cles",
        confidence=0.8 if clear else 0.3,
        detail=detail,
        requested_date=cited_date(question),
        candidate_securities=securities if len(securities) > 1 else [],
    )


def _system_prompt(ref_date: date | None) -> str:
    if ref_date is None:
        return SYSTEM_PROMPT
    # Une date, pas une donnée client : sans elle, « d'ici la fin de l'année » ne se convertit pas en mois.
    return (
        f"{SYSTEM_PROMPT}\n\nDate de référence : {ref_date:%d/%m/%Y}. Convertis toute échéance relative "
        "(« d'ici la fin de l'année », « au prochain trimestre ») en `horizon_months` entier compté depuis "
        "cette date, arrondi au mois supérieur."
    )


def _by_llm(
    question: str, db_path: Path, client, ref_date: date | None = None
) -> Understanding | str:
    """Une Comprehension, ou la raison pour laquelle le LLM n'est pas exploitable."""
    try:
        answer = client.messages.parse(
            model=MODEL,
            max_tokens=1024,
            system=_system_prompt(ref_date),
            messages=[{"role": "user", "content": question}],
            output_format=LlmIntent,
        )
    except anthropic.APIConnectionError as exc:
        return f"LLM indisponible (connexion : {type(exc).__name__})"
    except anthropic.RateLimitError:
        return "LLM indisponible (limite de débit)"
    except anthropic.APIStatusError as exc:
        return f"LLM indisponible (HTTP {exc.status_code})"
    except ValidationError:
        return "LLM indisponible (sortie non conforme au schéma)"
    except LlmUnavailable as exc:
        return f"LLM indisponible ({exc})"
    if answer.stop_reason == "refusal" or answer.parsed_output is None:
        return f"LLM sans réponse exploitable ({answer.stop_reason})"
    output: LlmIntent = answer.parsed_output
    horizon = (
        output.horizon_months
        if output.horizon_months and 1 <= output.horizon_months <= 120
        else None
    )
    securities = cited_securities(db_path, output.security) or cited_securities(db_path, question)
    try:  # la date du LLM n'est retenue que valide ; la lecture déterministe sert de filet
        llm_date = date.fromisoformat(output.requested_date or "").isoformat()
    except ValueError:
        llm_date = None
    return Understanding(
        intent=output.intent,
        fund=output.fund,
        horizon_months=horizon,
        isin=securities[0][0] if len(securities) == 1 else None,
        source="llm",
        confidence=max(0.0, min(1.0, output.confidence)),
        suggestions=output.suggestions[:3],
        requested_date=llm_date or cited_date(question),
        candidate_securities=securities if len(securities) > 1 else [],
    )


def understand(
    question: str, db_path: Path, client=None, ref_date: date | None = None
) -> Understanding:
    if client is None:
        return _by_keywords(question, db_path)
    result = _by_llm(question, db_path, client, ref_date)
    if isinstance(result, str):
        log.warning("comprehension : repli par mots-clés, %s", result)
        return _by_keywords(question, db_path, detail=result)
    return result


def execute(
    c: Understanding,
    question: str,
    db_path: Path,
    ref_date: date,
    context: ReconciliationContext | None = None,
) -> Answer:
    """Second temps : à partir de l'intention comprise, la requête du catalogue (ou un refus motivé)."""
    if refusal := refusal_reason(c, question, ref_date):
        reason, defaults = refusal
        # Une reformulation du LLM n'est proposée que si elle mène vraiment au catalogue.
        safe = [r for r in c.suggestions if _by_keywords(r, db_path).intent != "HORS_CATALOGUE"]
        answer = Answer(
            f"Attention : {reason}",
            [],
            "",
            {},
            [],
            confidence="basse",
            suggestions=(safe or defaults)[:3],
        )
    elif c.intent == "ENCOURS":
        answer = catalog.fund_valuation(db_path, c.fund, ref_date)
    elif c.intent == "ECHEANCES":
        end = None if c.horizon_months else cited_end(ref_date, c.requested_date)
        answer = catalog.maturities(db_path, c.fund, ref_date, c.horizon_months, c.isin, end)
    elif c.intent == "CONCENTRATION":
        answer = catalog.issuer_concentration(db_path, c.fund, ref_date)
    elif c.intent == "NON_DENOUEES":
        answer = catalog.unsettled_trades(db_path, c.fund, ref_date, c.isin)
    else:
        assert c.isin is not None  # motif_de_refus refuse ORIGINE_SUSPENS sans titre reconnu
        answer = catalog.break_origin(db_path, c.isin, context)
    answer.question = question
    answer.understanding = c.trace()
    return answer


def answer_question(
    question: str,
    db_path: Path,
    ref_date: date,
    client=None,
    context: ReconciliationContext | None = None,
) -> Answer:
    c = understand(question, db_path, client, ref_date)
    return execute(c, question, db_path, ref_date, context)
