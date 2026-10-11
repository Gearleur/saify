"""Injection des dépendances : les routes reçoivent réglages et historique, sans état global."""

from typing import Annotated

from fastapi import Depends, Request

from middle_office.api.config import Settings
from middle_office.api.services.history import History
from middle_office.api.services.llm import GuardedClient


def _settings(request: Request) -> Settings:
    return request.app.state.settings


def _history(request: Request) -> History:
    return request.app.state.history


def _llm(request: Request) -> GuardedClient | None:
    return request.app.state.llm


SettingsDep = Annotated[Settings, Depends(_settings)]
HistoryDep = Annotated[History, Depends(_history)]
LlmDep = Annotated[GuardedClient | None, Depends(_llm)]
