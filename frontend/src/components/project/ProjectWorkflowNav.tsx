import type { ReactNode } from "react";

import type { WorkflowTile } from "@/components/project/workflow/workflowTiles";
import { cn } from "@/lib/utils";

type ProjectWorkflowNavProps = {
  tiles: WorkflowTile[];
  selectedWorkflowId: string;
  onSelectWorkflow: (workflowId: string) => void;
  /** Optional first row (e.g. project switcher) matching nav item rhythm. */
  leading?: ReactNode;
};

export function ProjectWorkflowNav({
  tiles,
  selectedWorkflowId,
  onSelectWorkflow,
  leading,
}: ProjectWorkflowNavProps) {
  return (
    <nav className="shrink-0 px-6 py-6" aria-label="Project workflows">
      <ul className="flex flex-col gap-1">
        {leading ? <li>{leading}</li> : null}
        {tiles.map((tile) => {
          const Icon = tile.icon;
          const selected = tile.id === selectedWorkflowId;

          return (
            <li key={tile.id}>
              <button
                type="button"
                className={cn(
                  "flex min-h-12 w-full items-center gap-4 rounded-lg px-3 py-2.5 text-left text-base transition-colors",
                  selected
                    ? "bg-transparent font-medium text-foreground"
                    : "font-normal text-muted-foreground hover:bg-[var(--cockpit-selected-surface)] hover:text-foreground",
                )}
                aria-current={selected ? "page" : undefined}
                onClick={() => onSelectWorkflow(tile.id)}
              >
                <Icon
                  className={cn(
                    "size-5 shrink-0",
                    selected
                      ? "text-[var(--cockpit-accent)]"
                      : "text-muted-foreground",
                  )}
                  aria-hidden
                />
                <span className="truncate">{tile.label}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
