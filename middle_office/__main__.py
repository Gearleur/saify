"""Usage : uv run python -m middle_office data/donnees

Code de sortie : 0 si le rapprochement est fait (suspens ou non), 1 s'il est bloqué. Une tâche
planifiée voit ainsi l'échec sans lire la sortie.
"""

import sys
from decimal import Decimal
from pathlib import Path

from middle_office import reconcile_folder
from middle_office.domain.formats import format_quantity


def _qty(q: Decimal | None) -> str:
    return "-" if q is None else format_quantity(q)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    folder = Path(args[0] if args else "data/donnees")
    result = reconcile_folder(folder)
    print(f"Statut : {result.status} · {len(result.breaks)} suspens\n")
    for s in result.breaks:
        print(
            f"{s.fund or s.entity:<5} {s.isin:<12} {s.custodian:<5} {s.type:<7} "
            f"PMS {_qty(s.pms_qty):>9}  Dép. {_qty(s.custodian_qty):>9}  {s.security_name}"
        )
        print(f"      → {s.action}")
        if s.lead:
            print(f"      piste : {s.lead}")
        for sig in s.flags:
            print(f"      ⚠ {sig.message}")
    normalized = sum(a.level == "NORMALISE" for a in result.cleaning_log)
    print(f"\nJournal ({normalized} normalisations non détaillées) :")
    for a in result.cleaning_log:
        if a.level != "NORMALISE":
            print(f"  {a.level:<9} {a.rule:<21} {a.file}:{a.line}  {a.reason}")
            if a.remedy:
                print(f"            → {a.remedy}")

    return 1 if result.status == "BLOQUE" else 0


if __name__ == "__main__":
    sys.exit(main())
