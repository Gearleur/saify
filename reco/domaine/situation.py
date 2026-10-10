"""Restitutions texte d'un rapprochement : point de situation (à coller dans un mail) et CSV des suspens."""

import csv
import io
from collections import Counter
from datetime import date
from decimal import Decimal

from reco.domaine.rapprochement import DATE_ARRETE, PRIORITES, Resultat, Suspens, formater_quantite

COLONNES_CSV = (
    "priorite", "fonds", "entite", "isin", "titre", "conservateur", "type", "libelle_type",
    "qte_pms", "qte_conservateur", "ecart", "action", "piste", "signalements", "sources",
)  # fmt: skip
TITRES_PRIORITES = {"critique": "CRITIQUE", "a_relever": "À RELEVER", "en_attente": "EN ATTENTE"}


def quantite_texte(q: Decimal | None) -> str | None:
    """Écriture décimale sans exposant ni zéros inutiles (25000000 au 1/100 → « 250000 »)."""
    if q is None:
        return None
    return format(q.normalize(), "f") if q else "0"


def _qte(q: Decimal | None) -> str:
    return "—" if q is None else formater_quantite(q)


def _suspens(s: Suspens) -> list[str]:
    lignes = [
        f"- {s.fonds or s.entite} · {s.isin} · {s.libelle_titre or '(sans libellé)'} · "
        f"conservateur {s.conservateur} · {s.type} ({s.libelle_type})",
        f"  PMS {_qte(s.qte_pms)} · conservateur {_qte(s.qte_dep)} · écart {_qte(s.ecart)}",
        f"  Action : {s.action}",
    ]
    if s.piste:
        lignes.append(f"  Piste : {s.piste}")
    lignes += [f"  ⚠ {message}" for message in s.signalements]
    return lignes


def point_de_situation(resultat: Resultat, date_arrete: date = DATE_ARRETE) -> str:
    lignes = [f"Point de situation · rapprochement du {date_arrete:%d/%m/%Y}", ""]
    if resultat.statut == "BLOQUE":
        bloquants = [a for a in resultat.journal if a.niveau == "BLOQUANT"]
        lignes += [
            f"Statut : BLOQUÉ · rapprochement refusé ({len(bloquants)} blocage(s)), aucun suspens "
            "calculé : un rapprochement partiel masquerait des écarts.",
            "",
            "Blocages et remèdes",
        ]
        for a in bloquants:
            lignes += [f"- {a.fichier}:{a.ligne} · {a.regle} · {a.motif}", f"  → {a.remede}"]
        return "\n".join(lignes) + "\n"

    par_priorite = Counter(s.priorite for s in resultat.suspens)
    lignes.append(
        f"Statut : OK · {len(resultat.suspens)} suspens ("
        + ", ".join(f"{par_priorite[p]} {TITRES_PRIORITES[p].lower()}" for p in PRIORITES)
        + ")"
    )
    lignes += ["", "Synthèse par fonds"]
    par_fonds = Counter((s.fonds, s.entite) for s in resultat.suspens)
    lignes += [f"- {code or '?'} · {entite} : {n} suspens" for (code, entite), n in sorted(par_fonds.items())]  # fmt: skip
    par_conservateur = Counter(s.conservateur for s in resultat.suspens)
    lignes += ["", "Synthèse par conservateur"]
    lignes += [f"- {c} : {n} suspens" for c, n in sorted(par_conservateur.items())]

    for p in PRIORITES:
        groupe = [s for s in resultat.suspens if s.priorite == p]
        lignes += ["", f"{TITRES_PRIORITES[p]} ({len(groupe)})"]
        if not groupe:
            lignes.append("- aucun")
        for s in groupe:
            lignes += _suspens(s)

    for niveau, titre in (("EXCLU", "Exclusions"), ("SIGNALE", "Signalements du journal")):
        anomalies = [a for a in resultat.journal if a.niveau == niveau]
        lignes += ["", f"{titre} ({len(anomalies)})"]
        lignes += [f"- {a.fichier}:{a.ligne} · {a.regle} · {a.motif}" for a in anomalies] or ["- aucun"]  # fmt: skip
    return "\n".join(lignes) + "\n"


def suspens_csv(suspens: list[Suspens]) -> bytes:
    """`;` et BOM UTF-8 : Excel l'ouvre directement, accents compris."""
    sortie = io.StringIO()
    ecrivain = csv.writer(sortie, delimiter=";", lineterminator="\r\n")
    ecrivain.writerow(COLONNES_CSV)
    for s in suspens:
        ecrivain.writerow([
            s.priorite, s.fonds, s.entite, s.isin, s.libelle_titre, s.conservateur, s.type,
            s.libelle_type, quantite_texte(s.qte_pms) or "", quantite_texte(s.qte_dep) or "",
            quantite_texte(s.ecart), s.action, s.piste, " | ".join(s.signalements),
            " | ".join(s.sources),
        ])  # fmt: skip
    return sortie.getvalue().encode("utf-8-sig")
