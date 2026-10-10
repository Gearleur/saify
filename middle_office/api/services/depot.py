"""Dépôt de fichiers : identification de la source, décodage base64 strict, limites de taille."""

import base64
import binascii
from pathlib import Path

from middle_office.api.erreurs import ErreurApi
from middle_office.api.schemas import DemandeRapprochement
from middle_office.domaine.rapprochement.moteur import LECTEURS


def source_de(nom: str) -> str:
    """PMS, A, B ou C d'après le préfixe du nom ; 422 si aucun ne correspond."""
    for source, (prefixe, _) in LECTEURS.items():
        if nom.startswith(prefixe):
            return source
    attendus = ", ".join(prefixe for prefixe, _ in LECTEURS.values())
    raise ErreurApi(422, "FICHIER_NON_RECONNU",
                    f"« {nom} » : source non reconnue, préfixes attendus : {attendus}", {"nom": nom})  # fmt: skip


def decoder(demande: DemandeRapprochement, taille_fichier_max: int) -> dict[str, bytes]:
    depot: dict[str, bytes] = {}
    for fichier in demande.fichiers:
        if fichier.nom in depot:
            raise ErreurApi(422, "VALIDATION", f"« {fichier.nom} » déposé deux fois")
        source_de(fichier.nom)
        trop_gros = ErreurApi(413, "FICHIER_TROP_GROS",
                              f"« {fichier.nom} » dépasse {taille_fichier_max} octets une fois décodé")  # fmt: skip
        if len(fichier.contenu_b64) // 4 * 3 > taille_fichier_max + 2:
            raise trop_gros  # inutile de décoder ce qu'on refusera
        try:
            contenu = base64.b64decode(fichier.contenu_b64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ErreurApi(422, "VALIDATION", f"« {fichier.nom} » : base64 invalide",
                            [{"champ": "fichiers.contenu_b64", "message": "base64 invalide"}]) from exc  # fmt: skip
        if len(contenu) > taille_fichier_max:
            raise trop_gros
        depot[fichier.nom] = contenu
    return depot


def depot_exemple(dossier_donnees: Path) -> dict[str, bytes]:
    """Les fichiers du 25/09 fournis par le client, pour la démonstration."""
    return {
        f.name: f.read_bytes()
        for prefixe, _ in LECTEURS.values()
        for f in sorted(dossier_donnees.glob(f"{prefixe}*"))
    }
