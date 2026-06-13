import { ChevronRight } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export function NavAccordionSection({
  label,
  isOpen,
  onToggle,
  children,
}: {
  label: string;
  isOpen: boolean;
  onToggle: () => void;
  children: ReactNode;
}) {
  return (
    <section className={cn("pt-0.5", isOpen && "pb-0.5")}>
      <button
        type="button"
        className="flex h-[22px] w-full items-center gap-1 rounded-sm px-1.5 text-left text-xs transition-colors hover:bg-muted/70"
        aria-expanded={isOpen}
        onClick={onToggle}
      >
        <ChevronRight
          className={cn(
            "size-3 shrink-0 text-muted-foreground transition-transform",
            isOpen && "rotate-90",
          )}
          aria-hidden
        />
        <span className="min-w-0 flex-1 truncate">{label}</span>
      </button>
      {isOpen ? <div className="mt-0.5">{children}</div> : null}
    </section>
  );
}
