import { Moon, Sun } from "lucide-react";
import { useSyncExternalStore } from "react";

import { Button } from "@/components/ui/button";
import { isDarkMode, toggleThemeMode } from "@/lib/theme";
import { cn } from "@/lib/utils";

function subscribe(onStoreChange: () => void) {
  const observer = new MutationObserver(onStoreChange);
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["class"],
  });
  return () => observer.disconnect();
}

function getDarkSnapshot() {
  return isDarkMode();
}

function getDarkServerSnapshot() {
  return false;
}

export function AppSystemFooter({ className }: { className?: string }) {
  const dark = useSyncExternalStore(subscribe, getDarkSnapshot, getDarkServerSnapshot);

  return (
    <div
      className={cn(
        "app-system-footer flex shrink-0 items-center gap-1 border-t border-border bg-card px-3 py-2",
        className,
      )}
    >
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
        title={dark ? "Light mode" : "Dark mode"}
        onClick={() => toggleThemeMode()}
      >
        {dark ? <Sun className="size-4" aria-hidden /> : <Moon className="size-4" aria-hidden />}
      </Button>
    </div>
  );
}
