import { Search } from "lucide-react";
import { StatusDot } from "@/components/StatusDot";
import { Kbd } from "@/components/ui/kbd";
import { routeHref, useHashRoute } from "@/hooks/useHashRoute";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/ThemeToggle";
import { ApiHealth } from "./ApiHealth";
import { ROUTE_DEFS } from "./routes";
import { SidebarHistory } from "./SidebarHistory";
import { useNavBadges } from "./useNavBadges";

const SECTIONS = [...new Set(ROUTE_DEFS.map((r) => r.section))];

/** Navigation : sections par public et fréquence, compteurs gris, historique, santé de l'API. */
export function Sidebar({
  onSearch,
  onNavigate,
}: {
  onSearch: () => void;
  onNavigate?: () => void;
}) {
  const { route } = useHashRoute();
  const badges = useNavBadges();
  return (
    <nav aria-label="Navigation principale" className="flex h-full flex-col bg-sidebar">
      <div className="flex h-bar shrink-0 items-center gap-2 px-4">
        <span
          aria-hidden
          className="flex size-5 items-center justify-center rounded-[5px] bg-primary text-[9px] font-semibold text-primary-foreground"
        >
          OG
        </span>
        <span className="text-sm font-semibold">Orsay Gestion</span>
        <span className="text-xs text-subtle">Middle office</span>
      </div>
      <div className="px-3 pb-2">
        <button
          onClick={onSearch}
          className="flex h-control w-full items-center gap-2 rounded-md border border-border bg-background px-2 text-sm text-subtle transition-colors duration-150 hover:border-border-strong"
        >
          <Search className="size-3.5" />
          Rechercher
          <span className="ml-auto flex gap-0.5">
            <Kbd>⌘</Kbd>
            <Kbd>K</Kbd>
          </span>
        </button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-3 pb-3">
        {SECTIONS.map((section) => (
          <div key={section} className="pt-4">
            <p className="px-2 pb-1 text-xs text-subtle">{section}</p>
            <ul className="space-y-px">
              {ROUTE_DEFS.filter((r) => r.section === section).map(({ id, title, icon: Icon }) => {
                const badge = badges[id];
                const actif = route.id === id;
                return (
                  <li key={id}>
                    <a
                      href={routeHref(id)}
                      onClick={onNavigate}
                      aria-current={actif ? "page" : undefined}
                      className={cn(
                        "flex h-control items-center gap-2 rounded-md px-2 text-sm text-muted-foreground transition-colors duration-150 hover:bg-hover hover:text-foreground",
                        actif && "bg-hover font-medium text-foreground",
                      )}
                    >
                      <Icon className="size-[15px] shrink-0" strokeWidth={1.75} />
                      <span className="flex-1 truncate">{title}</span>
                      {badge?.tone && <StatusDot tone={badge.tone} />}
                      {badge?.count !== undefined && (
                        <span className="text-xs tabular-nums text-subtle">{badge.count}</span>
                      )}
                    </a>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
        <div className="pt-5">
          <p className="px-2 pb-1 text-xs text-subtle">Historique</p>
          <SidebarHistory />
        </div>
      </div>
      <div className="flex shrink-0 items-end justify-between gap-2 border-t border-border px-4 py-3 text-xs">
        <ApiHealth />
        <ThemeToggle />
      </div>
    </nav>
  );
}
