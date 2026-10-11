"""Règles de vigilance sur la concentration par émetteur : seuils internes, simples et modifiables.

Inspirées du ratio 5/10/40 que connaissent les gérants, mais ce ne sont **pas** des contrôles
réglementaires (pas de dérogation pour les émetteurs publics, pas de verdict) : elles attirent
l'attention, le gérant et le RCCI jugent. Les seuils se changent ici, en un seul endroit.
"""

from dataclasses import dataclass
from decimal import Decimal

from middle_office.domain.formats import CENT, percentage
from middle_office.domain.questions.models import Vigilance


def _threshold(value: Decimal) -> str:
    return f"{value.normalize():f}".replace(".", ",") + " %"


@dataclass(frozen=True)
class VigilanceRules:
    issuer_threshold: Decimal = Decimal("10")  # un émetteur au-delà : vigilance
    individual_threshold: Decimal = Decimal("5")  # émetteurs comptés dans le cumul
    cumulative_cap: Decimal = Decimal("40")  # cumul de ces émetteurs au-delà : vigilance

    def description(self) -> list[str]:
        return [
            f"Un émetteur pèse plus de {_threshold(self.issuer_threshold)} de l'encours valorisé du fonds.",
            f"Les émetteurs de plus de {_threshold(self.individual_threshold)} cumulent plus de "
            f"{_threshold(self.cumulative_cap)} de l'encours valorisé du fonds.",
        ]

    def evaluate(self, shares: list[tuple[str, Decimal]], total: Decimal) -> list[Vigilance]:
        """`parts` : (émetteur, montant exact) triés du plus gros au plus petit. Calcul sur les montants
        exacts : additionner des pourcentages arrondis décalerait le cumul."""
        vigilances = []
        share = {issuer: amount / total * 100 for issuer, amount in shares}
        above = [e for e, _ in shares if share[e] > self.issuer_threshold]
        if above:
            detail = ", ".join(f"{e} ({percentage(share[e])})" for e in above)
            vigilances.append(
                Vigilance(
                    "EMETTEUR_AU_DESSUS_DU_SEUIL",
                    f"Au-dessus du seuil de vigilance interne de {_threshold(self.issuer_threshold)} "
                    f"par émetteur : {detail}.",
                    above,
                    share[above[0]].quantize(CENT),
                )
            )
        accounts = [e for e, _ in shares if share[e] > self.individual_threshold]
        cumulative = (
            sum((amount for e, amount in shares if e in accounts), Decimal(0)) / total * 100
        )
        if cumulative > self.cumulative_cap:
            vigilances.append(
                Vigilance(
                    "CUMUL_AU_DESSUS_DU_PLAFOND",
                    f"Les {len(accounts)} émetteurs de plus de {_threshold(self.individual_threshold)} cumulent "
                    f"{percentage(cumulative)} de l'encours, au-delà du seuil de vigilance interne "
                    f"de {_threshold(self.cumulative_cap)}.",
                    accounts,
                    cumulative.quantize(CENT),
                )
            )
        return vigilances


DEFAULT_RULES = VigilanceRules()
