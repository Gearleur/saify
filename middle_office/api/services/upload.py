"""Dépôt de fichiers : identification de la source, décodage base64 strict, limites de taille."""

import base64
import binascii
from pathlib import Path

from middle_office.api.errors import ApiError
from middle_office.api.schemas import ReconciliationRequest
from middle_office.domain.reconciliation.engine import READERS, source_of_file


def source_of(name: str) -> str:
    """PMS, A, B ou C d'après le début du nom (casse ignorée) ; 422 si aucun ne correspond."""
    source = source_of_file(name)
    if source is None:
        expected = ", ".join(prefix for prefix, _ in READERS.values())
        raise ApiError(
            422,
            "FICHIER_NON_RECONNU",
            f"« {name} » : source non reconnue, préfixes attendus : {expected}",
            {"name": name},
        )
    return source


def decode(request_body: ReconciliationRequest, max_file_size: int) -> dict[str, bytes]:
    upload: dict[str, bytes] = {}
    for file in request_body.files:
        if file.name in upload:
            raise ApiError(422, "VALIDATION", f"« {file.name} » déposé deux fois")
        source_of(file.name)
        too_large = ApiError(
            413,
            "FICHIER_TROP_GROS",
            f"« {file.name} » dépasse {max_file_size} octets une fois décodé",
        )
        if len(file.content_b64) // 4 * 3 > max_file_size + 2:
            raise too_large  # inutile de décoder ce qu'on refusera
        try:
            content = base64.b64decode(file.content_b64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ApiError(
                422,
                "VALIDATION",
                f"« {file.name} » : base64 invalide",
                [{"field": "fichiers.contenu_b64", "message": "base64 invalide"}],
            ) from exc
        if len(content) > max_file_size:
            raise too_large
        upload[file.name] = content
    return upload


def sample_upload(data_dir: Path) -> dict[str, bytes]:
    """Les fichiers du 25/09 fournis par le client, pour la démonstration."""
    order = list(READERS)  # PMS, A, B, C
    recognized = [
        (order.index(source), f.name, f)
        for f in data_dir.iterdir()
        if f.is_file() and (source := source_of_file(f.name))
    ]
    return {name: f.read_bytes() for _, name, f in sorted(recognized)}
