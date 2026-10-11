"""Texte des questions ramené à une forme comparable : sans accents, en minuscules."""

import unicodedata


def normaliser(texte: str) -> str:
    sans_accents = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    return sans_accents.lower()
