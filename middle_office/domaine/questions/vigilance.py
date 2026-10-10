"""Règles de vigilance sur la concentration par émetteur : seuils internes, simples et modifiables.

Inspirées du ratio 5/10/40 que connaissent les gérants, mais ce ne sont **pas** des contrôles
réglementaires (pas de dérogation pour les émetteurs publics, pas de verdict) : elles attirent
l'attention, le gérant et le RCCI jugent. Les seuils se changent ici, en un seul endroit.
"""

from dataclasses import dataclass
from decimal import Decimal

from middle_office.domaine.questions.modeles import Vigilance

CENTIME = Decimal("0.01")


def _pct(valeur: Decimal) -> str:
    texte = f"{valeur.quantize(CENTIME)}".replace(".", ",")
    return f"{texte} %"


def _seuil(valeur: Decimal) -> str:
    return f"{valeur.normalize():f}".replace(".", ",") + " %"


@dataclass(frozen=True)
class ReglesVigilance:
    seuil_emetteur: Decimal = Decimal("10")  # un émetteur au-delà : vigilance
    seuil_cumul_individuel: Decimal = Decimal("5")  # émetteurs comptés dans le cumul
    plafond_cumul: Decimal = Decimal("40")  # cumul de ces émetteurs au-delà : vigilance

    def description(self) -> list[str]:
        return [
            f"Un émetteur pèse plus de {_seuil(self.seuil_emetteur)} de l'encours valorisé du fonds.",
            f"Les émetteurs de plus de {_seuil(self.seuil_cumul_individuel)} cumulent plus de "
            f"{_seuil(self.plafond_cumul)} de l'encours valorisé du fonds.",
        ]

    def evaluer(self, parts: list[tuple[str, Decimal]], total: Decimal) -> list[Vigilance]:
        """`parts` : (émetteur, montant exact) triés du plus gros au plus petit. Calcul sur les montants
        exacts : additionner des pourcentages arrondis décalerait le cumul."""
        vigilances = []
        part = {emetteur: montant / total * 100 for emetteur, montant in parts}
        au_dessus = [e for e, _ in parts if part[e] > self.seuil_emetteur]
        if au_dessus:
            detail = ", ".join(f"{e} ({_pct(part[e])})" for e in au_dessus)
            vigilances.append(Vigilance(
                "EMETTEUR_AU_DESSUS_DU_SEUIL",
                f"Au-dessus du seuil de vigilance interne de {_seuil(self.seuil_emetteur)} par émetteur : {detail}.",
                au_dessus, part[au_dessus[0]].quantize(CENTIME),
            ))  # fmt: skip
        comptes = [e for e, _ in parts if part[e] > self.seuil_cumul_individuel]
        cumul = sum((montant for e, montant in parts if e in comptes), Decimal(0)) / total * 100
        if cumul > self.plafond_cumul:
            vigilances.append(Vigilance(
                "CUMUL_AU_DESSUS_DU_PLAFOND",
                f"Les {len(comptes)} émetteurs de plus de {_seuil(self.seuil_cumul_individuel)} cumulent "
                f"{_pct(cumul)} de l'encours, au-delà du seuil de vigilance interne de {_seuil(self.plafond_cumul)}.",
                comptes, cumul.quantize(CENTIME),
            ))  # fmt: skip
        return vigilances


REGLES_PAR_DEFAUT = ReglesVigilance()
