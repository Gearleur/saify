"""Historique des reconciliations, dans un fichier SQLite séparé (traçabilité RCCI), ou en mémoire.

Chaque entrée est figée à la création : réponse JSON, CSV des suspens et point de status_report. On les
relit tels quels, sans recalcul ni objet métier sérialisé. Jamais dans orsay.db, qui reste en lecture seule.
"""

import secrets
import sqlite3
import threading
from pathlib import Path
from typing import NamedTuple

from middle_office.api.errors import ApiError
from middle_office.api.schemas import Reconciliation

SCHEMA = """
CREATE TABLE IF NOT EXISTS reconciliations (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    id TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL,
    response TEXT NOT NULL,
    csv BLOB NOT NULL,
    status_report TEXT NOT NULL
);
-- Statut de traitement d'un suspens, partagé entre les postes. Clé stable d'un rapprochement à
-- l'autre du même arrêté : date d'arrêté, entité, ISIN, conservateur, type.
CREATE TABLE IF NOT EXISTS work_statuses (
    break_key TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
-- Chaque changement, jamais effacé : qui (identifiant de requête) a changé quoi, et quand.
CREATE TABLE IF NOT EXISTS status_log (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    break_key TEXT NOT NULL,
    status TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    request_id TEXT NOT NULL
);
"""


class Input(NamedTuple):
    model: Reconciliation
    csv: bytes
    status_report: str


class History:
    """`fichier` None : en mémoire, borné à `taille` entrées (perdu au redémarrage).

    Sur disque, rien n'est supprimé : la liste montre les `taille` plus récents, mais tout se relit par id.
    Une seule connexion, partagée entre les threads de FastAPI : d'où `check_same_thread=False` et le verrou
    qui sérialise chaque opération. Elle est ouverte au premier usage : importer l'API n'écrit rien.
    """

    def __init__(self, size: int, file: Path | None = None):
        self.size = size
        self.file = file
        self._db: sqlite3.Connection | None = None
        self._lock = threading.Lock()

    def _connection(self) -> sqlite3.Connection:
        if self._db is None:
            if self.file is None:
                target = ":memory:"
            else:
                self.file.parent.mkdir(parents=True, exist_ok=True)
                target = str(self.file)
            self._db = sqlite3.connect(target, check_same_thread=False)
            with self._db:
                self._db.executescript(SCHEMA)
        return self._db

    def _rows(self, query: str, *params) -> list[tuple]:
        with self._lock:
            return self._connection().execute(query, params).fetchall()

    def new_id(self) -> str:
        while self._rows(
            "SELECT 1 FROM reconciliations WHERE id = ?", id_ := f"r_{secrets.token_hex(3)}"
        ):
            pass
        return id_

    def add(self, model: Reconciliation, csv: bytes, status_report: str) -> None:
        with self._lock, self._connection() as db:
            db.execute(
                "INSERT INTO reconciliations (id, created_at, status, response, csv, status_report)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    model.id,
                    model.created_at,
                    model.status,
                    model.model_dump_json(),
                    csv,
                    status_report,
                ),
            )
            if self.file is None:
                db.execute(
                    "DELETE FROM reconciliations WHERE seq NOT IN"
                    " (SELECT seq FROM reconciliations ORDER BY seq DESC LIMIT ?)",
                    (self.size,),
                )

    def read(self, id_: str) -> Input:
        lines = self._rows(
            "SELECT response, csv, status_report FROM reconciliations WHERE id = ?", id_
        )
        if not lines:
            limit = "" if self.file else f" (historique limité aux {self.size} derniers)"
            raise ApiError(404, "INTROUVABLE", f"rapprochement « {id_} » introuvable{limit}")
        ((answer, csv, status_report),) = lines
        return Input(Reconciliation.model_validate_json(answer), bytes(csv), status_report)

    def latest(self, status: str | None = None) -> Reconciliation | None:
        """Le rapprochement le plus récent, éventuellement restreint à un status (OK, BLOQUE)."""
        lines = self._rows(
            "SELECT response FROM reconciliations WHERE ? IS NULL OR status = ?"
            " ORDER BY seq DESC LIMIT 1",
            status,
            status,
        )
        return Reconciliation.model_validate_json(lines[0][0]) if lines else None

    def statuses(self, keys: list[str]) -> dict[str, str]:
        """Statut enregistré de chaque clé connue ; une clé absente est « à traiter »."""
        if not keys:
            return {}
        placeholders = ", ".join("?" * len(keys))
        lines = self._rows(
            f"SELECT break_key, status FROM work_statuses WHERE break_key IN ({placeholders})",
            *keys,
        )
        return dict(lines)

    def save_status(self, key: str, status: str, updated_at: str, request_id: str) -> None:
        with self._lock, self._connection() as db:
            db.execute(
                "INSERT INTO work_statuses (break_key, status, updated_at) VALUES (?, ?, ?)"
                " ON CONFLICT(break_key) DO UPDATE SET status = excluded.status, updated_at = excluded.updated_at",
                (key, status, updated_at),
            )
            db.execute(
                "INSERT INTO status_log (break_key, status, updated_at, request_id) VALUES (?, ?, ?, ?)",
                (key, status, updated_at, request_id),
            )

    def recent(self) -> list[Reconciliation]:
        lines = self._rows(
            "SELECT response FROM reconciliations ORDER BY seq DESC LIMIT ?", self.size
        )
        return [Reconciliation.model_validate_json(answer) for (answer,) in lines]
