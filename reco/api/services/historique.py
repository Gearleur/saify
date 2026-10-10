"""Historique borné des rapprochements, en mémoire (perdu au redémarrage : limite assumée en démo)."""

import secrets
import threading
from collections import OrderedDict

from reco.api.erreurs import ErreurApi
from reco.api.schemas import Rapprochement
from reco.domaine.rapprochement import Resultat


class Historique:
    """Garde, pour chaque rapprochement, la réponse API et le résultat métier (pour CSV et situation)."""

    def __init__(self, taille: int):
        self.taille = taille
        self._entrees: OrderedDict[str, tuple[Rapprochement, Resultat]] = OrderedDict()
        self._verrou = threading.Lock()

    def nouvel_id(self) -> str:
        with self._verrou:
            while (id_ := f"r_{secrets.token_hex(3)}") in self._entrees:
                pass
            return id_

    def ajouter(self, modele: Rapprochement, resultat: Resultat) -> None:
        with self._verrou:
            self._entrees[modele.id] = (modele, resultat)
            while len(self._entrees) > self.taille:
                self._entrees.popitem(last=False)

    def lire(self, id_: str) -> tuple[Rapprochement, Resultat]:
        with self._verrou:
            if id_ not in self._entrees:
                raise ErreurApi(404, "INTROUVABLE",
                                f"rapprochement « {id_} » introuvable (historique limité aux {self.taille} derniers)")  # fmt: skip
            return self._entrees[id_]

    def recents(self) -> list[Rapprochement]:
        with self._verrou:
            return [modele for modele, _ in reversed(self._entrees.values())]
