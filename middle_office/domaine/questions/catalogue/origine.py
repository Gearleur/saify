"""Origine d'un suspens : le pont avec le besoin 1 (suspens du dernier rapprochement exploitable,
ses lignes sources et les mouvements du titre).
"""

from datetime import date
from decimal import Decimal
from pathlib import Path

from middle_office.domaine.base_gestion import connexion_lecture_seule, decimal
from middle_office.domaine.formats import date_fr, formater_quantite
from middle_office.domaine.questions.modeles import (
    Chiffre,
    ContexteRapprochement,
    LigneSource,
    Reponse,
)

SQL_MOUVEMENTS_TITRE = """
SELECT id, portefeuille, date_operation, date_denouement, sens, quantite, statut
FROM mouvements
WHERE isin = :isin
ORDER BY id
""".strip()
COLONNES_MOUVEMENTS = (
    "id",
    "portefeuille",
    "date_operation",
    "date_denouement",
    "sens",
    "quantite",
    "statut",
)


def _sans_rapprochement(contexte: ContexteRapprochement | None) -> str:
    if contexte is not None and contexte.bloque_plus_recent:
        return (
            f"Le dernier rapprochement ({contexte.bloque_plus_recent}) est bloqué et aucun "
            "rapprochement exploitable n'existe : corrigez les fichiers, puis relancez."
        )
    return "Aucun rapprochement disponible : lancez d'abord le rapprochement du jour."


def _qte(valeur: str | None) -> str:
    return "absent" if valeur is None else formater_quantite(Decimal(valeur))


def _phrase(s: dict, reference: str) -> str:
    phrase = (
        f"Suspens {s['type']} ({s['libelle_type']}) sur {s['libelle_titre']} ({s['fonds'] or s['entite']}, "
        f"conservateur {s['conservateur']}) dans {reference} : PMS {_qte(s['qte_pms'])}, "
        f"conservateur {_qte(s['qte_dep'])}, écart {_qte(s['ecart'])}. Action attendue : {s['action']}."
    )
    return phrase + (f" Piste : {s['piste']}." if s["piste"] else "")


def _source_mouvement(ligne: tuple) -> LigneSource:
    valeurs = dict(zip(COLONNES_MOUVEMENTS, ligne, strict=True))
    valeurs["quantite"] = decimal(valeurs["quantite"])
    return LigneSource("mouvements", {cle: str(v) for cle, v in valeurs.items()})


def origine_suspens(base: Path, isin: str, contexte: ContexteRapprochement | None) -> Reponse:
    """Pont avec le besoin 1 : le suspens du dernier rapprochement exploitable, ses lignes sources
    et les mouvements du titre. Un rapprochement plus récent mais bloqué est toujours signalé."""
    parametres: dict[str, str | None] = {"isin": isin}
    if contexte is None or contexte.id is None:
        motif = _sans_rapprochement(contexte)
        return Reponse(motif, [], SQL_MOUVEMENTS_TITRE, parametres, [], confiance="basse")

    jour = (
        date_fr(date.fromisoformat(contexte.date_arrete))
        if contexte.date_arrete
        else "date inconnue"
    )
    reference = f"le rapprochement {contexte.id} (arrêté du {jour})"
    avertissements = []
    if contexte.bloque_plus_recent:
        avertissements.append(
            f"Le rapprochement le plus récent ({contexte.bloque_plus_recent}) est bloqué : cette réponse "
            f"vient de {reference}, le dernier exploitable. Elle peut ne plus être à jour."
        )
    confiance = "basse" if contexte.bloque_plus_recent else "haute"
    trouves = [s for s in contexte.suspens if s["isin"] == isin]
    if not trouves:
        phrase = f"Aucun suspens sur {isin} dans {reference}."
        return Reponse(
            phrase,
            [],
            SQL_MOUVEMENTS_TITRE,
            parametres,
            [],
            confiance=confiance,
            avertissements=avertissements,
        )

    fonds = {s["fonds"] for s in trouves}
    with connexion_lecture_seule(base) as db:
        mouvements = [m for m in db.execute(SQL_MOUVEMENTS_TITRE, parametres) if m[1] in fonds]
    sources = [
        LigneSource(ref, {"isin": isin, "suspens": s["id"]})
        for s in trouves
        for ref in s["sources"]
    ]
    sources += [_source_mouvement(m) for m in mouvements]
    chiffres = [
        Chiffre(
            f"Écart {s['type']} ({s['conservateur']})", Decimal(s["ecart"]), "titres ou nominal"
        )
        for s in trouves
    ]
    avertissements += [g["message"] for s in trouves for g in s["signalements"]]
    phrases = " ".join(_phrase(s, reference) for s in trouves)
    return Reponse(
        phrases, chiffres, SQL_MOUVEMENTS_TITRE, parametres, sources, confiance, avertissements
    )
