import { ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";

import { AppSystemFooter } from "@/components/AppSystemFooter";
import { CockpitPanelResizeHandle } from "@/components/project/CockpitPanelResizeHandle";
import { useCockpitShellResize } from "@/components/project/cockpitShellLayout";
import { ProjectSwitcher } from "@/components/project/ProjectSwitcher";
import { Button } from "@/components/ui/button";
import type { ProjectDetail, ProjectSummary } from "@/lib/types/project";

export type ProjectNavView = "workbench" | "file" | "draft" | "folder";

export function ProjectLeftNav({
  project,
  projects,
  projectsLoading,
}: {
  project: ProjectDetail;
  projects: ProjectSummary[];
  projectsLoading: boolean;
}) {
  const { onResizeLeftPanel } = useCockpitShellResize();

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="border-b px-3 py-3">
        <Button asChild variant="ghost" size="sm" className="-ml-2 mb-2 h-7 px-2 text-xs">
          <Link to="/">
            <ArrowLeft className="size-3.5" aria-hidden />
            Home
          </Link>
        </Button>

        <ProjectSwitcher
          projects={projects}
          activeProject={project}
          loading={projectsLoading}
        />
      </div>

      <div className="relative min-h-0 flex-1">
        {onResizeLeftPanel ? (
          <CockpitPanelResizeHandle
            ariaLabel="Resize navigation panel"
            edge="end"
            onResize={onResizeLeftPanel}
          />
        ) : null}
      </div>

      <AppSystemFooter className="bg-background" />
    </div>
  );
}
