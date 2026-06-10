import { ChevronRight, FileText } from "lucide-react";
import { useState } from "react";

import { handleWorkspaceNodeSelect } from "@/components/project/workflow/workflowRouting";
import type { WorkspaceTreeNode } from "@/lib/types/project";
import { cn } from "@/lib/utils";

type ExplorerNodeTone = {
  letter?: string;
  colorClass: string;
};

function explorerNodeTone(node: WorkspaceTreeNode): ExplorerNodeTone | null {
  if (node.kind !== "file") {
    return { colorClass: "text-[var(--wf-ready-text)]" };
  }

  const extension = node.name.includes(".") ? node.name.split(".").pop()?.toLowerCase() : undefined;

  switch (extension) {
    case "pdf":
      return { letter: "P", colorClass: "text-[var(--wf-danger-text)]" };
    case "md":
    case "markdown":
    case "docx":
    case "doc":
      return { letter: "M", colorClass: "text-[var(--wf-info-text)]" };
    case "xlsx":
    case "xls":
      return { letter: "E", colorClass: "text-[var(--wf-ok-text)]" };
    default:
      return null;
  }
}

function ExplorerNodeIcon({ tone }: { tone: ExplorerNodeTone | null }) {
  if (!tone?.letter) {
    return tone ? null : <FileText className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />;
  }

  return (
    <span
      className={cn(
        "grid size-3.5 shrink-0 place-items-center text-[11px] font-bold leading-none",
        tone.colorClass,
      )}
      aria-hidden
    >
      {tone.letter}
    </span>
  );
}

export function WorkspaceExplorer({
  tree,
  selectedPath,
  onSelectPath,
  onOpenWorkflow,
  onViewWorkbench,
  onViewFolder,
}: {
  tree: WorkspaceTreeNode[];
  selectedPath: string | null;
  onSelectPath: (path: string) => void;
  onOpenWorkflow: (tileId: string) => void;
  onViewWorkbench: () => void;
  onViewFolder: () => void;
}) {
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(() => new Set());

  if (!tree.length) {
    return <p className="px-2 text-xs text-muted-foreground">Loading folder template...</p>;
  }

  function togglePath(path: string) {
    setExpandedPaths((current) => {
      const next = new Set(current);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  }

  return (
    <div className="space-y-0.5" role="tree" aria-label="Project workspace explorer">
      {tree.map((node) => (
        <ExplorerNode
          key={node.path}
          node={node}
          level={0}
          selectedPath={selectedPath}
          expandedPaths={expandedPaths}
          onToggle={togglePath}
          onSelect={(selected) =>
            handleWorkspaceNodeSelect(selected, {
              onSelectPath,
              onOpenWorkflow,
              onViewWorkbench,
              onViewFolder,
            })
          }
        />
      ))}
    </div>
  );
}

function ExplorerNode({
  node,
  level,
  selectedPath,
  expandedPaths,
  onToggle,
  onSelect,
}: {
  node: WorkspaceTreeNode;
  level: number;
  selectedPath: string | null;
  expandedPaths: Set<string>;
  onToggle: (path: string) => void;
  onSelect: (node: WorkspaceTreeNode) => void;
}) {
  const isFile = node.kind === "file";
  const hasChildren = !isFile && node.children.length > 0;
  const expanded = expandedPaths.has(node.path);
  const selected = selectedPath === node.path;
  const tone = explorerNodeTone(node);

  return (
    <div role="none">
      <div
        className="flex min-w-0 items-center"
        style={{ paddingLeft: `${0.25 + level * 0.65}rem` }}
      >
        {hasChildren ? (
          <button
            type="button"
            className="grid size-6 shrink-0 place-items-center rounded-sm text-muted-foreground hover:bg-muted"
            aria-label={expanded ? `Collapse ${node.name}` : `Expand ${node.name}`}
            onClick={() => onToggle(node.path)}
          >
            <ChevronRight
              className={cn("size-3.5 transition-transform", expanded && "rotate-90")}
              aria-hidden
            />
          </button>
        ) : (
          <span className="size-6 shrink-0" aria-hidden />
        )}
        <button
          type="button"
          role="treeitem"
          aria-selected={selected}
          className={cn(
            "flex min-h-8 min-w-0 flex-1 items-center gap-2 rounded-md py-1.5 pr-2 text-left text-xs transition-colors hover:bg-muted/70",
            selected && "bg-muted font-medium",
            !selected && !tone && "text-muted-foreground",
          )}
          onClick={() => onSelect(node)}
        >
          <ExplorerNodeIcon tone={tone} />
          <span className={cn("min-w-0 truncate", tone?.colorClass)}>{node.name}</span>
          {node.document_count ? (
            <span className="ml-auto rounded bg-background px-1.5 text-[0.65rem] text-muted-foreground">
              {node.document_count}
            </span>
          ) : null}
        </button>
      </div>
      {hasChildren && expanded
        ? node.children.map((child) => (
            <ExplorerNode
              key={child.path}
              node={child}
              level={level + 1}
              selectedPath={selectedPath}
              expandedPaths={expandedPaths}
              onToggle={onToggle}
              onSelect={onSelect}
            />
          ))
        : null}
    </div>
  );
}
