import {
  BookOpenCheck,
  FileText,
  Inbox,
  MessageSquareText,
  Rows3,
  SlidersHorizontal,
  type LucideIcon,
} from "lucide-react";
import type { ComponentType } from "react";
import { JournalView } from "@/features/journal/JournalView";
import { QuestionsView } from "@/features/questions/QuestionsView";
import { SettingsView } from "@/features/settings/SettingsView";
import { SituationView } from "@/features/situation/SituationView";
import { BreaksView } from "@/features/breaks/BreaksView";
import { MorningView } from "@/features/triage/MorningView";
import type { RouteId } from "@/hooks/useHashRoute";

export interface RouteDef {
  id: RouteId;
  title: string;
  section: string;
  icon: LucideIcon;
  View: ComponentType;
}

/** Les vues, dans l'ordre de la matinée ; les sections regroupent par public et par fréquence. */
export const ROUTE_DEFS: RouteDef[] = [
  {
    id: "a-traiter",
    title: "Aujourd'hui",
    section: "Rapprochement",
    icon: Inbox,
    View: MorningView,
  },
  { id: "suspens", title: "Suspens", section: "Rapprochement", icon: Rows3, View: BreaksView },
  {
    id: "point",
    title: "Point de situation",
    section: "Rapprochement",
    icon: FileText,
    View: SituationView,
  },
  {
    id: "questions",
    title: "Questions",
    section: "Base de gestion",
    icon: MessageSquareText,
    View: QuestionsView,
  },
  {
    id: "journal",
    title: "Journal et fichiers",
    section: "Contrôle",
    icon: BookOpenCheck,
    View: JournalView,
  },
  {
    id: "parametrage",
    title: "Paramétrage",
    section: "Contrôle",
    icon: SlidersHorizontal,
    View: SettingsView,
  },
];

export function routeDef(id: RouteId): RouteDef {
  return ROUTE_DEFS.find((r) => r.id === id) ?? (ROUTE_DEFS[0] as RouteDef);
}
