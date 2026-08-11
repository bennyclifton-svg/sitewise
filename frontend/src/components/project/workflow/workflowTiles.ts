import {
  BriefcaseBusiness,
  ClipboardList,
  FileText,
  HandCoins,
  Settings2,
  type LucideIcon,
} from "lucide-react";

import type { WorkflowStatus } from "@/components/project/workflow/workflowStatus";
import type { DraftArtifactSummary, ProjectDetail } from "@/lib/types/project";

export type WorkflowTile = {
  id: string;
  label: string;
  folder: string;
  icon: LucideIcon;
  status: WorkflowStatus;
  statusLabel: string;
  description: string;
  implemented: boolean;
  attention?: boolean;
};

export function buildLifecycleTiles({
  project,
  latestDraft,
  latestCostPlanDraft,
  workflowError,
  costPlanWorkflowError,
  isRunningWorkflow,
  isRunningCostPlan,
  procurementError = null,
  isRunningProcurement = false,
}: {
  project: ProjectDetail;
  latestDraft: DraftArtifactSummary | null;
  latestCostPlanDraft: DraftArtifactSummary | null;
  workflowError: string | null;
  costPlanWorkflowError: string | null;
  isRunningWorkflow: boolean;
  isRunningCostPlan: boolean;
  procurementError?: string | null;
  isRunningProcurement?: boolean;
}): WorkflowTile[] {
  const capabilities = project.workflow_capabilities?.capabilities;
  const tenderCapability = capabilities?.tender_comparison;
  const consultantProcurementCapability = capabilities?.consultant_procurement;
  const tradeProcurementCapability = capabilities?.trade_procurement;
  const procurementTileStatus = procurementStatus({
    consultantCapability: consultantProcurementCapability,
    tradeCapability: tradeProcurementCapability,
    error: procurementError,
    isRunning: isRunningProcurement,
  });
  const createPmpStatus = getCreatePmpStatus({
    project,
    latestDraft,
    workflowError,
    isRunningWorkflow,
  });
  const costPlanStatus = getCreateCostPlanStatus({
    project,
    latestDraft: latestCostPlanDraft,
    workflowError: costPlanWorkflowError,
    isRunningWorkflow: isRunningCostPlan,
  });

  return [
    {
      id: "project-profile",
      label: "Project Profile",
      folder: "00-brief-pmp",
      icon: Settings2,
      status: project.overlay_status.ready ? "ready" : "blocked",
      statusLabel: project.overlay_status.ready ? "Ready" : "Blocked",
      description:
        "Set your role, state, building class, and work type so SiteWise overlays and workflow gates match this project.",
      implemented: true,
      attention: hasIdentityReviewMarker(project),
    },
    {
      id: "create-pmp",
      label: "Project Plan",
      folder: "00-brief-pmp",
      icon: FileText,
      status: createPmpStatus.status,
      statusLabel: createPmpStatus.label,
      description:
        "Create and review the project management plan from active project evidence and SiteWise knowledge.",
      implemented: true,
    },
    {
      id: "cost-plan",
      label: "Cost Plan",
      folder: "01-cost",
      icon: HandCoins,
      status: costPlanStatus.status,
      statusLabel: costPlanStatus.label,
      description:
        "Create and review the project cost plan from cost evidence, claims, and SiteWise cost doctrine.",
      implemented: true,
    },
    {
      id: "procurement-requests",
      label: "Procurement",
      folder: "05-procurement",
      icon: ClipboardList,
      status: procurementTileStatus.status,
      statusLabel: procurementTileStatus.label,
      description:
        "Prepare consultant proposals, trade quotations, or head-contractor tenders and review the latest draft.",
      implemented: true,
    },
    {
      id: "procurement",
      label: "Tender Comparison",
      folder: "05-procurement",
      icon: BriefcaseBusiness,
      status: tenderCapability && tenderCapability.status !== "supported" ? "blocked" : "ready",
      statusLabel:
        tenderCapability && tenderCapability.status !== "supported" ? "Blocked" : "Ready",
      description:
        "Create tender comparisons, review QA, inspect the matrix, and approve reports.",
      implemented: true,
    },
  ];
}

function hasIdentityReviewMarker(project: ProjectDetail): boolean {
  return Boolean(project.metadata?.identity_review?.fields?.length);
}

function procurementStatus({
  consultantCapability,
  tradeCapability,
  error,
  isRunning,
}: {
  consultantCapability: { status: string } | undefined;
  tradeCapability: { status: string } | undefined;
  error: string | null;
  isRunning: boolean;
}): { status: WorkflowStatus; label: string } {
  if (isRunning) return { status: "running", label: "Running" };
  if (error) return { status: "failed", label: "Failed" };
  if (
    consultantCapability?.status === "supported" ||
    tradeCapability?.status === "supported" ||
    (!consultantCapability && !tradeCapability)
  ) {
    return { status: "ready", label: "Ready" };
  }
  return { status: "blocked", label: "Blocked" };
}

function getCreatePmpStatus({
  project,
  latestDraft,
  workflowError,
  isRunningWorkflow,
}: {
  project: ProjectDetail;
  latestDraft: DraftArtifactSummary | null;
  workflowError: string | null;
  isRunningWorkflow: boolean;
}): { status: WorkflowStatus; label: string } {
  if (isRunningWorkflow) return { status: "running", label: "Running" };
  if (workflowError) return { status: "failed", label: "Failed" };
  const capability = project.workflow_capabilities?.capabilities.create_pmp;
  if (capability && capability.status !== "supported") {
    return { status: "blocked", label: "Blocked" };
  }
  if (!project.overlay_status.ready) return { status: "blocked", label: "Blocked" };
  if (latestDraft) return { status: "draft", label: `Draft v${latestDraft.version}` };
  return { status: "ready", label: "Ready" };
}

function getCreateCostPlanStatus({
  project,
  latestDraft,
  workflowError,
  isRunningWorkflow,
}: {
  project: ProjectDetail;
  latestDraft: DraftArtifactSummary | null;
  workflowError: string | null;
  isRunningWorkflow: boolean;
}): { status: WorkflowStatus; label: string } {
  if (isRunningWorkflow) return { status: "running", label: "Running" };
  if (workflowError) return { status: "failed", label: "Failed" };
  const capability = project.workflow_capabilities?.capabilities.create_cost_plan;
  if (capability && capability.status !== "supported") {
    return { status: "blocked", label: "Blocked" };
  }
  if (!project.overlay_status.ready) return { status: "blocked", label: "Blocked" };
  if (latestDraft) return { status: "draft", label: `Draft v${latestDraft.version}` };
  return { status: "ready", label: "Ready" };
}
