import { Check, ChevronDown, FolderPlus } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
  const navigate = useNavigate();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className={cn(
            "flex w-full cursor-pointer items-center gap-2 rounded-md px-1.5 py-1.5 text-left text-sm transition-colors outline-none",
            "text-muted-foreground hover:bg-muted/30 hover:text-foreground",
            "focus-visible:bg-muted/30 focus-visible:text-foreground",
            "aria-expanded:bg-muted/30 aria-expanded:text-foreground",
          )}
          aria-label={`Project: ${activeProject.title}`}
        >
          {/* Matches workflow nav icon column so the title lines up with labels below. */}
          <span className="size-4 shrink-0" aria-hidden />
          <span className="min-w-0 flex-1 truncate">{activeProject.title}</span>
          <ChevronDown className="size-4 shrink-0 text-muted-foreground" aria-hidden />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="start"
        className="max-h-64 w-[var(--radix-dropdown-menu-trigger-width)] overflow-y-auto"
      >
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
                <span className="min-w-0 flex-1 truncate">{project.title}</span>
                {isActive ? (
                  <Check className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />
                ) : (
                  <span className="size-3.5 shrink-0" aria-hidden />
                )}
              </DropdownMenuItem>
            );
          })
        )}
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link to="/" className="gap-2">
            <FolderPlus className="size-3.5 shrink-0" aria-hidden />
            Create project
          </Link>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
