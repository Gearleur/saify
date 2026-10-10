"""Pont entre l'API et le domaine des questions : contexte du dernier rapprochement, sérialisation."""

from middle_office.api.schemas import (
    ChiffreSortie,
    ComprehensionSortie,
    LigneSourceSortie,
    ReponseQuestion,
    VigilanceSortie,
)
from middle_office.api.services.historique import Historique
from middle_office.domaine.questions.modeles import Reponse


def contexte_suspens(historique: Historique) -> tuple[list[dict] | None, str | None]:
    """Suspens du rapprochement le plus récent, pour « d'où vient le suspens sur X ? »."""
    recents = historique.recents()
    if not recents:
        return None, None
    dernier = recents[0]
    return [s.model_dump() for s in dernier.suspens], dernier.id


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
