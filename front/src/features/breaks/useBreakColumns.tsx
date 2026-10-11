import { useMemo } from "react";
import type { Column } from "@/components/DataTable";
import { Quantity } from "@/components/Quantity";
import { StatusLabel } from "@/components/StatusDot";
import { Tag } from "@/components/Tag";
import { useReconciliation } from "@/hooks/useReconciliation";
import { useReferenceData } from "@/hooks/useReferenceData";
import { compareDecimal } from "@/lib/decimal";
import { PRIORITY_ORDER, PRIORITIES } from "@/lib/domain";
import { cn } from "@/lib/utils";
import type { Break } from "@/types/api";
import { STATUS_ORDER, useWorkStatuses } from "./workStatuses";
import { ACTION_AS_COLUMN, StatusCell, TitleCell, TypeCell } from "./BreakCells";

/**
 * `triage` : la file du matin (l'action attendue compte plus que le type).
 * `analyse` : la vue Suspens (priorité et type affichés, l'action passe en fiche sauf grand écran).
 */
export function useBreakColumns(variant: "triage" | "analyse"): Column<Break>[] {
  const { current } = useReconciliation();
  const { get } = useWorkStatuses(current);
  const { custodianName } = useReferenceData();

  return useMemo(() => {
    const priority: Column<Break> = {
      id: "priority",
      header: "Priorité",
      className: "w-[112px] whitespace-nowrap",
      cell: (s) => (
        <StatusLabel tone={PRIORITIES[s.priority].tone}>{PRIORITIES[s.priority].label}</StatusLabel>
      ),
      compare: (a, b) => PRIORITY_ORDER.indexOf(a.priority) - PRIORITY_ORDER.indexOf(b.priority),
    };
    const titleText: Column<Break> = {
      id: "security",
      header: "Titre",
      className: "w-full min-w-[200px] max-w-0",
      cell: (s) => <TitleCell s={s} withAction={variant === "triage"} />,
      compare: (a, b) => a.security_name.localeCompare(b.security_name, "fr"),
    };
    const type: Column<Break> = {
      id: "type",
      header: "Type",
      className: "hidden w-[150px] whitespace-nowrap @2xl:table-cell",
      cell: (s) => <TypeCell s={s} />,
      compare: (a, b) => a.type.localeCompare(b.type),
    };
    const fund: Column<Break> = {
      id: "fund",
      header: "Fonds",
      className: "w-[64px]",
      cell: (s) => <Tag>{s.fund}</Tag>,
      compare: (a, b) => a.fund.localeCompare(b.fund),
    };
    const custodian: Column<Break> = {
      id: "custodian",
      header: "Conservateur",
      className: cn(
        "hidden w-[136px] whitespace-nowrap",
        variant === "triage" ? "@6xl:table-cell" : "@5xl:table-cell",
      ),
      cell: (s) => <span className="text-muted-foreground">{custodianName(s.custodian)}</span>,
      compare: (a, b) => a.custodian.localeCompare(b.custodian),
    };
    const qty = (id: "pms_qty" | "custodian_qty", header: string): Column<Break> => ({
      id,
      header,
      align: "right",
      className: "hidden w-[96px] whitespace-nowrap @2xl:table-cell",
      cell: (s) => <Quantity value={s[id]} />,
      compare: (a, b) => compareDecimal(a[id], b[id]),
    });
    const difference: Column<Break> = {
      id: "difference",
      header: "Écart",
      align: "right",
      className: "w-[88px] whitespace-nowrap",
      cell: (s) => <Quantity value={s.difference} signed />,
      compare: (a, b) => compareDecimal(a.difference, b.difference),
    };
    const action = (visibility: string): Column<Break> => ({
      id: "action",
      header: "Action attendue",
      className: cn("hidden whitespace-nowrap", visibility),
      cell: (s) => s.action,
      compare: (a, b) => a.action.localeCompare(b.action, "fr"),
    });
    const status: Column<Break> = {
      id: "status",
      header: "Statut",
      className: "w-[100px] whitespace-nowrap",
      cell: (s) => <StatusCell status={get(s)} />,
      compare: (a, b) => STATUS_ORDER.indexOf(get(a)) - STATUS_ORDER.indexOf(get(b)),
    };
    const quantities = [qty("pms_qty", "Qté PMS"), qty("custodian_qty", "Qté conservateur")];
    return variant === "triage"
      ? [titleText, fund, custodian, ...quantities, difference, action(ACTION_AS_COLUMN), status]
      : [
          priority,
          titleText,
          type,
          fund,
          custodian,
          ...quantities,
          difference,
          action("@7xl:table-cell"),
          status,
        ];
  }, [variant, get, custodianName]);
}
