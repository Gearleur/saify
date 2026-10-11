"""Encours valorisé et concentration par émetteur : la même valorisation ligne à ligne, au cours
de clôture de la date de référence (obligations en % du nominal, pied de coupon ; actions à l'unité).
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from middle_office.domaine.base_gestion import connexion_lecture_seule, decimal
from middle_office.domaine.formats import CENTIME, date_fr, montant, pourcentage
from middle_office.domaine.questions.catalogue.commun import AVERTISSEMENT_PMS, valoriser
from middle_office.domaine.questions.modeles import (
    Chiffre,
    LigneSource,
    Reponse,
)
from middle_office.domaine.questions.vigilance import REGLES_PAR_DEFAUT, ReglesVigilance

SQL_ENCOURS = """
SELECT p.portefeuille, f.nom, p.isin, t.libelle, t.emetteur, t.type_titre, t.mode_cotation,
       p.quantite, c.cours, c.date_cours
FROM positions p
JOIN portefeuilles f ON f.code = p.portefeuille
JOIN titres t ON t.isin = p.isin
LEFT JOIN cours c ON c.isin = p.isin AND c.date_cours = :date
WHERE p.date_arrete = :date AND (:fonds IS NULL OR p.portefeuille = :fonds)
ORDER BY p.portefeuille, p.isin
""".strip()


@dataclass
class _Valorisation:
    """Positions valorisées ligne à ligne : base commune de l'encours et de la concentration."""

    parametres: dict[str, str | None]
    lignes: list[tuple]
    valeurs: list[Decimal | None]  # None : ligne non valorisée (cours absent, mode inconnu)
    sources: list[LigneSource]
    avertissements: list[str]

    @property
    def exclues(self) -> int:
        return sum(v is None for v in self.valeurs)


def valoriser_positions(base: Path, fonds: str | None, date_ref: date) -> _Valorisation:
    parametres = {"date": date_ref.isoformat(), "fonds": fonds}
    with connexion_lecture_seule(base) as db:
        lignes = db.execute(SQL_ENCOURS, parametres).fetchall()
    valeurs, sources, avertissements = [], [], []
    for (
        code,
        _nom,
        isin,
        libelle,
        emetteur,
        type_titre,
        mode,
        quantite,
        cours,
        date_cours,
    ) in lignes:
        qte, prix = decimal(quantite), decimal(cours)
        valeur = None
        if prix is None:
            avertissements.append(
                f"{isin} {libelle} : pas de cours au {date_fr(date_ref)}, ligne non valorisée"
            )
        else:
            valeur = valoriser(qte, prix, mode)
            if valeur is None:
                avertissements.append(
                    f"{isin} {libelle} : mode de cotation « {mode} » inconnu, ligne non valorisée"
                )
        valeurs.append(valeur)
        sources.append(
            LigneSource(
                "positions × titres × cours",
                {
                    "portefeuille": code,
                    "isin": isin,
                    "libelle": libelle,
                    "emetteur": emetteur or "",
                    "type_titre": type_titre,
                    "mode_cotation": mode or "",
                    "quantite": str(qte),
                    "cours": "" if prix is None else str(prix),
                    "date_cours": date_cours or "",
                    "valorisation": "" if valeur is None else str(valeur.quantize(CENTIME)),
                },
            )
        )
    if any(ligne[6] == "POURCENTAGE" for ligne in lignes):
        avertissements.append(
            "Obligations valorisées au pied de coupon (cours en % du nominal), sans coupon couru."
        )
    avertissements.append(AVERTISSEMENT_PMS)
    return _Valorisation(parametres, lignes, valeurs, sources, avertissements)


def encours_valorise(base: Path, fonds: str | None, date_ref: date) -> Reponse:
    v = valoriser_positions(base, fonds, date_ref)
    jour = date_fr(date_ref)
    if not v.lignes:
        return Reponse(
            f"Aucune position pour {fonds or 'les fonds'} au {jour} dans la base de gestion.",
            [],
            SQL_ENCOURS,
            v.parametres,
            [],
            confiance="basse",
        )

    totaux: dict[str, Decimal] = defaultdict(Decimal)
    for ligne, valeur in zip(v.lignes, v.valeurs, strict=True):
        if valeur is not None:
            totaux[ligne[1]] += valeur
    partiel = " partiel" if v.exclues else ""
    chiffres = [
        Chiffre(f"Encours valorisé{partiel}" if fonds else nom, total.quantize(CENTIME), "EUR")
        for nom, total in sorted(totaux.items())
    ]
    if fonds is None:
        total = sum(totaux.values(), Decimal(0)).quantize(CENTIME)
        chiffres.append(Chiffre(f"Total des {len(totaux)} fonds{partiel}", total, "EUR"))
        phrase = f"L'encours valorisé{partiel} des {len(totaux)} fonds au {jour} est de {montant(total)} EUR"
    else:
        phrase = f"L'encours valorisé{partiel} d'{v.lignes[0][1]} au {jour} est de {montant(chiffres[0].valeur)} EUR"
    phrase += f" ({len(v.lignes) - v.exclues} lignes valorisées au cours de clôture du {jour}"
    phrase += f", {v.exclues} non valorisées)." if v.exclues else ")."
    return Reponse(
        phrase,
        chiffres,
        SQL_ENCOURS,
        v.parametres,
        v.sources,
        confiance="basse" if v.exclues else "haute",
        avertissements=v.avertissements,
    )


def concentration_emetteurs(
    base: Path, fonds: str | None, date_ref: date, regles: ReglesVigilance = REGLES_PAR_DEFAUT
) -> Reponse:
    """Part de chaque émetteur dans l'encours valorisé d'un fonds. Chiffres bruts, sans jugement réglementaire."""
    if fonds is None:
        return Reponse(
            "Précisez le fonds : la concentration par émetteur se lit fonds par fonds (PAT, OBL ou ACT).",
            [],
            SQL_ENCOURS,
            {"date": date_ref.isoformat(), "fonds": None},
            [],
            confiance="basse",
        )
    v = valoriser_positions(base, fonds, date_ref)
    jour = date_fr(date_ref)
    par_emetteur: dict[str, Decimal] = defaultdict(Decimal)
    for ligne, valeur in zip(v.lignes, v.valeurs, strict=True):
        if valeur is not None:
            par_emetteur[ligne[4] or "Émetteur non renseigné"] += valeur
    total = sum(par_emetteur.values(), Decimal(0))
    if not total:
        return Reponse(
            f"Aucune position valorisée pour {fonds} au {jour} dans la base de gestion.",
            [],
            SQL_ENCOURS,
            v.parametres,
            v.sources,
            confiance="basse",
            avertissements=v.avertissements,
        )

    classement = sorted(par_emetteur.items(), key=lambda e: (-e[1], e[0]))
    chiffres = [
        Chiffre(emetteur, (valeur / total * 100).quantize(CENTIME), "%")
        for emetteur, valeur in classement
    ]
    premier, valeur_premier = classement[0]
    partiel = " partiel" if v.exclues else ""
    phrase = (
        f"Premier émetteur d'{v.lignes[0][1]} au {jour} : {premier}, {pourcentage(chiffres[0].valeur)} "
        f"de l'encours valorisé{partiel} ({montant(valeur_premier.quantize(CENTIME))} EUR sur "
        f"{montant(total.quantize(CENTIME))} EUR, {len(classement)} émetteurs)."
    )
    avertissements = [
        "Aucune appréciation des ratios réglementaires (5/10/40, dérogations des émetteurs publics) : "
        "chiffres bruts, à interpréter par le gérant ou le RCCI.",
        *v.avertissements,
    ]
    return Reponse(
        phrase,
        chiffres,
        SQL_ENCOURS,
        v.parametres,
        v.sources,
        confiance="basse" if v.exclues else "haute",
        avertissements=avertissements,
        vigilances=regles.evaluer(classement, total),
    )
