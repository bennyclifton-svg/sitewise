import type { UIMessage } from "ai";

type MessagePart = UIMessage["parts"][number];

type RecordLike = Record<string, unknown>;

export type ToolStatusState = "running" | "done" | "error";

export type ToolStatusEvent = {
  kind: "tool";
  tool: string;
  state: ToolStatusState;
  message: string;
};

export type ArtefactEvent = {
  kind: "artefact";
  title: string;
  workflowType?: string;
  draftId?: string;
  comparisonId?: string;
  projectId?: string;
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
