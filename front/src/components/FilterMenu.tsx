import { ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { DotTone } from "@/lib/domain";
import { cn } from "@/lib/utils";
import { StatusDot } from "./StatusDot";

export interface FilterOption {
  value: string;
  label: string;
  count?: number;
  tone?: DotTone;
  hint?: string;
}

interface FilterMenuProps {
  label: string;
  options: FilterOption[];
  selected: string[];
  onChange: (selected: string[]) => void;
  description?: string;
}

/** Filtre de barre d'outils façon Supabase : un menu déroulant à cases, avec effectifs. */
export function FilterMenu({ label, options, selected, onChange, description }: FilterMenuProps) {
  const enabled = selected.length > 0;
  const toggleOpen = (value: string) =>
    onChange(selected.includes(value) ? selected.filter((v) => v !== value) : [...selected, value]);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className={cn(enabled && "border-foreground/30 bg-hover")}
        >
          {label}
          {enabled && (
            <span className="rounded bg-background px-1 text-2xs text-muted-foreground">
              {selected.length}
            </span>
          )}
          <ChevronDown className="text-subtle" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-64">
        {description && <DropdownMenuLabel>{description}</DropdownMenuLabel>}
        {options.map((o) => (
          <DropdownMenuCheckboxItem
            key={o.value}
            checked={selected.includes(o.value)}
            onCheckedChange={() => toggleOpen(o.value)}
            onSelect={(e) => e.preventDefault()}
          >
            {o.tone && <StatusDot tone={o.tone} />}
            <span className="min-w-0 flex-1">
              <span className="block truncate">{o.label}</span>
              {o.hint && <span className="block truncate text-xs text-subtle">{o.hint}</span>}
            </span>
            {o.count !== undefined && <span className="text-xs text-subtle">{o.count}</span>}
          </DropdownMenuCheckboxItem>
        ))}
        {enabled && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={() => onChange([])} className="text-muted-foreground">
              Effacer le filtre
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
