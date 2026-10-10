"""Usage : uv run python -m reco data/donnees"""

import sys
from decimal import Decimal
from pathlib import Path

from reco import rapprocher_dossier


def _qte(q: Decimal | None) -> str:
    return "-" if q is None else f"{q:,.0f}".replace(",", " ")


def main() -> None:
    dossier = Path(sys.argv[1] if len(sys.argv) > 1 else "data/donnees")
    resultat = rapprocher_dossier(dossier)
    print(f"{len(resultat.suspens)} suspens\n")
    print(
        f"{'Fonds':<5} {'ISIN':<12} {'Cons.':<5} {'Type':<7} {'PMS':>9} {'Dép.':>9}  Titre / action / piste"
    )
    for s in resultat.suspens:
        print(
            f"{s.fonds:<5} {s.isin:<12} {s.conservateur:<5} {s.type:<7} "
            f"{_qte(s.qte_pms):>9} {_qte(s.qte_dep):>9}  {s.libelle_titre} · {s.action}"
            + (f" · {s.piste}" if s.piste else "")
        )
    print("\nJournal :")
    for a in resultat.journal:
        print(f"  {a.niveau:<9} {a.regle:<17} {a.fichier}:{a.ligne}  {a.motif}")


if __name__ == "__main__":
    main()
