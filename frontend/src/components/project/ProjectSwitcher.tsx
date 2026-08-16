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
    <div className="shrink-0 px-3 pt-3 pb-2">
      {renaming ? (
        <form
          className="grid gap-1 px-1.5"
          onSubmit={(event) => {
            event.preventDefault();
            void commitRename();
          }}
        >
          <label className="text-[0.65rem] font-medium tracking-[0.08em] text-muted-foreground">
            PROJECT
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
                "flex w-full cursor-pointer items-start gap-2 rounded-md px-1.5 py-1.5 text-left text-sm transition-colors outline-none",
                "text-muted-foreground hover:bg-muted/30 hover:text-foreground",
                "focus-visible:bg-muted/30 focus-visible:text-foreground",
                "aria-expanded:bg-muted/30 aria-expanded:text-foreground",
              )}
              aria-label={`Project: ${activeProject.title}`}
              title={activeProject.title}
            >
              <FolderOpen
                className="mt-0.5 size-4 shrink-0 text-[var(--cockpit-workflow-icon)]"
                aria-hidden
              />
              <span className="min-w-0 flex-1">
                <span className="block text-[0.65rem] font-medium tracking-[0.08em] text-muted-foreground">
                  PROJECT
                </span>
                <span className="mt-0.5 block line-clamp-2 leading-snug text-foreground">
                  {activeProject.title}
                </span>
              </span>
              <ChevronDown className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="min-w-[16rem] max-w-[20rem]">
            <DropdownMenuItem asChild>
              <Link to="/">All projects</Link>
            </DropdownMenuItem>
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
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link to="/" className="gap-2">
                <FolderPlus className="size-3.5 shrink-0" aria-hidden />
                Create project
              </Link>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )}
    </div>
  );
}
