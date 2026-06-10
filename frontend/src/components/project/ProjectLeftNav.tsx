import {
  ArrowLeft,
  BookOpen,
  Bot,
  FileText,
  FolderTree,
  LayoutDashboard,
  Server,
  ShieldCheck,
} from "lucide-react";
import type { ReactNode } from "react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { AppSystemFooter } from "@/components/AppSystemFooter";
import { NavAccordionSection } from "@/components/project/NavAccordionSection";
import {
  PlatformKnowledgePanel,
  PlatformKnowledgeSummary,
} from "@/components/project/PlatformKnowledgePanel";
import { ProjectSwitcher } from "@/components/project/ProjectSwitcher";
import { WorkspaceExplorer } from "@/components/project/WorkspaceExplorer";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type {
  DraftArtifactSummary,
  PlatformKnowledgeStatus,
  ProjectDetail,
  ProjectSummary,
  WorkspaceTreeNode,
} from "@/lib/types/project";
import { cn } from "@/lib/utils";

export type ProjectNavView = "workbench" | "evidence" | "draft" | "folder";

type NavSectionId = "workspace" | "explorer" | "skills" | "knowledge" | "admin";

export function ProjectLeftNav({
  project,
  projects,
  projectsLoading,
  platformStatus,
  latestDraft,
  activeView,
  evidenceCount,
  workspaceTree,
  selectedWorkspacePath,
  onViewChange,
  onSelectWorkspacePath,
  onOpenWorkflow,
}: {
  project: ProjectDetail;
  projects: ProjectSummary[];
  projectsLoading: boolean;
  platformStatus: PlatformKnowledgeStatus | null;
  latestDraft: DraftArtifactSummary | null;
  activeView: ProjectNavView;
  evidenceCount: number;
  workspaceTree: WorkspaceTreeNode[];
  selectedWorkspacePath: string | null;
  onViewChange: (view: ProjectNavView) => void;
  onSelectWorkspacePath: (path: string) => void;
  onOpenWorkflow: (tileId: string) => void;
}) {
  const [openSections, setOpenSections] = useState<Set<NavSectionId>>(
    () => new Set(["workspace", "explorer", "admin"]),
  );

  function toggleSection(id: NavSectionId) {
    setOpenSections((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="border-b px-4 py-4">
        <Button asChild variant="ghost" size="sm" className="-ml-2 mb-3">
          <Link to="/">
            <ArrowLeft className="size-4" aria-hidden />
            Home
          </Link>
        </Button>

        <ProjectSwitcher
          projects={projects}
          activeProject={project}
          loading={projectsLoading}
        />

        <p className="mt-2 break-all text-xs text-muted-foreground">{project.workspace_path}</p>
        <div className="mt-2 flex flex-wrap gap-2">
          <Badge variant="outline">{project.status}</Badge>
          <Badge variant="secondary">{project.phase}</Badge>
        </div>
      </div>

      <nav className="min-h-0 flex-1 overflow-y-auto px-3 py-3" aria-label="Project cockpit">
        <NavAccordionSection
          label="Workspace"
          icon={LayoutDashboard}
          isOpen={openSections.has("workspace")}
          onToggle={() => toggleSection("workspace")}
        >
          <NavButton
            active={activeView === "workbench"}
            icon={<LayoutDashboard className="size-4" aria-hidden />}
            label="Workbench"
            onClick={() => onViewChange("workbench")}
          />
          <NavButton
            active={activeView === "evidence"}
            icon={<FileText className="size-4" aria-hidden />}
            label={`Evidence (${evidenceCount})`}
            onClick={() => onViewChange("evidence")}
          />
          <NavButton
            active={activeView === "draft"}
            disabled={!latestDraft}
            icon={<Bot className="size-4" aria-hidden />}
            label={latestDraft ? `PMP Draft v${latestDraft.version}` : "PMP Draft"}
            onClick={() => onViewChange("draft")}
          />
        </NavAccordionSection>

        <NavAccordionSection
          label="Explorer"
          icon={FolderTree}
          isOpen={openSections.has("explorer")}
          onToggle={() => toggleSection("explorer")}
        >
          <WorkspaceExplorer
            tree={workspaceTree}
            selectedPath={selectedWorkspacePath}
            onSelectPath={onSelectWorkspacePath}
            onOpenWorkflow={onOpenWorkflow}
            onViewWorkbench={() => onViewChange("workbench")}
            onViewFolder={() => onViewChange("folder")}
          />
        </NavAccordionSection>

        <NavAccordionSection
          label="Skills"
          icon={ShieldCheck}
          isOpen={openSections.has("skills")}
          onToggle={() => toggleSection("skills")}
        >
          <PlatformKnowledgePanel platformStatus={platformStatus} mode="skills" />
        </NavAccordionSection>

        <NavAccordionSection
          label="Knowledge"
          icon={BookOpen}
          isOpen={openSections.has("knowledge")}
          onToggle={() => toggleSection("knowledge")}
        >
          <PlatformKnowledgePanel platformStatus={platformStatus} mode="knowledge" />
        </NavAccordionSection>

        <NavAccordionSection
          label="Admin"
          icon={Server}
          isOpen={openSections.has("admin")}
          onToggle={() => toggleSection("admin")}
        >
          <PlatformKnowledgeSummary platformStatus={platformStatus} />
        </NavAccordionSection>
      </nav>

      <AppSystemFooter />
    </div>
  );
}

function NavButton({
  active,
  disabled = false,
  icon,
  label,
  onClick,
}: {
  active: boolean;
  disabled?: boolean;
  icon: ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      className={cn(
        "flex h-9 w-full items-center gap-2 rounded-md px-2 text-left text-sm transition-colors",
        active ? "bg-muted font-medium" : "text-muted-foreground hover:bg-muted/70 hover:text-foreground",
        disabled && "cursor-not-allowed opacity-50 hover:bg-transparent",
      )}
      onClick={onClick}
    >
      {icon}
      <span className="min-w-0 truncate">{label}</span>
    </button>
  );
}
