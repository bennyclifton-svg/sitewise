import { ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";

import { AppSystemFooter } from "@/components/AppSystemFooter";
import { ChatRail } from "@/components/chat/ChatRail";
import { CockpitPanelResizeHandle } from "@/components/project/CockpitPanelResizeHandle";
import { useCockpitShellResize } from "@/components/project/cockpitShellLayout";
import { ProjectSwitcher } from "@/components/project/ProjectSwitcher";
import { Button } from "@/components/ui/button";
import type { Citation } from "@/lib/types/citation";
import type { ChatMessage, ChatThread } from "@/lib/types/chat";
import type { ProjectDetail, ProjectSummary } from "@/lib/types/project";

export type ProjectNavView = "workbench" | "file" | "draft" | "folder";

type ChatRailConfig = {
  thread: ChatThread | null;
  messages: ChatMessage[];
  chatRevision: number;
  chatLoading: boolean;
  crossProject: boolean;
  selectedCitationId: string | null;
  onCrossProjectChange: (value: boolean) => void;
  onConversationUpdate: () => void;
  onSelectThread: (threadId: string) => void;
  onCreateThread: (thread: ChatThread) => void;
  onActiveThreadDeleted: () => void;
  onSelectCitation: (citation: Citation | null) => void;
};

export function ProjectLeftNav({
  project,
  projects,
  projectsLoading,
  chat,
  chatPreview = false,
}: {
  project: ProjectDetail;
  projects: ProjectSummary[];
  projectsLoading: boolean;
  chat?: ChatRailConfig;
  chatPreview?: boolean;
}) {
  const { onResizeLeftPanel } = useCockpitShellResize();

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="shrink-0 border-b px-3 py-3">
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

      {chat ? (
        <ChatRail
          projectId={project.id}
          projectTitle={project.title}
          thread={chat.thread}
          messages={chat.messages}
          chatRevision={chat.chatRevision}
          chatLoading={chat.chatLoading}
          crossProject={chat.crossProject}
          selectedCitationId={chat.selectedCitationId}
          onCrossProjectChange={chat.onCrossProjectChange}
          onConversationUpdate={chat.onConversationUpdate}
          onSelectThread={chat.onSelectThread}
          onCreateThread={chat.onCreateThread}
          onActiveThreadDeleted={chat.onActiveThreadDeleted}
          onSelectCitation={chat.onSelectCitation}
        />
      ) : chatPreview ? (
        <div className="flex min-h-0 flex-1 flex-col">
          <header className="flex shrink-0 items-center gap-2 border-b px-3 py-2">
            <div className="min-w-0 flex-1">
              <h2 className="text-sm font-semibold">Clerk</h2>
              <p className="truncate text-xs text-muted-foreground">
                Preview only. Real chat opens inside a backend project cockpit.
              </p>
            </div>
          </header>
          <p className="px-3 py-3 text-sm text-muted-foreground">
            Connect the backend to use the project chat rail.
          </p>
        </div>
      ) : (
        <div className="relative min-h-0 flex-1">
          {onResizeLeftPanel ? (
            <CockpitPanelResizeHandle
              ariaLabel="Resize navigation panel"
              edge="end"
              onResize={onResizeLeftPanel}
            />
          ) : null}
        </div>
      )}

      <AppSystemFooter />
    </div>
  );
}
