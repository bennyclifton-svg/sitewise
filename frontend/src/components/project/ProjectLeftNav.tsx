import { History } from "lucide-react";
import { Link } from "react-router-dom";

import { AppSystemFooter } from "@/components/AppSystemFooter";
import { ChatHistoryNav } from "@/components/chat/ChatHistoryNav";
import { SitewiseMark } from "@/components/SitewiseMark";
import { CockpitPanelResizeHandle } from "@/components/project/CockpitPanelResizeHandle";
import { useCockpitShellResize } from "@/components/project/cockpitShellLayout";
import { ProjectSwitcher } from "@/components/project/ProjectSwitcher";
import { ProjectWorkflowNav } from "@/components/project/ProjectWorkflowNav";
import type { WorkflowTile } from "@/components/project/workflow/workflowTiles";
import type { ChatThread } from "@/lib/types/chat";
import type { ProjectDetail, ProjectSummary } from "@/lib/types/project";

export type ProjectNavView = "workbench" | "file" | "draft" | "folder" | "knowledge";

type ChatHistoryConfig = {
  projectId: string;
  activeThreadId?: string;
  onSelectThread: (threadId: string) => void;
  onCreateSession: (thread: ChatThread) => void;
  onActiveThreadDeleted: () => void;
};

type WorkflowNavConfig = {
  tiles: WorkflowTile[];
  selectedWorkflowId: string;
  onSelectWorkflow: (workflowId: string) => void;
};

export function ProjectLeftNav({
  project,
  projects,
  projectsLoading,
  workflows,
  chatHistory,
  chatHistoryPreview = false,
}: {
  project: ProjectDetail;
  projects: ProjectSummary[];
  projectsLoading: boolean;
  workflows?: WorkflowNavConfig;
  chatHistory?: ChatHistoryConfig;
  chatHistoryPreview?: boolean;
}) {
  const { onResizeLeftPanel } = useCockpitShellResize();

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex h-[var(--cockpit-ribbon-height)] shrink-0 items-center px-3 pl-6">
        <Link
          to="/"
          aria-label="SiteWise home"
          title="SiteWise"
          className="inline-flex sw-transition opacity-95 hover:opacity-100"
        >
          <SitewiseMark size={48} variant="full" className="!p-1.5" />
        </Link>
      </div>

      {workflows ? (
        <ProjectWorkflowNav
          tiles={workflows.tiles}
          selectedWorkflowId={workflows.selectedWorkflowId}
          onSelectWorkflow={workflows.onSelectWorkflow}
          leading={
            <ProjectSwitcher
              projects={projects}
              activeProject={project}
              loading={projectsLoading}
            />
          }
        />
      ) : (
        <nav className="shrink-0 px-3 pt-10 pb-2" aria-label="Project">
          <ul className="flex flex-col gap-0.5">
            <li>
              <ProjectSwitcher
                projects={projects}
                activeProject={project}
                loading={projectsLoading}
              />
            </li>
          </ul>
        </nav>
      )}

      <div className="relative min-h-0 flex-1">
        {onResizeLeftPanel ? (
          <CockpitPanelResizeHandle
            ariaLabel="Resize navigation panel"
            edge="end"
            onResize={onResizeLeftPanel}
          />
        ) : null}
      </div>

      {chatHistory ? (
        <ChatHistoryNav
          projectId={chatHistory.projectId}
          activeThreadId={chatHistory.activeThreadId}
          onSelectThread={chatHistory.onSelectThread}
          onCreateSession={chatHistory.onCreateSession}
          onActiveThreadDeleted={chatHistory.onActiveThreadDeleted}
        />
      ) : chatHistoryPreview ? (
        <section
          className="flex min-h-0 max-h-[min(24rem,52%)] flex-col"
          aria-label="Chat history preview"
        >
          <header className="shrink-0 px-3 py-2">
            <div className="flex items-center gap-2 px-1.5 py-1.5">
              <History className="size-4 shrink-0" aria-hidden />
              <span className="text-sm font-semibold">History</span>
            </div>
          </header>
          <p className="px-3 py-3 text-sm text-muted-foreground">
            Connect the backend to browse project chat sessions.
          </p>
        </section>
      ) : null}

      <div className="relative min-h-0 flex-1">
        {onResizeLeftPanel ? (
          <CockpitPanelResizeHandle
            ariaLabel="Resize navigation panel"
            edge="end"
            onResize={onResizeLeftPanel}
          />
        ) : null}
      </div>

      <AppSystemFooter className="border-t-0" />
    </div>
  );
}
