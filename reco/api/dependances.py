"""Injection des dépendances : les routes reçoivent réglages et historique, sans état global."""

from typing import Annotated

from fastapi import Depends, Request

from reco.api.config import Reglages
from reco.api.services.historique import Historique


def _reglages(request: Request) -> Reglages:
    return request.app.state.reglages


def _historique(request: Request) -> Historique:
    return request.app.state.historique


ReglagesDep = Annotated[Reglages, Depends(_reglages)]
HistoriqueDep = Annotated[Historique, Depends(_historique)]
