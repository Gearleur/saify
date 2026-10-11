"""Tombées d'échéances à venir : titres détenus qui arrivent à maturité dans l'horizon demandé."""

import calendar
from datetime import date
from decimal import Decimal
from pathlib import Path

from middle_office.domaine.base_gestion import connexion_lecture_seule, decimal
from middle_office.domaine.formats import date_fr, formater_quantite, montant
from middle_office.domaine.questions.catalogue.commun import AVERTISSEMENT_PMS, libelle_perimetre
from middle_office.domaine.questions.modeles import (
    Chiffre,
    LigneSource,
    Reponse,
)

HORIZON_DEFAUT_MOIS = 12  # à valider avec le client (NOTES.md, Q4)


SQL_ECHEANCES = """
SELECT p.portefeuille, f.nom, p.isin, t.libelle, t.type_titre, t.date_echeance, p.quantite
FROM positions p
JOIN portefeuilles f ON f.code = p.portefeuille
JOIN titres t ON t.isin = p.isin
WHERE p.date_arrete = :date AND p.quantite > 0
  AND t.date_echeance > :date AND t.date_echeance <= :fin
  AND (:fonds IS NULL OR p.portefeuille = :fonds) AND (:isin IS NULL OR p.isin = :isin)
ORDER BY t.date_echeance, p.portefeuille, p.isin
""".strip()


def ajouter_mois(d: date, mois: int) -> date:
    annee, mois_0 = divmod(d.month - 1 + mois, 12)
    annee += d.year
    return date(annee, mois_0 + 1, min(d.day, calendar.monthrange(annee, mois_0 + 1)[1]))


def _borne_de_fin(
    date_ref: date, horizon_mois: int | None, isin: str | None, fin: date | None
) -> tuple[date | None, bool]:
    """Date de fin (None : pas de borne) et vrai si l'horizon par défaut s'applique. Un titre précis
    sans horizon n'a pas de borne : « quand tombe EDF 2031 ? » ne doit pas répondre « aucune tombée »
    parce que c'est au-delà de 12 mois."""
    if fin is not None or horizon_mois is not None:
        return fin or ajouter_mois(date_ref, horizon_mois or HORIZON_DEFAUT_MOIS), False
    if isin is not None:
        return None, False
    return ajouter_mois(date_ref, HORIZON_DEFAUT_MOIS), True


def _source(ligne: tuple) -> LigneSource:
    code, _nom, isin, libelle, type_titre, echeance, quantite = ligne
    return LigneSource(
        "positions × titres",
        {
            "portefeuille": code,
            "isin": isin,
            "libelle": libelle,
            "type_titre": type_titre,
            "date_echeance": echeance,
            "nominal": str(decimal(quantite)),
        },
    )


def _detail(ligne: tuple) -> str:
    code, _nom, _isin, libelle, _type, echeance, quantite = ligne
    return f"{libelle} ({code}) le {date_fr(date.fromisoformat(echeance))} pour {formater_quantite(decimal(quantite))}"


def echeances(
    base: Path,
    fonds: str | None,
    date_ref: date,
    horizon_mois: int | None = None,
    isin: str | None = None,
    fin: date | None = None,
) -> Reponse:
    """Titres détenus arrivant à échéance après la date de référence, dans l'horizon donné."""
    fin, horizon_par_defaut = _borne_de_fin(date_ref, horizon_mois, isin, fin)
    parametres = {
        "date": date_ref.isoformat(),
        "fin": (fin or date.max).isoformat(),
        "fonds": fonds,
        "isin": isin,
    }
    with connexion_lecture_seule(base) as db:
        lignes = db.execute(SQL_ECHEANCES, parametres).fetchall()
    avertissements = [
        "Montant remboursé = nominal détenu (remboursement au pair), hors dernier coupon.",
        AVERTISSEMENT_PMS,
    ]
    if horizon_par_defaut:
        avertissements.insert(
            0,
            f"Horizon par défaut de {HORIZON_DEFAUT_MOIS} mois (à valider avec le middle office).",
        )
    perimetre = libelle_perimetre(fonds, isin)
    borne = (
        f"entre le {date_fr(date_ref)} et le {date_fr(fin)}"
        if fin
        else f"après le {date_fr(date_ref)}"
    )
    if not lignes:
        phrase = f"Aucune tombée d'échéance {perimetre} {borne}."
        return Reponse(phrase, [], SQL_ECHEANCES, parametres, [], avertissements=avertissements)

    nominal = sum((decimal(ligne[6]) for ligne in lignes), Decimal(0))
    phrase = (
        f"{len(lignes)} tombée(s) d'échéance {perimetre} {borne} : {', '.join(map(_detail, lignes))}. "
        f"Nominal remboursé : {montant(nominal)} EUR."
    )
    chiffres = [
        Chiffre("Tombées d'échéance", Decimal(len(lignes)), "lignes"),
        Chiffre("Nominal remboursé", nominal, "EUR"),
    ]
    sources = [_source(ligne) for ligne in lignes]
    return Reponse(
        phrase, chiffres, SQL_ECHEANCES, parametres, sources, avertissements=avertissements
    )
