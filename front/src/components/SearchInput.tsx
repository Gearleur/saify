import { Search } from "lucide-react";
import { forwardRef } from "react";
import { Kbd } from "@/components/ui/kbd";
import { cn } from "@/lib/utils";

interface SearchInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  className?: string;
}

/** Recherche de barre d'outils ; `/` y place le curseur (voir useSlashFocus). */
export const SearchInput = forwardRef<HTMLInputElement, SearchInputProps>(
  ({ value, onChange, placeholder, className }, ref) => (
    <label
      className={cn(
        "group flex h-8 w-64 items-center gap-2 rounded-md border border-border-strong bg-background px-2.5 transition-colors duration-150 focus-within:border-ring",
        className,
      )}
    >
      <Search className="size-3.5 shrink-0 text-subtle" />
      <input
        ref={ref}
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="h-full min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-subtle [&::-webkit-search-cancel-button]:hidden"
      />
      {!value && <Kbd className="group-focus-within:hidden">/</Kbd>}
    </label>
  ),
);
SearchInput.displayName = "SearchInput";
