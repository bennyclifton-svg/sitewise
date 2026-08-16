import type { ToolStatusEvent } from "@/lib/chat-events";
import { isWebSourceType } from "@/lib/citations";
import type { Citation } from "@/lib/types/citation";

const PROJECT_DOCUMENT_TOOLS = new Set([
  "find_document_text",
  "search_documents",
  "get_document",
]);

const PLATFORM_KNOWLEDGE_TOOLS = new Set([
  "list_platform_knowledge",
  "read_platform_knowledge",
]);

const WEB_RESEARCH_TOOLS = new Set([
  "search_web",
  "read_web_source",
  "attach_official_instrument",
]);

export type AnswerTraceTone =
  | "context"
  | "documents"
  | "knowledge"
  | "web"
  | "tools"
  | "model";

export type AnswerTraceItem = {
  key: string;
  label: string;
  tone: AnswerTraceTone;
  title: string;
};

type AnswerTraceInput = {
  agentMode?: boolean;
  messageData?: Record<string, unknown> | null;
  toolEvents?: ToolStatusEvent[];
  citations?: Citation[];
};

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null
    ? (value as Record<string, unknown>)
    : null;
}

function stringList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string" && item.length > 0);
}

function unique(values: string[]): string[] {
  return [...new Set(values)];
}

function sourceTrace(messageData: Record<string, unknown> | null | undefined) {
  const root = asRecord(messageData);
  const agent = asRecord(root?.agent);
  return asRecord(agent?.sourceTrace) ?? asRecord(root?.sourceTrace);
}

function traceSection(trace: Record<string, unknown> | null, key: string) {
  return asRecord(trace?.[key]);
}

function traceTools(trace: Record<string, unknown> | null): string[] {
  const tools = trace?.tools;
  if (!Array.isArray(tools)) return [];
  return tools
    .map((tool) => asRecord(tool)?.name)
    .filter((name): name is string => typeof name === "string" && name.length > 0);
}

function hasAgentMetadata(messageData: Record<string, unknown> | null | undefined): boolean {
  return asRecord(asRecord(messageData)?.agent) !== null;
}

export function answerTraceItems({
  agentMode = false,
  messageData,
  toolEvents = [],
  citations = [],
}: AnswerTraceInput): AnswerTraceItem[] {
  const trace = sourceTrace(messageData);
  const context = traceSection(trace, "context");
  const documents = traceSection(trace, "documents");
  const knowledge = traceSection(trace, "knowledge");
  const web = traceSection(trace, "web");
  const model = traceSection(trace, "model");

  const liveToolNames = unique(
    toolEvents
      .filter((event) => event.state === "done")
      .map((event) => event.tool),
  );
  const persistedToolNames = traceTools(trace);
  const allToolNames = unique([...persistedToolNames, ...liveToolNames]);

  const documentTools = unique([
    ...stringList(documents?.tools),
    ...allToolNames.filter((tool) => PROJECT_DOCUMENT_TOOLS.has(tool)),
  ]);
  const knowledgeTools = unique([
    ...stringList(knowledge?.tools),
    ...allToolNames.filter((tool) => PLATFORM_KNOWLEDGE_TOOLS.has(tool)),
  ]);
  const webTools = unique([
    ...stringList(web?.tools),
    ...allToolNames.filter((tool) => WEB_RESEARCH_TOOLS.has(tool)),
  ]);
  const knowledgeRefs = stringList(knowledge?.references);
  const liveKnowledgeRefs = toolEvents
    .map((event) => event.knowledgePath)
    .filter((path): path is string => typeof path === "string" && path.length > 0);
  const persistedWebSources = Array.isArray(web?.sources)
    ? web.sources.map(asRecord).filter((source) => source !== null)
    : [];
  const webSourceTitles = unique([
    ...persistedWebSources
      .map((source) => source.title)
      .filter((title): title is string => typeof title === "string" && title.length > 0),
    ...toolEvents
      .map((event) => event.webSource?.title)
      .filter((title): title is string => typeof title === "string" && title.length > 0),
    ...citations
      .filter((citation) => isWebSourceType(citation.sourceType))
      .map((citation) => citation.title),
  ]);

  const hasProjectEvidence = citations.some(
    (citation) => citation.sourceType === "project_evidence",
  );
  const hasSeedCitation = citations.some(
    (citation) =>
      citation.sourceType === "doctrine" || citation.sourceType === "reference",
  );
  const showWebSource = webSourceTitles.length > 0;
  const showWeb = showWebSource || webTools.length > 0;

  const showContext =
    context?.used === true || agentMode || hasAgentMetadata(messageData);
  const showDocuments = documents?.used === true || documentTools.length > 0 || hasProjectEvidence;
  const showKnowledge =
    knowledge?.used === true ||
    knowledgeTools.length > 0 ||
    knowledgeRefs.length > 0 ||
    liveKnowledgeRefs.length > 0 ||
    hasSeedCitation;
  const showModel =
    model?.used === true ||
    agentMode ||
    hasAgentMetadata(messageData) ||
    showDocuments ||
    showKnowledge ||
    showWeb;

  const items: AnswerTraceItem[] = [];
  if (showContext) {
    items.push({
      key: "context",
      label: "Project context",
      tone: "context",
      title: "Saved project profile and recent chat context were included.",
    });
  }
  if (showDocuments) {
    const tools = documentTools.length > 0 ? ` Tools: ${documentTools.join(", ")}.` : "";
    items.push({
      key: "documents",
      label: "Project documents",
      tone: "documents",
      title: `Project document evidence influenced this answer.${tools}`,
    });
  }
  if (showKnowledge) {
    const references = unique([...knowledgeRefs, ...liveKnowledgeRefs]);
    const sourceText =
      references.length > 0 ? ` Sources: ${references.join(", ")}.` : "";
    items.push({
      key: "knowledge",
      label: "SiteWise knowledge",
      tone: "knowledge",
      title: `SiteWise platform knowledge influenced this answer.${sourceText}`,
    });
  }
  if (showWeb) {
    items.push({
      key: "web",
      label: showWebSource
        ? webSourceTitles.length === 1
          ? "Web source"
          : `Web sources · ${webSourceTitles.length}`
        : "Internet search",
      tone: "web",
      title: showWebSource
        ? `Official web material influenced this answer. Sources: ${webSourceTitles.join(", ")}.`
        : "An official-source internet search informed this answer. Search results are discovery candidates, not source evidence.",
    });
  }
  if (allToolNames.length > 0) {
    items.push({
      key: "tools",
      label: allToolNames.length === 1 ? "1 tool used" : `${allToolNames.length} tools used`,
      tone: "tools",
      title: `Tools used: ${allToolNames.join(", ")}`,
    });
  }
  if (showModel) {
    items.push({
      key: "model",
      label: "LLM reasoning",
      tone: "model",
      title: "The model composed and reasoned over the available context.",
    });
  }

  return items;
}
