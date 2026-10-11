"""Fabrique de jeux de test : fichiers du 25/09 altérés en mémoire, base copiée et modifiée."""

import io
import shutil
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import openpyxl

from middle_office import reconcile

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "donnees"
PMS, A, B, C = (
    "positions_internes.csv",
    "depositaire_A_20260925.xlsx",
    "depositaire_B_20260925.txt",
    "depositaire_C_20260925.xml",
)
KEYS = {"pms": PMS, "a": A, "b": B, "c": C}


def files(**replacements: bytes) -> dict[str, bytes]:
    everything = {name: (DATA_DIR / name).read_bytes() for name in (PMS, A, B, C)}
    for key, content in replacements.items():
        everything[KEYS[key]] = content
    return everything


def run(
    upload: dict[str, bytes],
    db: Path | None = DATA_DIR / "orsay.db",
    config: Path = DATA_DIR / "parametrage.xlsx",
):
    return reconcile(upload, config, db)


def rules(result, level: str) -> set[str]:
    return {a.rule for a in result.cleaning_log if a.level == level}


def replace_in(name: str, *pairs: tuple[str, str]) -> bytes:
    text = (DATA_DIR / name).read_bytes().decode()
    for before, after in pairs:
        assert before in text, before
        text = text.replace(before, after)
    return text.encode()


def xlsx_a(
    security: str | None = None,
    quantity: str | None = None,
    duplicate: int | None = None,
    add: list | None = None,
) -> bytes:
    wb = openpyxl.load_workbook(DATA_DIR / A)
    ws = wb.worksheets[0]
    if security is not None:
        ws["A1"] = security
    if quantity is not None:
        ws["D4"] = quantity
    if duplicate is not None:
        ws.append([cell.value for cell in ws[duplicate]])
    if add is not None:
        ws.append(add)
    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()


def modified_db(folder: Path, *queries: str) -> Path:
    """Copie de orsay.db modifiée : l'original n'est jamais touché."""
    copy = folder / "orsay.db"
    shutil.copy(DATA_DIR / "orsay.db", copy)
    with sqlite3.connect(copy) as db:
        for query in queries:
            db.execute(query)
    return copy


def modified_client_config(folder: Path, sheet: str, modify) -> Path:
    """Copie de parametrage.xlsx dont la feuille est passée à `modifier(ws)`."""
    wb = openpyxl.load_workbook(DATA_DIR / "parametrage.xlsx")
    modify(wb[sheet])
    copy = folder / "parametrage.xlsx"
    wb.save(copy)
    return copy


class FakeClient:
    """Imite `client.messages.parse(...)` : renvoie une intention fixée, ou lève une erreur."""

    def __init__(self, intent=None, error: Exception | None = None, stop_reason: str = "end_turn"):
        self.calls: list[dict] = []
        self.messages = SimpleNamespace(parse=self._parse)
        self._intent, self._error, self._stop = intent, error, stop_reason

    def _parse(self, **kwargs):
        self.calls.append(kwargs)
        if self._error:
            raise self._error
        return SimpleNamespace(parsed_output=self._intent, stop_reason=self._stop)
