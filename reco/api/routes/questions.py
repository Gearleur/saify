"""Questions sur la base de gestion (besoin 2) : route réservée, branchée sur le domaine plus tard."""

from fastapi import APIRouter

from reco.api.erreurs import ErreurApi
from reco.api.schemas import Question

router = APIRouter(prefix="/api/questions", tags=["questions"])


@router.post("")
def poser(question: Question) -> None:
    raise ErreurApi(501, "NON_DISPONIBLE",
                    "Questions sur la base : fonctionnalité prévue (besoin 2), pas encore disponible")  # fmt: skip
