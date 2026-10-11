"""Texte des questions ramené à une forme comparable : sans accents, en minuscules."""

import unicodedata


def normalize(text: str) -> str:
    without_accents = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return without_accents.lower()
