import { ArrowLeft, Bot, Send } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { DocumentRepositoryPanel } from "@/components/project/DocumentRepositoryPanel";
import { DraftReviewPanel } from "@/components/project/DraftReviewPanel";
import { WorkspaceFilePanel } from "@/components/project/WorkspaceFilePanel";
import { ProjectControlBoard } from "@/components/project/ProjectControlBoard";
import { ProjectLeftNav, type ProjectNavView } from "@/components/project/ProjectLeftNav";
import { isCostPlanWorkspaceFile, isPmpWorkspaceFile } from "@/components/project/workflow/workspaceRouting";
import { ProjectShell } from "@/components/project/ProjectShell";
import { WorkspaceFolderPanel } from "@/components/project/WorkspaceFolderPanel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type {
  DraftArtifact,
  EvidencePreview,
  PlatformKnowledgeStatus,
  ProjectDetail,
  WorkflowTraceEvent,
  WorkspaceTreeNode,
} from "@/lib/types/project";

const previewProject: ProjectDetail = {
  id: "preview-project",
  slug: "sitewise-preview",
  title: "SiteWise Cockpit Preview",
  workspace_path: "04-projects/sitewise-preview",
  phase: "brief-planning",
  archetype: "renovation",
  user_role: "architect-pm",
  state: "NSW",
  status: "preview",
  updated_at: new Date().toISOString(),
  metadata: {
    preview: true,
  },
  overlay_status: {
    ready: true,
    missing: [],
    invalid: [],
  },
  evidence_preview: null,
};

const previewEvidence: EvidencePreview[] = [
  {
    id: "ev-brief",
    title: "Client brief extract",
    filename: "client-brief.md",
    relative_path: "04-projects/sitewise-preview/00-brief-pmp/client-brief.md",
    source_type: "project_evidence",
    document_class: "brief",
    excerpt:
      "The project scope includes early procurement planning, consultant coordination, cost control, programme setup, and evidence-backed PM reporting.",
    content: [
      "# Client Brief Extract",
      "",
      "## Scope",
      "",
      "The project scope includes early procurement planning, consultant coordination, cost control, programme setup, and evidence-backed PM reporting.",
      "",
      "## Initial Priorities",
      "",
      "| Priority | Status | Owner |",
      "| --- | --- | --- |",
      "| Consultant appointments | Open | Architect PM |",
      "| Cost plan validation | Open | Quantity surveyor |",
      "| Programme baseline | Draft | Project lead |",
    ].join("\n"),
  },
  {
    id: "ev-cost",
    title: "Cost planning note",
    filename: "cost-planning-note.md",
    relative_path: "04-projects/sitewise-preview/01-cost/cost-planning-note.md",
    source_type: "project_evidence",
    document_class: "cost_plan",
    excerpt:
      "Current cost assumptions require validation against tender returns, authority conditions, and identified project risks before approval.",
    content: [
      "# Cost Planning Note",
      "",
      "## Budget Checks",
      "",
      "| Item | Current basis | Next check |",
      "| --- | --- | --- |",
      "| Construction budget | Order-of-cost allowance | Tender return comparison |",
      "| Consultant fees | Fee proposals | Appointment schedule |",
      "| Contingency | Risk allowance | Risk register update |",
    ].join("\n"),
  },
  {
    id: "ev-procurement",
    title: "Procurement register sample",
    filename: "procurement-register.md",
    relative_path: "04-projects/sitewise-preview/05-procurement/procurement-register.md",
    source_type: "project_evidence",
    document_class: "register",
    excerpt:
      "Open procurement items include builder market sounding, consultant scope alignment, and a tender recommendation report draft.",
    content: [
      "# Procurement Register Sample",
      "",
      "## Open Items",
      "",
      "| Ref | Item | Status |",
      "| --- | --- | --- |",
      "| PR-01 | Builder market sounding | Open |",
      "| PR-02 | Consultant scope alignment | In progress |",
      "| PR-03 | Tender recommendation report draft | Not started |",
    ].join("\n"),
  },
];

const previewWorkspaceTree: WorkspaceTreeNode[] = [
  templateNode("00-brief-pmp", "04-projects/sitewise-preview/00-brief-pmp", "Brief, project setup, and PMP drafts.", ["create_pmp"], [
    fileNode("client-brief.md", "04-projects/sitewise-preview/00-brief-pmp/client-brief.md"),
    fileNode("PMP.md", "04-projects/sitewise-preview/00-brief-pmp/PMP.md"),
  ]),
  templateNode("01-cost", "04-projects/sitewise-preview/01-cost", "Cost plans, claims, invoices, and variations.", ["create_cost_plan"], [
    fileNode("cost-planning-note.md", "04-projects/sitewise-preview/01-cost/cost-planning-note.md"),
  ]),
  templateNode("02-consultant", "04-projects/sitewise-preview/02-consultant", "Consultant scopes and RFP records.", ["consultant_procurement"]),
  templateNode("03-design", "04-projects/sitewise-preview/03-design", "Design documents and RFIs.", ["rfi"]),
  templateNode("04-planning-and-authorities", "04-projects/sitewise-preview/04-planning-and-authorities", "Approvals, certificates, and authority correspondence.", ["approval_pathway"]),
  templateNode("05-procurement", "04-projects/sitewise-preview/05-procurement", "Tender packages, submissions, evaluation, and TRR drafts.", ["tender_evaluation"], [
    fileNode("procurement-register.md", "04-projects/sitewise-preview/05-procurement/procurement-register.md"),
  ]),
  templateNode("06-programme", "04-projects/sitewise-preview/06-programme", "Baseline programme and time-risk evidence.", ["programme"]),
  templateNode("07-construction", "04-projects/sitewise-preview/07-construction", "Construction phase records and registers.", ["risk_register"], [
    templateNode("02-rfis", "04-projects/sitewise-preview/07-construction/02-rfis", "Construction RFIs and responses.", ["rfi"]),
    templateNode("06-variations", "04-projects/sitewise-preview/07-construction/06-variations", "Variation submissions and approvals.", ["process_variations"]),
  ]),
  templateNode("08-reporting", "04-projects/sitewise-preview/08-reporting", "Project reports and status outputs.", ["project_report"]),
  templateNode("09-handover-dlp", "04-projects/sitewise-preview/09-handover-dlp", "Handover and defects liability period records.", ["handover_closeout"]),
];

const platformStatus: PlatformKnowledgeStatus = {
  available: true,
  buckets: [
    { kind: "doctrine", document_count: 1 },
    { kind: "seed", document_count: 6 },
    { kind: "skills", document_count: 4 },
  ],
};

const previewTrace: WorkflowTraceEvent[] = [
  {
    step: "gate",
    status: "passed",
    message: "SiteWise three-overlay gate passed.",
    metadata: {},
  },
  {
    step: "retrieval",
    status: "complete",
    message: "Retrieved preview project evidence and SiteWise platform knowledge.",
    metadata: {
      project_passages: 3,
      platform_passages: 4,
      total_passages: 7,
    },
  },
  {
    step: "draft_save",
    status: "complete",
    message: "Preview draft artefact is ready for review.",
    metadata: {
      version: 2,
    },
  },
];

const previewDraft: DraftArtifact = {
  id: "preview-draft",
  project_id: previewProject.id,
  workflow_type: "create_pmp",
  version: 2,
  status: "draft",
  title: "Preview Project Management Plan",
  workspace_path: "04-projects/sitewise-preview/00-brief-pmp/PMP.md",
  author_user_id: "preview-user",
  content_markdown: [
    "# Preview Project Management Plan",
    "",
    "## Facts",
    "",
    "- This preview demonstrates the Clerk cockpit shell without requiring the backend project catalog.",
    "- The real Create PMP workflow remains backend-owned and project-scoped.",
    "",
    "## Assumptions",
    "",
    "- Project evidence, seed knowledge, and workflow state will be supplied by Clerk's hosted API once the backend is running.",
    "",
    "## Recommended next actions",
    "",
    "- Start the backend service.",
    "- Open a real project cockpit from the project catalog.",
    "- Run Create PMP and review the saved draft artefact with provenance.",
  ].join("\n"),
  model: "preview",
  runtime: "frontend-preview",
  provenance_metadata: {
    seed_consulted: ["01-seed/setup-and-commission-guide.md"],
    evidence_refs: previewEvidence.map((item) => item.relative_path),
    context_refs: ["docs/plans/2026-06-07-cockpit-shell-v2-frontend-plan.md"],
    trace: previewTrace,
  },
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

const previewProjects = [previewProject];

export function CockpitPreviewPage() {
  const [activeView, setActiveView] = useState<ProjectNavView>("workbench");
  const [selectedEvidenceId, setSelectedEvidenceId] = useState(previewEvidence[0].id);
  const [selectedWorkspacePath, setSelectedWorkspacePath] = useState(previewWorkspaceTree[0].path);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState("create-pmp");
  const selectedEvidence =
    previewEvidence.find((item) => item.id === selectedEvidenceId) ?? previewEvidence[0];
  const selectedFolder = findWorkspaceNode(previewWorkspaceTree, selectedWorkspacePath);
  const repositoryEvidence = selectedEvidenceId
    ? previewEvidence.find((item) => item.id === selectedEvidenceId) ?? null
    : null;
  const draftEvidencePanel =
    repositoryEvidence &&
    normalizeWorkspacePath(repositoryEvidence.relative_path) !==
      normalizeWorkspacePath(previewDraft.workspace_path)
      ? repositoryEvidence
      : null;

  function selectEvidenceFromRepository(evidenceId: string) {
    setSelectedEvidenceId(evidenceId);
    const item = previewEvidence.find((candidate) => candidate.id === evidenceId);
    if (item) {
      setSelectedWorkspacePath(normalizeWorkspacePath(item.relative_path));
      if (isPmpWorkspaceFile(item.relative_path)) {
        setSelectedWorkflowId("create-pmp");
        setActiveView("draft");
        return;
      }
      if (isCostPlanWorkspaceFile(item.relative_path)) {
        setSelectedWorkflowId("cost-plan");
        setActiveView("draft");
        return;
      }
    }
    if (activeView === "draft") {
      return;
    }
    setActiveView("file");
  }

  function selectWorkspacePath(path: string) {
    setSelectedWorkspacePath(path);
    const selectedNode = findWorkspaceNode(previewWorkspaceTree, path);
    if (selectedNode?.kind === "file") {
      if (isPmpWorkspaceFile(selectedNode.path)) {
        setSelectedWorkflowId("create-pmp");
        setActiveView("draft");
        return;
      }
      if (isCostPlanWorkspaceFile(selectedNode.path)) {
        setSelectedWorkflowId("cost-plan");
        setActiveView("draft");
        return;
      }
      const selectedDocument = findEvidenceByPath(previewEvidence, selectedNode.path);
      if (selectedDocument) {
        setSelectedEvidenceId(selectedDocument.id);
        setActiveView("file");
        return;
      }
    }
    setActiveView("folder");
  }

  return (
    <ProjectShell
      onShowWorkbench={() => setActiveView("workbench")}
      leftNav={
        <ProjectLeftNav
          project={previewProject}
          projects={previewProjects}
          projectsLoading={false}
          platformStatus={platformStatus}
        />
      }
      repository={
        <DocumentRepositoryPanel
          projectId="00000000-0000-0000-0000-000000000000"
          evidence={previewEvidence}
          selectedEvidenceId={selectedEvidence.id}
          workspaceTree={previewWorkspaceTree}
          selectedWorkspacePath={selectedWorkspacePath}
          onSelectEvidence={selectEvidenceFromRepository}
          onSelectWorkspacePath={selectWorkspacePath}
          onOpenWorkflow={setSelectedWorkflowId}
          onViewWorkbench={() => setActiveView("workbench")}
          onViewFolder={() => setActiveView("folder")}
          onUploadComplete={async () => {}}
        />
      }
      chatBar={<PreviewChatBar />}
    >
      <div className="border-b bg-amber-50 px-4 py-2 text-sm text-amber-900">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3">
          <span>
            Cockpit preview: this surface uses sample data so the shell is visible while
            the backend project catalog is unavailable.
          </span>
          <Button asChild variant="outline" size="sm" className="bg-background">
            <Link to="/">
              <ArrowLeft className="size-4" aria-hidden />
              Back home
            </Link>
          </Button>
        </div>
      </div>
      {activeView === "workbench" ? (
        <ProjectControlBoard
          project={previewProject}
          evidence={previewEvidence}
          latestDraft={previewDraft}
          latestCostPlanDraft={null}
          trace={previewTrace}
          costPlanTrace={[]}
          workflowError={null}
          costPlanWorkflowError={null}
          isRunningWorkflow={false}
          isRunningCostPlan={false}
          selectedWorkflowId={selectedWorkflowId}
          onSelectWorkflow={setSelectedWorkflowId}
          onRunCreatePmp={() => setActiveView("draft")}
          onRunUpdatePmp={() => setActiveView("draft")}
          onRunCreateCostPlan={() => setActiveView("draft")}
          onRunSortFiles={() => undefined}
          onOpenDraft={() => setActiveView("draft")}
          onOpenTenderComparison={() => undefined}
          inboxCount={0}
          sortFilesResult={null}
          sortFilesDraft={null}
          sortFilesError={null}
          isRunningSortFiles={false}
        />
      ) : null}
      {activeView === "file" ? (
        <WorkspaceFilePanel projectId={previewProject.id} evidence={selectedEvidence} />
      ) : null}
      {activeView === "folder" ? (
        <WorkspaceFolderPanel folder={selectedFolder} evidence={previewEvidence} />
      ) : null}
      {activeView === "draft" ? (
        <>
          <DraftReviewPanel
            projectId={previewProject.id}
            draft={previewDraft}
            onDraftUpdated={() => undefined}
          />
          {draftEvidencePanel ? (
            <WorkspaceFilePanel
              projectId={previewProject.id}
              evidence={draftEvidencePanel}
            />
          ) : null}
        </>
      ) : null}
    </ProjectShell>
  );
}

function templateNode(
  name: string,
  path: string,
  description: string,
  relatedWorkflows: string[],
  children: WorkspaceTreeNode[] = [],
): WorkspaceTreeNode {
  return {
    name,
    path,
    kind: "directory",
    description,
    document_count: 0,
    related_workflows: relatedWorkflows,
    children,
  };
}

function fileNode(name: string, path: string): WorkspaceTreeNode {
  return {
    name,
    path,
    kind: "file",
    description: name,
    document_count: 1,
    related_workflows: [],
    children: [],
  };
}

function findWorkspaceNode(
  nodes: WorkspaceTreeNode[],
  path: string,
): WorkspaceTreeNode | null {
  for (const node of nodes) {
    if (node.path === path) return node;
    const childMatch = findWorkspaceNode(node.children, path);
    if (childMatch) return childMatch;
  }
  return null;
}

function findEvidenceByPath(
  evidence: EvidencePreview[],
  path: string,
): EvidencePreview | null {
  const selectedPath = normalizeWorkspacePath(path);
  return (
    evidence.find((item) => normalizeWorkspacePath(item.relative_path) === selectedPath) ?? null
  );
}

function normalizeWorkspacePath(path: string): string {
  return path.replaceAll("\\", "/");
}

function PreviewChatBar() {
  return (
    <section className="border-t bg-background" aria-label="Preview chat">
      <header className="flex min-h-14 items-center justify-between gap-3 px-4 py-2">
        <div className="flex min-w-0 items-center gap-3">
          <span className="grid size-8 shrink-0 place-items-center rounded-md bg-muted">
            <Bot className="size-4" aria-hidden />
          </span>
          <div className="min-w-0">
            <h2 className="truncate text-sm font-semibold">Clerk</h2>
            <p className="truncate text-xs text-muted-foreground">
              Preview only. Real chat opens inside a backend project cockpit.
            </p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Badge variant="outline">Project</Badge>
          <Button disabled variant="secondary" size="sm">
            <Send className="size-4" aria-hidden />
            Backend required
          </Button>
        </div>
      </header>
    </section>
  );
}
