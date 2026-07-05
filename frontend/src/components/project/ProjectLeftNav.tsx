import { ArrowLeft, History } from "lucide-react";
import { Link } from "react-router-dom";

import { AppSystemFooter } from "@/components/AppSystemFooter";
import { ChatHistoryNav } from "@/components/chat/ChatHistoryNav";
import { CockpitPanelResizeHandle } from "@/components/project/CockpitPanelResizeHandle";
import { useCockpitShellResize } from "@/components/project/cockpitShellLayout";
import { ProjectSwitcher } from "@/components/project/ProjectSwitcher";
import { ProjectWorkflowNav } from "@/components/project/ProjectWorkflowNav";
import type { WorkflowTile } from "@/components/project/workflow/workflowTiles";
import { Button } from "@/components/ui/button";
import type { ChatThread } from "@/lib/types/chat";
import type { ProjectDetail, ProjectSummary } from "@/lib/types/project";

export type ProjectNavView = "workbench" | "file" | "draft" | "folder";

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
      <div className="shrink-0 px-3 py-3">
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

      {workflows ? (
        <ProjectWorkflowNav
          tiles={workflows.tiles}
          selectedWorkflowId={workflows.selectedWorkflowId}
          onSelectWorkflow={workflows.onSelectWorkflow}
        />
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
          <header className="flex shrink-0 items-center gap-2 px-3 py-2">
            <History className="size-4 shrink-0" aria-hidden />
            <span className="text-sm font-semibold">History</span>
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
