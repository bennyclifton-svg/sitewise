import { Check, ChevronDown, FolderOpen, FolderPlus, Pencil } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import type { ProjectSummary } from "@/lib/types/project";
import { cn } from "@/lib/utils";

export function ProjectSwitcher({
  projects,
  activeProject,
  loading = false,
  onRename,
}: {
  projects: ProjectSummary[];
  activeProject: ProjectSummary;
  loading?: boolean;
  onRename?: (title: string) => Promise<void>;
}) {
  const navigate = useNavigate();
  const [renaming, setRenaming] = useState(false);
  const [draftTitle, setDraftTitle] = useState(activeProject.title);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function commitRename() {
    const title = draftTitle.trim();
    if (!onRename || !title || title === activeProject.title) {
      setRenaming(false);
      setDraftTitle(activeProject.title);
      setError(null);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onRename(title);
      setRenaming(false);
    } catch {
      setError("Could not rename project.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="shrink-0 border-y border-[var(--cockpit-border)] px-6 py-6">
      {renaming ? (
        <form
          className="grid gap-1 px-1.5"
          onSubmit={(event) => {
            event.preventDefault();
            void commitRename();
          }}
        >
          <label className="sr-only">
            Project name
          </label>
          <Input
            value={draftTitle}
            autoFocus
            disabled={saving}
            aria-label="Project name"
            onChange={(event) => setDraftTitle(event.target.value)}
            onBlur={() => void commitRename()}
            onKeyDown={(event) => {
              if (event.key === "Escape") {
                event.preventDefault();
                setRenaming(false);
                setDraftTitle(activeProject.title);
                setError(null);
              }
            }}
          />
          {error ? <p className="text-xs text-destructive">{error}</p> : null}
        </form>
      ) : (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              className={cn(
                "flex w-full cursor-pointer items-center gap-3 rounded-[calc(var(--cockpit-card-radius)+0.25rem)] border border-[var(--cockpit-selected-border)] bg-[var(--cockpit-selected-surface)] px-4 py-3.5 text-left text-base transition-colors outline-none",
                "text-foreground hover:border-[var(--cockpit-accent)]",
                "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              )}
              aria-label={`Project: ${activeProject.title}`}
              title={activeProject.title}
            >
              <FolderOpen
                className="size-5 shrink-0 text-[var(--cockpit-workflow-icon)]"
                aria-hidden
              />
              <span className="min-w-0 flex-1 truncate leading-snug text-foreground">
                {activeProject.title}
              </span>
              <ChevronDown className="size-5 shrink-0 text-muted-foreground" aria-hidden />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            align="start"
            className="flex max-h-[var(--radix-dropdown-menu-content-available-height)] min-w-[16rem] max-w-[20rem] flex-col overflow-hidden"
          >
            <DropdownMenuItem asChild>
              <Link to="/" className="gap-2">
                <FolderPlus className="size-3.5 shrink-0" aria-hidden />
                Create project
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link to="/">All projects</Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <div className="min-h-0 overflow-y-auto">
              {loading ? (
                <p className="px-2 py-1.5 text-xs text-muted-foreground">Loading projects...</p>
              ) : (
                projects.map((project) => {
                  const isActive = project.id === activeProject.id;
                  return (
                    <DropdownMenuItem
                      key={project.id}
                      className={cn(isActive && "bg-muted font-medium text-foreground")}
                      onSelect={() => navigate(`/projects/${project.id}`)}
                    >
                      <span className="min-w-0 flex-1 whitespace-normal">{project.title}</span>
                      {isActive ? (
                        <Check className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />
                      ) : (
                        <span className="size-3.5 shrink-0" aria-hidden />
                      )}
                    </DropdownMenuItem>
                  );
                })
              )}
            </div>
            {onRename ? (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onSelect={() => {
                    setDraftTitle(activeProject.title);
                    setError(null);
                    setRenaming(true);
                  }}
                >
                  <Pencil className="size-3.5 shrink-0" aria-hidden />
                  Rename project
                </DropdownMenuItem>
              </>
            ) : null}
          </DropdownMenuContent>
        </DropdownMenu>
      )}
    </div>
  );
}
