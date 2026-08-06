import { ChevronDown, FolderPlus } from "lucide-react";
import { useRef } from "react";
import { Link, useNavigate } from "react-router-dom";

import type { ProjectSummary } from "@/lib/types/project";
import { cn } from "@/lib/utils";

export function ProjectSwitcher({
  projects,
  activeProject,
  loading = false,
}: {
  projects: ProjectSummary[];
  activeProject: ProjectSummary;
  loading?: boolean;
}) {
  const detailsRef = useRef<HTMLDetailsElement>(null);
  const navigate = useNavigate();

  function closeMenu() {
    if (detailsRef.current) detailsRef.current.open = false;
  }

  function openProject(projectId: string) {
    closeMenu();
    navigate(`/projects/${projectId}`);
  }

  return (
    <details ref={detailsRef} className="group relative">
      <summary
        className={cn(
          "flex w-full cursor-pointer list-none items-center gap-2 rounded-md px-1.5 py-1.5 text-left text-sm transition-colors",
          "text-muted-foreground hover:bg-muted/30 hover:text-foreground",
          "[&::-webkit-details-marker]:hidden",
        )}
      >
        {/* Matches workflow nav icon column so the title lines up with labels below. */}
        <span className="size-4 shrink-0" aria-hidden />
        <span className="min-w-0 flex-1 truncate">{activeProject.title}</span>
        <ChevronDown
          className="size-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-180"
          aria-hidden
        />
      </summary>
      <div className="sw-surface sw-contact absolute left-0 right-0 z-20 mt-1 max-h-64 overflow-y-auto p-1 hover:translate-y-0">
        <Link
          to="/"
          className="flex w-full rounded-md px-3 py-2 text-left text-sm transition-colors hover:bg-muted"
          onClick={closeMenu}
        >
          All projects
        </Link>
        {loading ? (
          <p className="px-3 py-2 text-xs text-muted-foreground">Loading projects...</p>
        ) : (
          projects.map((project) => (
            <button
              key={project.id}
              type="button"
              className={cn(
                "flex w-full items-center rounded-md px-3 py-2 text-left text-sm transition-colors hover:bg-muted",
                project.id === activeProject.id && "bg-muted font-medium text-foreground",
              )}
              onClick={() => openProject(project.id)}
            >
              <span className="min-w-0 truncate">{project.title}</span>
            </button>
          ))
        )}
        <Link
          to="/"
          className="mt-1 flex w-full items-center gap-2 rounded-md border-t px-3 py-2 text-left text-sm transition-colors hover:bg-muted"
          onClick={closeMenu}
        >
          <FolderPlus className="size-4 shrink-0" aria-hidden />
          Create project
        </Link>
      </div>
    </details>
  );
}
