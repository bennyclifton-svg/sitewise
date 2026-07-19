import type { UIMessage } from "ai";

type MessagePart = UIMessage["parts"][number];

type RecordLike = Record<string, unknown>;

export type ToolStatusState = "running" | "done" | "error";

export type ToolStatusEvent = {
  kind: "tool";
  tool: string;
  state: ToolStatusState;
  message: string;
  stage?: string;
  knowledgePath?: string;
  sectionIds?: string[];
  percent?: number;
  doneUnits?: number;
  totalUnits?: number;
};

export type ArtefactEvent = {
  kind: "artefact";
  title: string;
  workflowType?: string;
  draftId?: string;
  comparisonId?: string;
  projectId?: string;
};

export type ResourceEvent = {
  kind: "resource";
  projectId: string;
  resourceType: string;
  resourceId: string;
  action: string;
  revision?: number;
  changedFields: string[];
  clearedFields: string[];
};

function isRecord(value: unknown): value is RecordLike {
  return typeof value === "object" && value !== null;
}

function clerkStatusData(part: MessagePart): RecordLike | null {
  if (part.type !== "data-clerk-status") return null;
  const data = (part as { data?: unknown }).data;
  return isRecord(data) ? data : null;
}

export function toolStatusFromPart(part: MessagePart): ToolStatusEvent | null {
  const data = clerkStatusData(part);
  if (!data || data.kind !== "tool") return null;
  if (typeof data.tool !== "string" || typeof data.message !== "string") return null;
  if (
    data.state !== "running" &&
    data.state !== "done" &&
    data.state !== "error"
  ) {
    return null;
  }
  return {
    kind: "tool",
    tool: data.tool,
    state: data.state,
    message: data.message,
    stage: typeof data.stage === "string" ? data.stage : undefined,
    knowledgePath:
      typeof data.knowledge_path === "string" ? data.knowledge_path : undefined,
    sectionIds: Array.isArray(data.section_ids)
      ? data.section_ids.filter((item): item is string => typeof item === "string")
      : undefined,
    percent: typeof data.percent === "number" ? data.percent : undefined,
    doneUnits: typeof data.doneUnits === "number" ? data.doneUnits : undefined,
    totalUnits:
      typeof data.totalUnits === "number" ? data.totalUnits : undefined,
  };
}

export function artefactFromPart(part: MessagePart): ArtefactEvent | null {
  const data = clerkStatusData(part);
  if (!data || data.kind !== "artefact") return null;
  const title = typeof data.title === "string" ? data.title : "Artefact";
  return {
    kind: "artefact",
    title,
    workflowType:
      typeof data.workflowType === "string" ? data.workflowType : undefined,
    draftId: typeof data.draftId === "string" ? data.draftId : undefined,
    comparisonId:
      typeof data.comparisonId === "string" ? data.comparisonId : undefined,
    projectId: typeof data.projectId === "string" ? data.projectId : undefined,
  };
}

export function resourceFromPart(part: MessagePart): ResourceEvent | null {
  const data = clerkStatusData(part);
  if (!data || data.kind !== "resource") return null;
  if (
    typeof data.projectId !== "string" ||
    typeof data.resourceType !== "string" ||
    typeof data.resourceId !== "string" ||
    typeof data.action !== "string"
  ) {
    return null;
  }
  return {
    kind: "resource",
    projectId: data.projectId,
    resourceType: data.resourceType,
    resourceId: data.resourceId,
    action: data.action,
    revision: typeof data.revision === "number" ? data.revision : undefined,
    changedFields: stringArray(data.changedFields),
    clearedFields: stringArray(data.clearedFields),
  };
}

export function toolStatusesFromMessage(message: UIMessage): ToolStatusEvent[] {
  return message.parts
    .map((part) => toolStatusFromPart(part))
    .filter((event): event is ToolStatusEvent => event !== null);
}

export function artefactsFromMessage(message: UIMessage): ArtefactEvent[] {
  return message.parts
    .map((part) => artefactFromPart(part))
    .filter((event): event is ArtefactEvent => event !== null);
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}
