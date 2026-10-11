"""Jours ouvrés du règlement-livraison (calendrier TARGET2), pour la date d'arrêté attendue (J-1 ouvré)."""

from datetime import date, timedelta


def _easter(year: int) -> date:
    """Dimanche de Pâques (algorithme grégorien anonyme, dit de Meeus/Jones/Butcher)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    m = (32 + 2 * e + 2 * i - h - k) % 7
    n = (a + 11 * h + 22 * m) // 451
    months, day = divmod(h + m - 7 * n + 114, 31)
    return date(year, months, day + 1)


def target2_holidays(year: int) -> set[date]:
    """Jours de fermeture de TARGET2 : 1er janvier, vendredi saint, lundi de Pâques, 1er mai, 25 et 26 décembre."""
    easter = _easter(year)
    return {
        date(year, 1, 1),
        easter - timedelta(days=2),
        easter + timedelta(days=1),
        date(year, 5, 1),
        date(year, 12, 25),
        date(year, 12, 26),
    }


def is_business_day(day: date) -> bool:
    return day.weekday() < 5 and day not in target2_holidays(day.year)


def previous_business_day(day: date) -> date:
    """J-1 ouvré : la date d'arrêté attendue des relevés reçus le matin du `jour`."""
    previous_day = day - timedelta(days=1)
    while not is_business_day(previous_day):
        previous_day -= timedelta(days=1)
    return previous_day
