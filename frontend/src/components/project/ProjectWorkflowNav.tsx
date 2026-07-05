import type { WorkflowTile } from "@/components/project/workflow/workflowTiles";
import { cn } from "@/lib/utils";

type ProjectWorkflowNavProps = {
  tiles: WorkflowTile[];
  selectedWorkflowId: string;
  onSelectWorkflow: (workflowId: string) => void;
};

export function ProjectWorkflowNav({
  tiles,
  selectedWorkflowId,
  onSelectWorkflow,
}: ProjectWorkflowNavProps) {
  return (
    <nav className="shrink-0 px-3 py-2" aria-label="Project workflows">
      <ul className="flex flex-col gap-0.5">
        {tiles.map((tile) => {
          const Icon = tile.icon;
          const selected = tile.id === selectedWorkflowId;

          return (
            <li key={tile.id}>
              <button
                type="button"
                className={cn(
                  "flex w-full items-center gap-2 rounded-md px-1.5 py-1.5 text-left text-sm transition-colors",
                  selected
                    ? "bg-muted/40 text-foreground"
                    : "text-muted-foreground hover:bg-muted/30 hover:text-foreground",
                )}
                aria-current={selected ? "page" : undefined}
                onClick={() => onSelectWorkflow(tile.id)}
              >
                <Icon
                  className="size-4 shrink-0 text-[var(--cockpit-workflow-icon)]"
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
