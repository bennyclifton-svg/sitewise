import { Moon, Sun } from "lucide-react";
import { useSyncExternalStore } from "react";

import { readStoredTheme, subscribeTheme, toggleTheme } from "@/lib/theme";
import { cn } from "@/lib/utils";

export function ColorThemeButton({ className }: { className?: string }) {
  const theme = useSyncExternalStore(subscribeTheme, readStoredTheme, () => "dark");
  const nextLabel = theme === "light" ? "Dark" : "Light";
  const Icon = theme === "light" ? Moon : Sun;

  return (
    <button
      type="button"
      className={cn(
        "inline-flex size-14 cursor-pointer items-center justify-center rounded-full border border-[var(--cockpit-border)] bg-[var(--cockpit-card-surface)] text-muted-foreground shadow-[var(--cockpit-floating-shadow)] outline-none transition-[color,background-color,border-color,box-shadow] hover:border-[var(--cockpit-selected-border)] hover:bg-[var(--cockpit-selected-surface)] hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        className,
      )}
      aria-label={nextLabel}
      onClick={() => {
        toggleTheme();
      }}
    >
      <Icon className="size-6" aria-hidden />
    </button>
  );
}
