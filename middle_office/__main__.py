"""Usage : uv run python -m middle_office data/donnees"""

import sys
from decimal import Decimal
from pathlib import Path

from middle_office import rapprocher_dossier
from middle_office.domaine.rapprochement.moteur import formater_quantite


def _qte(q: Decimal | None) -> str:
    return "-" if q is None else formater_quantite(q)


def main() -> None:
    dossier = Path(sys.argv[1] if len(sys.argv) > 1 else "data/donnees")
    resultat = rapprocher_dossier(dossier)
    print(f"Statut : {resultat.statut} · {len(resultat.suspens)} suspens\n")
    for s in resultat.suspens:
        print(
            f"{s.fonds or s.entite:<5} {s.isin:<12} {s.conservateur:<5} {s.type:<7} "
            f"PMS {_qte(s.qte_pms):>9}  Dép. {_qte(s.qte_dep):>9}  {s.libelle_titre}"
        )
        print(f"      → {s.action}")
        if s.piste:
            print(f"      piste : {s.piste}")
        for message in s.signalements:
            print(f"      ⚠ {message}")
    normalises = sum(a.niveau == "NORMALISE" for a in resultat.journal)
    print(f"\nJournal ({normalises} normalisations non détaillées) :")
    for a in resultat.journal:
        if a.niveau != "NORMALISE":
            print(f"  {a.niveau:<9} {a.regle:<21} {a.fichier}:{a.ligne}  {a.motif}")
            if a.remede:
                print(f"            → {a.remede}")


if __name__ == "__main__":
    main()
