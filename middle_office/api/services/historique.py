"""Historique des rapprochements, dans un fichier SQLite séparé (traçabilité RCCI), ou en mémoire.

Chaque entrée est figée à la création : réponse JSON, CSV des suspens et point de situation. On les
relit tels quels, sans recalcul ni objet métier sérialisé. Jamais dans orsay.db, qui reste en lecture seule.
"""

import secrets
import sqlite3
import threading
from pathlib import Path
from typing import NamedTuple

from middle_office.api.erreurs import ErreurApi
from middle_office.api.schemas import Rapprochement

SCHEMA = """
CREATE TABLE IF NOT EXISTS rapprochements (
    rang INTEGER PRIMARY KEY AUTOINCREMENT,
    id TEXT NOT NULL UNIQUE,
    cree_le TEXT NOT NULL,
    statut TEXT NOT NULL,
    reponse TEXT NOT NULL,
    csv BLOB NOT NULL,
    situation TEXT NOT NULL
);
-- Statut de traitement d'un suspens, partagé entre les postes. Clé stable d'un rapprochement à
-- l'autre du même arrêté : date d'arrêté, entité, ISIN, conservateur, type.
CREATE TABLE IF NOT EXISTS statuts (
    cle TEXT PRIMARY KEY,
    statut TEXT NOT NULL,
    modifie_le TEXT NOT NULL
);
-- Chaque changement, jamais effacé : qui (identifiant de requête) a changé quoi, et quand.
CREATE TABLE IF NOT EXISTS statuts_journal (
    rang INTEGER PRIMARY KEY AUTOINCREMENT,
    cle TEXT NOT NULL,
    statut TEXT NOT NULL,
    modifie_le TEXT NOT NULL,
    request_id TEXT NOT NULL
);
"""


class Entree(NamedTuple):
    modele: Rapprochement
    csv: bytes
    situation: str


class Historique:
    """`fichier` None : en mémoire, borné à `taille` entrées (perdu au redémarrage).

    Sur disque, rien n'est supprimé : la liste montre les `taille` plus récents, mais tout se relit par id.
    Une seule connexion, partagée entre les threads de FastAPI : d'où `check_same_thread=False` et le verrou
    qui sérialise chaque opération. Elle est ouverte au premier usage : importer l'API n'écrit rien.
    """

    def __init__(self, taille: int, fichier: Path | None = None):
        self.taille = taille
        self.fichier = fichier
        self._db: sqlite3.Connection | None = None
        self._verrou = threading.Lock()

    def _connexion(self) -> sqlite3.Connection:
        if self._db is None:
            if self.fichier is None:
                cible = ":memory:"
            else:
                self.fichier.parent.mkdir(parents=True, exist_ok=True)
                cible = str(self.fichier)
            self._db = sqlite3.connect(cible, check_same_thread=False)
            with self._db:
                self._db.executescript(SCHEMA)
        return self._db

    def _lignes(self, requete: str, *parametres) -> list[tuple]:
        with self._verrou:
            return self._connexion().execute(requete, parametres).fetchall()

    def nouvel_id(self) -> str:
        while self._lignes(
            "SELECT 1 FROM rapprochements WHERE id = ?", id_ := f"r_{secrets.token_hex(3)}"
        ):
            pass
        return id_

    def ajouter(self, modele: Rapprochement, csv: bytes, situation: str) -> None:
        with self._verrou, self._connexion() as db:
            db.execute(
                "INSERT INTO rapprochements (id, cree_le, statut, reponse, csv, situation)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    modele.id,
                    modele.cree_le,
                    modele.statut,
                    modele.model_dump_json(),
                    csv,
                    situation,
                ),
            )
            if self.fichier is None:
                db.execute(
                    "DELETE FROM rapprochements WHERE rang NOT IN"
                    " (SELECT rang FROM rapprochements ORDER BY rang DESC LIMIT ?)",
                    (self.taille,),
                )

    def lire(self, id_: str) -> Entree:
        lignes = self._lignes(
            "SELECT reponse, csv, situation FROM rapprochements WHERE id = ?", id_
        )
        if not lignes:
            limite = "" if self.fichier else f" (historique limité aux {self.taille} derniers)"
            raise ErreurApi(404, "INTROUVABLE", f"rapprochement « {id_} » introuvable{limite}")
        ((reponse, csv, situation),) = lignes
        return Entree(Rapprochement.model_validate_json(reponse), bytes(csv), situation)

    def dernier(self, statut: str | None = None) -> Rapprochement | None:
        """Le rapprochement le plus récent, éventuellement restreint à un statut (OK, BLOQUE)."""
        lignes = self._lignes(
            "SELECT reponse FROM rapprochements WHERE ? IS NULL OR statut = ?"
            " ORDER BY rang DESC LIMIT 1",
            statut,
            statut,
        )
        return Rapprochement.model_validate_json(lignes[0][0]) if lignes else None

    def statuts(self, cles: list[str]) -> dict[str, str]:
        """Statut enregistré de chaque clé connue ; une clé absente est « à traiter »."""
        if not cles:
            return {}
        marques = ", ".join("?" * len(cles))
        lignes = self._lignes(f"SELECT cle, statut FROM statuts WHERE cle IN ({marques})", *cles)
        return dict(lignes)

    def changer_statut(self, cle: str, statut: str, modifie_le: str, request_id: str) -> None:
        with self._verrou, self._connexion() as db:
            db.execute(
                "INSERT INTO statuts (cle, statut, modifie_le) VALUES (?, ?, ?)"
                " ON CONFLICT(cle) DO UPDATE SET statut = excluded.statut, modifie_le = excluded.modifie_le",
                (cle, statut, modifie_le),
            )
            db.execute(
                "INSERT INTO statuts_journal (cle, statut, modifie_le, request_id) VALUES (?, ?, ?, ?)",
                (cle, statut, modifie_le, request_id),
            )

    def recents(self) -> list[Rapprochement]:
        lignes = self._lignes(
            "SELECT reponse FROM rapprochements ORDER BY rang DESC LIMIT ?", self.taille
        )
        return [Rapprochement.model_validate_json(reponse) for (reponse,) in lignes]
