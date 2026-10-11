"""Jours ouvrés du règlement-livraison (calendrier TARGET2), pour la date d'arrêté attendue (J-1 ouvré)."""

from datetime import date, timedelta


def _paques(annee: int) -> date:
    """Dimanche de Pâques (algorithme grégorien anonyme, dit de Meeus/Jones/Butcher)."""
    a, b, c = annee % 19, annee // 100, annee % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    m = (32 + 2 * e + 2 * i - h - k) % 7
    n = (a + 11 * h + 22 * m) // 451
    mois, jour = divmod(h + m - 7 * n + 114, 31)
    return date(annee, mois, jour + 1)


def feries_target2(annee: int) -> set[date]:
    """Jours de fermeture de TARGET2 : 1er janvier, vendredi saint, lundi de Pâques, 1er mai, 25 et 26 décembre."""
    paques = _paques(annee)
    return {
        date(annee, 1, 1),
        paques - timedelta(days=2),
        paques + timedelta(days=1),
        date(annee, 5, 1),
        date(annee, 12, 25),
        date(annee, 12, 26),
    }


def est_ouvre(jour: date) -> bool:
    return jour.weekday() < 5 and jour not in feries_target2(jour.year)


def jour_ouvre_precedent(jour: date) -> date:
    """J-1 ouvré : la date d'arrêté attendue des relevés reçus le matin du `jour`."""
    veille = jour - timedelta(days=1)
    while not est_ouvre(veille):
        veille -= timedelta(days=1)
    return veille
