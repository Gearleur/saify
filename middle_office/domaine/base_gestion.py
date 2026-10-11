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

LECTURES = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION}


def _autoriser(action: int, *_) -> int:
    return sqlite3.SQLITE_OK if action in LECTURES else sqlite3.SQLITE_DENY


@contextmanager
def connexion_lecture_seule(base: Path) -> Iterator[sqlite3.Connection]:
    db = sqlite3.connect(f"file:{base}?mode=ro", uri=True)
    try:
        db.execute("PRAGMA query_only = ON")
        db.set_authorizer(_autoriser)  # posé en dernier : plus rien d'autre qu'une lecture
        yield db
    finally:
        db.close()


def decimal(valeur: float | int | None) -> Decimal | None:
    """Les cours sont stockés en REAL : on passe par leur écriture décimale, jamais par le binaire."""
    return None if valeur is None else Decimal(str(valeur))


def date_reference(base: Path) -> date | None:
    """Date de référence des questions : la dernière date de positions de la base elle-même."""
    with connexion_lecture_seule(base) as db:
        (valeur,) = db.execute("SELECT max(date_arrete) FROM positions").fetchone()
    return date.fromisoformat(valeur) if valeur else None
