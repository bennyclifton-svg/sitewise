import type { UIMessage } from "ai";

type MessagePart = UIMessage["parts"][number];

type RecordLike = Record<string, unknown>;

export type ToolStatusState = "running" | "done" | "error";

export type WebSourceTrace = {
  url: string;
  title: string;
  publisher?: string;
  jurisdiction?: string;
  authorityClass?: string;
  sourceType?: string;
  versionStatus?: string;
  effectiveDate?: string;
  section?: string;
  excerpt?: string;
  contentHash?: string;
  retrievedAt?: string;
};

export type ToolStatusEvent = {
  kind: "tool";
  tool: string;
  state: ToolStatusState;
  message: string;
  stage?: string;
  knowledgePath?: string;
  sectionIds?: string[];
  documents?: string[];
  query?: string;
  percent?: number;
  doneUnits?: number;
  totalUnits?: number;
  webSource?: WebSourceTrace;
};

export type ArtefactEvent = {
  kind: "artefact";
  title: string;
  workflowType?: string;
  draftId?: string;
  comparisonId?: string;
  projectId?: string;
  version?: number;
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
  workflowType?: string;
};

export type DocumentSelectionEvent = {
  kind: "document_selection";
  projectId: string;
  action: "replace" | "clear";
  documentIds: string[];
  requestedAction?: "replace" | "add" | "remove" | "clear";
};

export type WorkflowRunRef = {
  kind: "workflow_run";
  projectId: string;
  runId: string;
  workflowType?: string;
  action?: string;
};

function isRecord(value: unknown): value is RecordLike {
  return typeof value === "object" && value !== null;
}

function clerkStatusData(part: MessagePart): RecordLike | null {
  if (part.type !== "data-clerk-status") return null;
  const data = (part as { data?: unknown }).data;
  return isRecord(data) ? data : null;
}

function optionalString(record: RecordLike, key: string): string | undefined {
  return typeof record[key] === "string" ? record[key] : undefined;
}

function webSourceFromData(value: unknown): WebSourceTrace | undefined {
  if (!isRecord(value)) return undefined;
  const url = optionalString(value, "url");
  const title = optionalString(value, "title");
  if (!url || !title) return undefined;
  return {
    url,
    title,
    publisher: optionalString(value, "publisher"),
    jurisdiction: optionalString(value, "jurisdiction"),
    authorityClass: optionalString(value, "authority_class"),
    sourceType: optionalString(value, "source_type"),
    versionStatus: optionalString(value, "version_status"),
    effectiveDate: optionalString(value, "effective_date"),
    section: optionalString(value, "section"),
    excerpt: optionalString(value, "excerpt"),
    contentHash: optionalString(value, "content_hash"),
    retrievedAt: optionalString(value, "retrieved_at"),
  };
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
    documents: Array.isArray(data.documents)
      ? data.documents.filter((item): item is string => typeof item === "string")
      : undefined,
    query: typeof data.query === "string" ? data.query : undefined,
    percent: typeof data.percent === "number" ? data.percent : undefined,
    doneUnits: typeof data.doneUnits === "number" ? data.doneUnits : undefined,
    totalUnits:
      typeof data.totalUnits === "number" ? data.totalUnits : undefined,
    webSource: webSourceFromData(data.web_source),
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
    version: typeof data.version === "number" ? data.version : undefined,
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
    workflowType:
      typeof data.workflowType === "string" ? data.workflowType : undefined,
  };
}

export function documentSelectionFromPart(
  part: MessagePart,
): DocumentSelectionEvent | null {
  const data = clerkStatusData(part);
  if (!data || data.kind !== "document_selection") return null;
  if (
    typeof data.projectId !== "string" ||
    (data.action !== "replace" && data.action !== "clear") ||
    !Array.isArray(data.documentIds) ||
    !data.documentIds.every((item) => typeof item === "string")
  ) {
    return null;
  }
  const requestedAction =
    data.requestedAction === "replace" ||
    data.requestedAction === "add" ||
    data.requestedAction === "remove" ||
    data.requestedAction === "clear"
      ? data.requestedAction
      : undefined;
  return {
    kind: "document_selection",
    projectId: data.projectId,
    action: data.action,
    documentIds: data.documentIds,
    requestedAction,
  };
}

export function applyDocumentSelectionEvent(
  current: Set<string>,
  event: DocumentSelectionEvent,
  availableDocumentIds: Iterable<string>,
): Set<string> {
  if (event.action === "clear") {
    return current.size ? new Set<string>() : current;
  }
  const available = new Set(availableDocumentIds);
  const selected = new Set(
    event.documentIds.filter((documentId) => available.has(documentId)),
  );
  return selected.size === current.size &&
    [...selected].every((documentId) => current.has(documentId))
    ? current
    : selected;
}

export function workflowRunFromPart(part: MessagePart): WorkflowRunRef | null {
  const data = clerkStatusData(part);
  if (!data) return null;

  if (data.kind === "resource" && data.resourceType === "workflow_run") {
    if (
      typeof data.projectId !== "string" ||
      typeof data.resourceId !== "string"
    ) {
      return null;
    }
    return {
      kind: "workflow_run",
      projectId: data.projectId,
      runId: data.resourceId,
      workflowType:
        typeof data.workflowType === "string" ? data.workflowType : undefined,
      action: typeof data.action === "string" ? data.action : undefined,
    };
  }

  if (data.kind === "run") {
    const runId =
      typeof data.runId === "string"
        ? data.runId
        : typeof data.resourceId === "string"
          ? data.resourceId
          : null;
    const projectId =
      typeof data.projectId === "string" ? data.projectId : null;
    if (!runId || !projectId) return null;
    return {
      kind: "workflow_run",
      projectId,
      runId,
      workflowType:
        typeof data.workflowType === "string" ? data.workflowType : undefined,
      action:
        typeof data.action === "string"
          ? data.action
          : typeof data.status === "string"
            ? data.status
            : undefined,
    };
  }

  return null;
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

export function workflowRunsFromMessage(message: UIMessage): WorkflowRunRef[] {
  const seen = new Set<string>();
  const runs: WorkflowRunRef[] = [];
  for (const part of message.parts) {
    const run = workflowRunFromPart(part);
    if (!run || seen.has(run.runId)) continue;
    seen.add(run.runId);
    runs.push(run);
  }
  return runs;
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}
