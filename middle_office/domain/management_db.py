"""Accès à orsay.db (base de gestion), pour les deux besoins, en lecture seule garantie :
« personne ne doit pouvoir modifier l'inventaire ».

Trois verrous indépendants : fichier ouvert en `mode=ro`, `PRAGMA query_only`, et un autorisateur
SQLite qui refuse toute opération autre qu'une lecture (y compris PRAGMA et ATTACH).
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import overload

READ_ACTIONS = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION}


def _authorize(action: int, *_) -> int:
    return sqlite3.SQLITE_OK if action in READ_ACTIONS else sqlite3.SQLITE_DENY


@contextmanager
def read_only_connection(db_path: Path) -> Iterator[sqlite3.Connection]:
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        db.execute("PRAGMA query_only = ON")
        db.set_authorizer(_authorize)  # posé en dernier : plus rien d'autre qu'une lecture
        yield db
    finally:
        db.close()


@overload
def decimal(value: None) -> None: ...
@overload
def decimal(value: float | int) -> Decimal: ...
def decimal(value: float | int | None) -> Decimal | None:
    """Les cours sont stockés en REAL : on passe par leur écriture décimale, jamais par le binaire."""
    return None if value is None else Decimal(str(value))


def latest_position_date(db_path: Path) -> date | None:
    """Date de référence des questions : la dernière date de positions de la base elle-même."""
    with read_only_connection(db_path) as db:
        (value,) = db.execute("SELECT max(date_arrete) FROM positions").fetchone()
    return date.fromisoformat(value) if value else None
