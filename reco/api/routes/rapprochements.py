"""Rapprochements : création (dépôt ou exemple), historique, exports (CSV, point de situation)."""

from fastapi import APIRouter, Response

from reco.api.dependances import HistoriqueDep, ReglagesDep
from reco.api.schemas import (
    DemandeRapprochement,
    PointDeSituation,
    Rapprochement,
    RapprochementResume,
)
from reco.api.services import depot, rapprochements

router = APIRouter(prefix="/api/rapprochements", tags=["rapprochements"])


def _statut_http(modele: Rapprochement, response: Response) -> Rapprochement:
    # Refus métier : pas une erreur HTTP, le journal dit quoi faire (docs/API.md).
    response.status_code = 200 if modele.statut == "BLOQUE" else 201
    return modele


@router.post("", status_code=201)
def creer(demande: DemandeRapprochement, response: Response,
          reglages: ReglagesDep, historique: HistoriqueDep) -> Rapprochement:  # fmt: skip
    fichiers = depot.decoder(demande, reglages.taille_fichier_max)
    return _statut_http(rapprochements.executer(fichiers, reglages, historique), response)


@router.post("/exemple", status_code=201)
def exemple(response: Response, reglages: ReglagesDep, historique: HistoriqueDep) -> Rapprochement:
    fichiers = depot.depot_exemple(reglages.dossier_donnees)
    return _statut_http(rapprochements.executer(fichiers, reglages, historique), response)


@router.get("")
def lister(historique: HistoriqueDep) -> list[RapprochementResume]:
    return [rapprochements.resume(r) for r in historique.recents()]


@router.get("/{id_}")
def lire(id_: str, historique: HistoriqueDep) -> Rapprochement:
    return historique.lire(id_).modele


@router.get("/{id_}/suspens.csv")
def csv_suspens(id_: str, historique: HistoriqueDep) -> Response:
    entree = historique.lire(id_)
    return Response(
        entree.csv,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="suspens_{entree.modele.date_arrete or "date-inconnue"}.csv"'
        },
    )


@router.get("/{id_}/point-de-situation")
def situation(id_: str, historique: HistoriqueDep) -> PointDeSituation:
    return PointDeSituation(texte=historique.lire(id_).situation)
