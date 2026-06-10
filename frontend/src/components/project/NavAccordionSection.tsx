import { ChevronRight, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export function NavAccordionSection({
  label,
  icon: Icon,
  isOpen,
  onToggle,
  children,
}: {
  label: string;
  icon: LucideIcon;
  isOpen: boolean;
  onToggle: () => void;
  children: ReactNode;
}) {
  return (
    <section className={cn("border-t pt-3", isOpen && "pb-1")}>
      <button
        type="button"
        className="flex h-9 w-full items-center gap-2 rounded-md px-2 text-left text-sm font-semibold transition-colors hover:bg-muted/70"
        aria-expanded={isOpen}
        onClick={onToggle}
      >
        <Icon className="size-4 shrink-0 text-muted-foreground" aria-hidden />
        <span className="min-w-0 flex-1 truncate">{label}</span>
        <ChevronRight
          className={cn(
            "size-3.5 shrink-0 text-muted-foreground transition-transform",
            isOpen && "rotate-90",
          )}
          aria-hidden
        />
      </button>
      {isOpen ? <div className="mt-2 space-y-1 px-1">{children}</div> : null}
    </section>
  );
}
