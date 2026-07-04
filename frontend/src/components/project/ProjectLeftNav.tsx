import { ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";
import { useState } from "react";

import { AppSystemFooter } from "@/components/AppSystemFooter";
import { NavAccordionSection } from "@/components/project/NavAccordionSection";
import {
  PlatformKnowledgePanel,
  PlatformKnowledgeSummary,
} from "@/components/project/PlatformKnowledgePanel";
import { ProjectSwitcher } from "@/components/project/ProjectSwitcher";
import { Button } from "@/components/ui/button";
import type {
  PlatformKnowledgeStatus,
  ProjectDetail,
  ProjectSummary,
} from "@/lib/types/project";

type NavSectionId = "skills" | "knowledge" | "admin";

export type ProjectNavView = "workbench" | "file" | "draft" | "folder";

export function ProjectLeftNav({
  project,
  projects,
  projectsLoading,
  platformStatus,
}: {
  project: ProjectDetail;
  projects: ProjectSummary[];
  projectsLoading: boolean;
  platformStatus: PlatformKnowledgeStatus | null;
}) {
  const [openSections, setOpenSections] = useState<Set<NavSectionId>>(
    () => new Set(["admin"]),
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

      <nav className="min-h-0 flex-1 overflow-y-auto px-2 py-2" aria-label="Project cockpit">
        <NavAccordionSection
          label="Skills"
          isOpen={openSections.has("skills")}
          onToggle={() => toggleSection("skills")}
        >
          <PlatformKnowledgePanel platformStatus={platformStatus} mode="skills" />
        </NavAccordionSection>

        <NavAccordionSection
          label="Knowledge"
          isOpen={openSections.has("knowledge")}
          onToggle={() => toggleSection("knowledge")}
        >
          <PlatformKnowledgePanel platformStatus={platformStatus} mode="knowledge" />
        </NavAccordionSection>

        <NavAccordionSection
          label="Admin"
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
