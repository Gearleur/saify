"""Front : la page et ses fichiers statiques (reco/web/)."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from reco.api.dependances import ReglagesDep
from reco.api.erreurs import reponse_erreur

router = APIRouter(include_in_schema=False)


@router.get("/")
def page(reglages: ReglagesDep) -> Response:
    index = reglages.dossier_web / "index.html"
    if not index.is_file():
        return reponse_erreur(503, "PAGE_INDISPONIBLE",
                              "Interface pas encore installée (reco/web/index.html absent) ; l'API répond sous /api")  # fmt: skip
    return FileResponse(index, media_type="text/html; charset=utf-8")


class Statiques(StaticFiles):
    """Dossier web absent (front pas encore livré) : 404 propre plutôt qu'une erreur 500."""

    async def check_config(self) -> None:
        if self.directory is None or not Path(self.directory).is_dir():
            raise StarletteHTTPException(404)
        await super().check_config()
