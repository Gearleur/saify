"""Catalogue des requêtes autorisées. Chaque entrée : SQL fixe et paramétré, calcul en Decimal, gabarit."""

from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

from reco.domaine.questions.base import connexion_lecture_seule, decimal
from reco.domaine.questions.modeles import Chiffre, LigneSource, Reponse, montant

CENTIME = Decimal("0.01")

SQL_ENCOURS = """
SELECT p.portefeuille, f.nom, p.isin, t.libelle, t.type_titre, t.mode_cotation,
       p.quantite, c.cours, c.date_cours
FROM positions p
JOIN portefeuilles f ON f.code = p.portefeuille
JOIN titres t ON t.isin = p.isin
LEFT JOIN cours c ON c.isin = p.isin AND c.date_cours = :date
WHERE p.date_arrete = :date AND (:fonds IS NULL OR p.portefeuille = :fonds)
ORDER BY p.portefeuille, p.isin
""".strip()


def _valoriser(quantite: Decimal, cours: Decimal, mode_cotation: str) -> Decimal | None:
    """Quantité en nominal pour les obligations (cours en % du nominal), en titres pour les actions."""
    if mode_cotation == "POURCENTAGE":
        return (
            quantite * cours / 100
        )  # surtout pas × valeur_nominale : la quantité est déjà un nominal
    if mode_cotation == "UNITAIRE":
        return quantite * cours
    return None


def encours_valorise(base: Path, fonds: str | None, date_ref: date) -> Reponse:
    parametres = {"date": date_ref.isoformat(), "fonds": fonds}
    with connexion_lecture_seule(base) as db:
        lignes = db.execute(SQL_ENCOURS, parametres).fetchall()
    jour = f"{date_ref:%d/%m/%Y}"
    if not lignes:
        return Reponse(f"Aucune position pour {fonds or 'les fonds'} au {jour} dans la base de gestion.",
                       [], SQL_ENCOURS, parametres, [], confiance="basse")  # fmt: skip

    totaux: dict[str, Decimal] = defaultdict(Decimal)
    sources, avertissements, exclues = [], [], 0
    for code, nom, isin, libelle, type_titre, mode, quantite, cours, date_cours in lignes:
        qte, prix = decimal(quantite), decimal(cours)
        valeur = None
        if prix is None:
            avertissements.append(f"{isin} {libelle} : pas de cours au {jour}, ligne non valorisée")
        else:
            valeur = _valoriser(qte, prix, mode)
            if valeur is None:
                avertissements.append(f"{isin} {libelle} : mode de cotation « {mode} » inconnu, ligne non valorisée")  # fmt: skip
        if valeur is None:
            exclues += 1
        else:
            totaux[nom] += valeur
        sources.append(LigneSource("positions × titres × cours", {
            "portefeuille": code, "isin": isin, "libelle": libelle, "type_titre": type_titre,
            "mode_cotation": mode, "quantite": str(qte), "cours": "" if prix is None else str(prix),
            "date_cours": date_cours or "",
            "valorisation": "" if valeur is None else str(valeur.quantize(CENTIME)),
        }))  # fmt: skip

    if any(mode == "POURCENTAGE" for *_, mode, _, _, _ in lignes):
        avertissements.append("Obligations valorisées au pied de coupon (cours en % du nominal), sans coupon couru.")  # fmt: skip
    avertissements.append("Positions de la base de gestion (vue PMS, en date de négociation) : opérations non dénouées incluses.")  # fmt: skip

    partiel = " partiel" if exclues else ""
    chiffres = [Chiffre(f"Encours valorisé{partiel}" if fonds else nom, total.quantize(CENTIME), "EUR")
                for nom, total in sorted(totaux.items())]  # fmt: skip
    if fonds is None:
        total = sum(totaux.values(), Decimal(0)).quantize(CENTIME)
        chiffres.append(Chiffre(f"Total des {len(totaux)} fonds{partiel}", total, "EUR"))
        phrase = f"L'encours valorisé{partiel} des {len(totaux)} fonds au {jour} est de {montant(total)} EUR"
    else:
        nom = lignes[0][1]
        phrase = f"L'encours valorisé{partiel} d'{nom} au {jour} est de {montant(chiffres[0].valeur)} EUR"
    phrase += f" ({len(lignes) - exclues} lignes valorisées au cours de clôture du {jour}"
    phrase += f", {exclues} non valorisées)." if exclues else ")."
    return Reponse(phrase, chiffres, SQL_ENCOURS, parametres, sources,
                   confiance="basse" if exclues else "haute", avertissements=avertissements)  # fmt: skip
