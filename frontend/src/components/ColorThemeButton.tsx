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
        "inline-flex size-8 cursor-pointer items-center justify-center text-muted-foreground outline-none transition-colors hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring",
        className,
      )}
      aria-label={nextLabel}
      onClick={() => {
        toggleTheme();
      }}
    >
      <Icon className="size-4" aria-hidden />
    </button>
  );
}
