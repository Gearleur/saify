"""Pont entre l'API et le domaine des questions : contexte du dernier rapprochement, sérialisation."""

from middle_office.api.schemas import (
    ChiffreSortie,
    ComprehensionSortie,
    LigneSourceSortie,
    ReponseQuestion,
    VigilanceSortie,
)
from middle_office.api.services.historique import Historique
from middle_office.domaine.questions.modeles import ContexteRapprochement, Reponse


def contexte_suspens(historique: Historique) -> ContexteRapprochement | None:
    """Dernier rapprochement exploitable (OK), pour « d'où vient le suspens sur X ? ».

    Le plus récent n'est pas forcément le bon : bloqué, il n'a aucun suspens, et répondre « aucun
    suspens sur X » rassurerait à tort. On répond sur le dernier OK en signalant le blocage.
    """
    dernier = historique.dernier()
    if dernier is None:
        return None
    bloque = dernier.id if dernier.statut != "OK" else None
    ok = dernier if bloque is None else historique.dernier("OK")
    if ok is None:
        return ContexteRapprochement(id=None, bloque_plus_recent=bloque)
    return ContexteRapprochement(
        id=ok.id,
        date_arrete=ok.date_arrete,
        suspens=[s.model_dump() for s in ok.suspens],
        bloque_plus_recent=bloque,
    )


def vers_sortie(r: Reponse) -> ReponseQuestion:
    """Décimaux en texte (jamais de float), comme le reste de l'API."""
    return ReponseQuestion(
        question=r.question,
        reponse=r.reponse,
        chiffres=[
            ChiffreSortie(libelle=c.libelle, valeur=str(c.valeur), unite=c.unite)
            for c in r.chiffres
        ],
        requete_sql=r.requete_sql,
        parametres_sql=r.parametres_sql,
        lignes_sources=[
            LigneSourceSortie(table=ligne.table, valeurs=ligne.valeurs)
            for ligne in r.lignes_sources
        ],
        confiance=r.confiance,
        avertissements=r.avertissements,
        vigilances=[
            VigilanceSortie(
                code=v.code, message=v.message, emetteurs=v.emetteurs, valeur=str(v.valeur)
            )
            for v in r.vigilances
        ],  # fmt: skip
        reformulations=r.reformulations,
        comprehension=ComprehensionSortie(**r.comprehension),
    )
