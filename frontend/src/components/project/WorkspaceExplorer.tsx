import { ChevronRight } from "lucide-react";
import { useEffect, useState } from "react";

import { handleWorkspaceNodeSelect } from "@/components/project/workflow/workflowRouting";
import { collectExplorerExpandPaths } from "@/components/project/workflow/workspaceRouting";
import type { WorkspaceTreeNode } from "@/lib/types/project";
import { cn } from "@/lib/utils";

const INDENT_PX = 10;
const BASE_PADDING_PX = 2;

type FileTypeMark = {
  letter: string;
  colorClass: string;
};

function fileTypeMark(node: WorkspaceTreeNode): FileTypeMark | null {
  if (node.kind !== "file") return null;

  const extension = node.name.includes(".")
    ? node.name.split(".").pop()?.toLowerCase()
    : undefined;

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

function FileTypeIcon({ mark }: { mark: FileTypeMark }) {
  return (
    <span
      className={cn(
        "grid size-3 shrink-0 place-items-center text-[10px] font-bold leading-none",
        mark.colorClass,
      )}
      aria-hidden
    >
      {mark.letter}
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

  useEffect(() => {
    setExpandedPaths(collectExplorerExpandPaths(tree, selectedPath));
  }, [tree, selectedPath]);

  if (!tree.length) {
    return <p className="px-1.5 text-xs text-muted-foreground">Loading folder template...</p>;
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
    <div role="tree" aria-label="Project workspace explorer">
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
  const fileMark = fileTypeMark(node);

  return (
    <div role="none">
      <div
        className="flex min-w-0 items-center"
        style={{ paddingLeft: `${BASE_PADDING_PX + level * INDENT_PX}px` }}
      >
        {hasChildren ? (
          <button
            type="button"
            className="grid size-[18px] shrink-0 place-items-center rounded-sm text-muted-foreground hover:bg-muted/70"
            aria-label={expanded ? `Collapse ${node.name}` : `Expand ${node.name}`}
            onClick={() => onToggle(node.path)}
          >
            <ChevronRight
              className={cn("size-3 transition-transform", expanded && "rotate-90")}
              aria-hidden
            />
          </button>
        ) : (
          <span className="size-[18px] shrink-0" aria-hidden />
        )}
        <button
          type="button"
          role="treeitem"
          aria-selected={selected}
          className={cn(
            "flex h-[22px] min-w-0 flex-1 items-center gap-1.5 truncate rounded-sm px-1 text-left text-xs transition-colors hover:bg-muted/70",
            selected ? "bg-muted text-foreground" : "text-muted-foreground",
          )}
          onClick={() => onSelect(node)}
        >
          {fileMark ? <FileTypeIcon mark={fileMark} /> : null}
          <span className="min-w-0 truncate">{node.name}</span>
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
