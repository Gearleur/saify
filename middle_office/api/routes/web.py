"""Front : la page et ses fichiers statiques (middle_office/web/)."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from middle_office.api.dependencies import SettingsDep
from middle_office.api.errors import error_response

router = APIRouter(include_in_schema=False)


@router.get("/")
def page(settings: SettingsDep) -> Response:
    index = settings.web_dir / "index.html"
    if not index.is_file():
        return error_response(
            503,
            "PAGE_INDISPONIBLE",
            "Interface pas encore installée (middle_office/web/index.html absent) ; l'API répond sous /api",
        )
    return FileResponse(index, media_type="text/html; charset=utf-8")


class OptionalStaticFiles(StaticFiles):
    """Dossier web absent (front pas encore livré) : 404 propre plutôt qu'une erreur 500."""

    async def check_config(self) -> None:
        if self.directory is None or not Path(self.directory).is_dir():
            raise StarletteHTTPException(404)
        await super().check_config()
