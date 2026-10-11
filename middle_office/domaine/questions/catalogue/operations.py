"""Opérations non dénouées : en attente de règlement-livraison ; une date prévue dépassée est un
défaut de règlement, donc un risque CSDR.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import NamedTuple

from middle_office.domaine.base_gestion import connexion_lecture_seule, decimal
from middle_office.domaine.formats import CENTIME, date_fr, formater_quantite
from middle_office.domaine.questions.catalogue.commun import libelle_perimetre, valoriser
from middle_office.domaine.questions.modeles import (
    Chiffre,
    LigneSource,
    Reponse,
)

SQL_NON_DENOUEES = """
SELECT m.id, m.date_operation, m.date_denouement, m.portefeuille, m.isin, t.libelle,
       t.mode_cotation, m.sens, m.quantite, m.prix, m.contrepartie
FROM mouvements m
LEFT JOIN titres t ON t.isin = m.isin
WHERE m.statut = 'EN_ATTENTE' AND (:fonds IS NULL OR m.portefeuille = :fonds)
  AND (:isin IS NULL OR m.isin = :isin)
ORDER BY m.date_denouement, m.id
""".strip()


class _Operation(NamedTuple):
    detail: str  # pour la phrase de réponse
    source: LigneSource
    retard: str | None  # avertissement CSDR si la date de dénouement prévue est dépassée


def _operation(ligne: tuple, date_ref: date) -> _Operation:
    id_, date_op, date_den, code, isin, libelle, mode, sens, quantite, prix, contrepartie = ligne
    qte, cours = decimal(quantite), decimal(prix)
    valeur = None if cours is None else valoriser(qte, cours, mode)
    prevue = date.fromisoformat(date_den)
    retard = None
    if prevue <= date_ref:
        retard = (
            f"Op. n°{id_} ({libelle or isin}) devait être dénouée le {date_fr(prevue)} : "
            "défaut de règlement-livraison, risque CSDR."
        )
    detail = f"n°{id_} {sens} {formater_quantite(qte)} {libelle or isin} ({code}, dén. prévu {date_fr(prevue)})"
    source = LigneSource(
        "mouvements",
        {
            "id": str(id_),
            "date_operation": date_op,
            "date_denouement": date_den,
            "portefeuille": code,
            "isin": isin,
            "sens": sens,
            "quantite": str(qte),
            "prix": "" if cours is None else str(cours),
            "montant": "" if valeur is None else str(valeur.quantize(CENTIME)),
            "contrepartie": contrepartie or "",
        },
    )
    return _Operation(detail, source, retard)


def operations_non_denouees(
    base: Path, fonds: str | None, date_ref: date, isin: str | None = None
) -> Reponse:
    """Opérations en attente de dénouement ; une date prévue dépassée est un défaut de règlement (CSDR)."""
    parametres = {"fonds": fonds, "isin": isin}
    with connexion_lecture_seule(base) as db:
        lignes = db.execute(SQL_NON_DENOUEES, parametres).fetchall()
    perimetre = libelle_perimetre(fonds, isin)
    avertissements = ["Statut lu dans la base de gestion (opérations de la semaine)."]
    if not lignes:
        phrase = f"Aucune opération non dénouée {perimetre}."
        return Reponse(phrase, [], SQL_NON_DENOUEES, parametres, [], avertissements=avertissements)

    operations = [_operation(ligne, date_ref) for ligne in lignes]
    retards = [o.retard for o in operations if o.retard]
    avertissements = (
        list(reversed(retards)) + avertissements
    )  # les retards d'abord, le plus récent en tête
    suffixe = f", dont {len(retards)} en retard (risque CSDR)" if retards else ""
    phrase = (
        f"{len(lignes)} opération(s) non dénouée(s) {perimetre} au {date_fr(date_ref)}{suffixe} : "
        f"{', '.join(o.detail for o in operations)}."
    )
    chiffres = [Chiffre("Opérations non dénouées", Decimal(len(lignes)), "opérations")]
    if retards:
        chiffres.append(Chiffre("En retard (risque CSDR)", Decimal(len(retards)), "opérations"))
    sources = [o.source for o in operations]
    return Reponse(
        phrase, chiffres, SQL_NON_DENOUEES, parametres, sources, avertissements=avertissements
    )
