import { useMemo } from "react";
import type { Column } from "@/components/DataTable";
import { Quantity } from "@/components/Quantity";
import { StatusLabel } from "@/components/StatusDot";
import { Tag } from "@/components/Tag";
import { useReconciliation } from "@/hooks/useReconciliation";
import { useReferentiel } from "@/hooks/useReferentiel";
import { compareDecimal } from "@/lib/decimal";
import { ORDRE_PRIORITES, PRIORITES } from "@/lib/metier";
import { cn } from "@/lib/utils";
import type { Suspens } from "@/types/api";
import { ORDRE_STATUTS, useStatuts } from "./statutsTraitement";
import { ACTION_EN_COLONNE, StatusCell, TitleCell, TypeCell } from "./SuspensCells";

/**
 * `triage` : la file du matin (l'action attendue compte plus que le type).
 * `analyse` : la vue Suspens (priorité et type affichés, l'action passe en fiche sauf grand écran).
 */
export function useSuspensColumns(variant: "triage" | "analyse"): Column<Suspens>[] {
  const { courant } = useReconciliation();
  const { get } = useStatuts(courant);
  const { nomConservateur } = useReferentiel();

  return useMemo(() => {
    const priorite: Column<Suspens> = {
      id: "priorite",
      header: "Priorité",
      className: "w-[112px] whitespace-nowrap",
      cell: (s) => (
        <StatusLabel tone={PRIORITES[s.priorite].tone}>{PRIORITES[s.priorite].label}</StatusLabel>
      ),
      compare: (a, b) => ORDRE_PRIORITES.indexOf(a.priorite) - ORDRE_PRIORITES.indexOf(b.priorite),
    };
    const titre: Column<Suspens> = {
      id: "titre",
      header: "Titre",
      className: "w-full min-w-[200px] max-w-0",
      cell: (s) => <TitleCell s={s} withAction={variant === "triage"} />,
      compare: (a, b) => a.libelle_titre.localeCompare(b.libelle_titre, "fr"),
    };
    const type: Column<Suspens> = {
      id: "type",
      header: "Type",
      className: "hidden w-[150px] whitespace-nowrap @2xl:table-cell",
      cell: (s) => <TypeCell s={s} />,
      compare: (a, b) => a.type.localeCompare(b.type),
    };
    const fonds: Column<Suspens> = {
      id: "fonds",
      header: "Fonds",
      className: "w-[64px]",
      cell: (s) => <Tag>{s.fonds}</Tag>,
      compare: (a, b) => a.fonds.localeCompare(b.fonds),
    };
    const conservateur: Column<Suspens> = {
      id: "conservateur",
      header: "Conservateur",
      className: cn(
        "hidden w-[136px] whitespace-nowrap",
        variant === "triage" ? "@6xl:table-cell" : "@5xl:table-cell",
      ),
      cell: (s) => <span className="text-muted-foreground">{nomConservateur(s.conservateur)}</span>,
      compare: (a, b) => a.conservateur.localeCompare(b.conservateur),
    };
    const qte = (id: "qte_pms" | "qte_dep", header: string): Column<Suspens> => ({
      id,
      header,
      align: "right",
      className: "hidden w-[96px] whitespace-nowrap @2xl:table-cell",
      cell: (s) => <Quantity value={s[id]} />,
      compare: (a, b) => compareDecimal(a[id], b[id]),
    });
    const ecart: Column<Suspens> = {
      id: "ecart",
      header: "Écart",
      align: "right",
      className: "w-[88px] whitespace-nowrap",
      cell: (s) => <Quantity value={s.ecart} signed />,
      compare: (a, b) => compareDecimal(a.ecart, b.ecart),
    };
    const action = (visibilite: string): Column<Suspens> => ({
      id: "action",
      header: "Action attendue",
      className: cn("hidden whitespace-nowrap", visibilite),
      cell: (s) => s.action,
      compare: (a, b) => a.action.localeCompare(b.action, "fr"),
    });
    const statut: Column<Suspens> = {
      id: "statut",
      header: "Statut",
      className: "w-[100px] whitespace-nowrap",
      cell: (s) => <StatusCell status={get(s)} />,
      compare: (a, b) => ORDRE_STATUTS.indexOf(get(a)) - ORDRE_STATUTS.indexOf(get(b)),
    };
    const qtes = [qte("qte_pms", "Qté PMS"), qte("qte_dep", "Qté conservateur")];
    return variant === "triage"
      ? [titre, fonds, conservateur, ...qtes, ecart, action(ACTION_EN_COLONNE), statut]
      : [
          priorite,
          titre,
          type,
          fonds,
          conservateur,
          ...qtes,
          ecart,
          action("@7xl:table-cell"),
          statut,
        ];
  }, [variant, get, nomConservateur]);
}
