import { THEME_OPTIONS } from "@/components/ThemeToggle";
import { CommandGroup, CommandItem } from "@/components/ui/command";
import { useTheme } from "@/hooks/useTheme";

/** Groupe « Préférences » de la palette : Thème clair, sombre, système (le choix actif est signalé). */
export function ThemeCommands({ onDone }: { onDone: () => void }) {
  const { preference, setPreference } = useTheme();
  return (
    <CommandGroup heading="Préférences">
      {THEME_OPTIONS.map(({ value, label, icon: Icon }) => (
        <CommandItem
          key={value}
          value={`préférence thème ${label}`}
          onSelect={() => (onDone(), setPreference(value))}
        >
          <Icon />
          Thème {label.toLowerCase()}
          {preference === value && <span className="ml-auto text-xs text-subtle">Actif</span>}
        </CommandItem>
      ))}
    </CommandGroup>
  );
}
