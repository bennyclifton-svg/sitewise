import type { Components } from "react-markdown";
import { useMemo, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import {
  DecisionControl,
  parseEmbeddedDecision,
} from "@/components/project/DecisionControl";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { splitMarkdownSections } from "@/lib/markdown-sections";
import type { MarkdownRange } from "@/lib/markdown-selection";
import type {
  DraftArtifact,
  ProjectDecision,
} from "@/lib/types/project";

const EVIDENCE_STATUSES = [
  "User provided",
  "Grounded",
  "Partial",
  "Not evidenced",
  "Assumption",
  "Gap",
  "Conflict",
  "Profile",
  "Confirm",
] as const;

/**
 * Offsets into the source markdown for one block element.
 *
 * `react-markdown` hard-enables `passNode`, and `mdast-util-to-hast` copies the
 * mdast `position` onto every hast node, so every custom component already
 * receives these for free — no rehype plugin and no extra dependency.
 *
 * Selection anchoring slices quoted text out of the *source* using these
 * offsets, and never reads rendered text back (design decision D1): the
 * evidence-cell and decision-fence renderers replace source text with
 * synthesized elements, so rendered text does not map back to markdown.
 */
type MdPositionAttributes = {
  "data-md-start": number;
  "data-md-end": number;
  "data-md-changed"?: string;
};

function mdPosition(
  node: unknown,
  changedRanges: readonly MarkdownRange[],
): MdPositionAttributes | undefined {
  const position = (
    node as {
      position?: { start?: { offset?: number }; end?: { offset?: number } };
    } | null
  )?.position;
  const start = position?.start?.offset;
  const end = position?.end?.offset;
  if (typeof start !== "number" || typeof end !== "number") return undefined;
  const changed = changedRanges.some(
    (range) => range.start < end && range.end > start,
  );
  return changed
    ? { "data-md-start": start, "data-md-end": end, "data-md-changed": "" }
    : { "data-md-start": start, "data-md-end": end };
}

function baseComponents(changedRanges: readonly MarkdownRange[]): Components {
  const position = (node: unknown) => mdPosition(node, changedRanges);
  return {
    h1: ({ children }) => (
      <h1 className="mb-4 text-2xl font-semibold leading-tight">{children}</h1>
    ),
    h2: ({ children, node }) => (
      <h2
        className="pmp-section-heading mt-8 border-b pb-2 text-lg font-semibold first:mt-0"
        {...position(node)}
      >
        {children}
      </h2>
    ),
    h3: ({ children, node }) => (
      <h3 className="mt-5 text-base font-semibold" {...position(node)}>
        {children}
      </h3>
    ),
    h4: ({ children, node }) => (
      <h4 className="mt-4 text-sm font-semibold" {...position(node)}>
        {children}
      </h4>
    ),
    p: ({ children, node }) => (
      <p className="my-3 leading-relaxed" {...position(node)}>
        {children}
      </p>
    ),
    a: ({ children, href }) => (
      <a className="font-medium text-primary underline underline-offset-2" href={href}>
        {children}
      </a>
    ),
    blockquote: ({ children, node }) => (
      <blockquote
        className="my-4 border-l-2 pl-4 text-muted-foreground"
        {...position(node)}
      >
        {children}
      </blockquote>
    ),
    hr: () => <hr className="my-6 border-border" />,
    ul: ({ children }) => (
      <ul className="my-3 list-disc space-y-1.5 pl-5 leading-relaxed">{children}</ul>
    ),
    ol: ({ children }) => (
      <ol className="my-3 list-decimal space-y-1.5 pl-5 leading-relaxed">{children}</ol>
    ),
    li: ({ children, node }) => (
      <li className="leading-relaxed" {...position(node)}>
        {children}
      </li>
    ),
    strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
    code: ({ children, className }) => {
      const language = className?.replace("language-", "") ?? "";
      if (language === "pmp-decision") {
        return (
          <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">{children}</code>
        );
      }
      return (
        <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">{children}</code>
      );
    },
    table: ({ children }) => (
      <div className="my-4 overflow-x-auto rounded-md border pmp-table-wrap">
        <table className="w-full min-w-[36rem] border-collapse text-left text-sm">
          {children}
        </table>
      </div>
    ),
    thead: ({ children }) => <thead className="bg-muted/50">{children}</thead>,
    th: ({ children }) => (
      <th className="border-b px-3 py-2 align-top font-medium text-foreground">{children}</th>
    ),
    td: ({ children }) => (
      <td className="border-b px-3 py-2 align-top text-foreground">
        {renderEvidenceCell(children)}
      </td>
    ),
    // `tr` is the addressable unit for a table, never `td`/`th` — renderEvidenceCell
    // replaces cell content with badges, so a cell's rendered text is not its source.
    tr: ({ children, node }) => (
      <tr className="sw-table-row even:bg-muted/20" {...position(node)}>
        {children}
      </tr>
    ),
  };
}

function markdownComponents(
  version?: number,
  options?: {
    projectId?: string;
    decisionsById?: ReadonlyMap<string, ProjectDecision>;
    readOnly?: boolean;
    changedRanges?: readonly MarkdownRange[];
    onDraftUpdated?: (draft: DraftArtifact) => void;
    onEditSection?: (heading: string) => void;
  },
): Components {
  let isFirstHeading = true;
  const changedRanges = options?.changedRanges ?? [];
  const position = (node: unknown) => mdPosition(node, changedRanges);

  return {
    ...baseComponents(changedRanges),
    pre: ({ children }) => {
      const child = Array.isArray(children) ? children[0] : children;
      if (
        typeof child === "object" &&
        child !== null &&
        "props" in child &&
        typeof child.props === "object" &&
        child.props !== null &&
        "className" in child.props &&
        typeof child.props.className === "string" &&
        child.props.className.includes("language-pmp-decision")
      ) {
        const raw = String("children" in child.props ? child.props.children : "").trim();
        const embedded = parseEmbeddedDecision(raw);
        const decision = embedded
          ? hydrateEmbeddedDecision(
              embedded,
              options?.decisionsById?.get(embedded.id),
            )
          : null;
        if (decision && options?.projectId) {
          return (
            <DecisionControl
              key={`${decision.id}:${decision.revision ?? 0}:${decision.set_revision ?? 0}`}
              projectId={options.projectId}
              decision={decision}
              readOnly={options.readOnly}
              onDraftUpdated={options.onDraftUpdated}
            />
          );
        }
        return (
          <pre className="my-4 overflow-x-auto rounded-md border bg-muted/30 p-3 text-xs">
            {children}
          </pre>
        );
      }
      return (
        <pre className="my-4 overflow-x-auto rounded-md border bg-muted/30 p-3 text-xs">
          {children}
        </pre>
      );
    },
    h1: ({ children }) => {
      if (isFirstHeading && version != null) {
        isFirstHeading = false;
        return (
          <div className="mb-4 flex items-start justify-between gap-3">
            <h1 className="min-w-0 text-2xl font-semibold leading-tight">{children}</h1>
            <Badge variant="secondary" className="shrink-0 print:hidden">
              v{version}
            </Badge>
          </div>
        );
      }
      isFirstHeading = false;
      return (
        <h1 className="mb-4 text-2xl font-semibold leading-tight">{children}</h1>
      );
    },
    h2: ({ children, node }) => {
      const heading = flattenText(children);
      return (
        <div className="group mt-8 flex items-start justify-between gap-3 first:mt-0">
          <h2
            id={sectionAnchor(heading)}
            className="pmp-section-heading min-w-0 flex-1 border-b pb-2 text-lg font-semibold"
            {...position(node)}
          >
            {children}
          </h2>
          {options?.onEditSection ? (
            <Button
              type="button"
              size="sm"
              variant="ghost"
              className="shrink-0 opacity-0 transition-opacity group-hover:opacity-100 print:hidden"
              onClick={() => options.onEditSection?.(heading)}
            >
              Edit section
            </Button>
          ) : null}
        </div>
      );
    },
  };
}

/**
 * Strip the leading `- |` generation artefact from table rows.
 *
 * Must stay byte-identical to `normalize_draft_markdown` in
 * `backend/app/sitewise/markdown_sections.py` — the two define one offset space
 * that selection anchors resolve against (design decision D3). The shared
 * vectors in `backend/tests/sitewise/fixtures/normalize_vectors.json` are
 * asserted against both implementations.
 */
function normalizeDraftMarkdown(markdown: string): string {
  return markdown
    .split("\n")
    .map((line) => {
      const trimmed = line.trimStart();
      if (trimmed.startsWith("- |")) {
        return trimmed.slice(2).trimStart();
      }
      return line;
    })
    .join("\n");
}

function flattenText(children: ReactNode): string {
  if (typeof children === "string") return children;
  if (Array.isArray(children)) return children.map(flattenText).join("");
  if (typeof children === "object" && children !== null && "props" in children) {
    const props = children.props as { children?: ReactNode };
    return flattenText(props.children);
  }
  return "";
}

function sectionAnchor(heading: string): string {
  return heading.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

function renderEvidenceCell(children: ReactNode): ReactNode {
  const text = flattenText(children).trim();
  if (/^\[\d+\]$/.test(text)) {
    return (
      <Badge
        variant="outline"
        className="evidence-status-chip border-transparent bg-[var(--decision-evidenced-bg)] text-[var(--decision-evidenced-text)]"
      >
        <span data-status-dot="info" aria-hidden />
        {text}
      </Badge>
    );
  }
  const match = EVIDENCE_STATUSES.find(
    (status) => text === status || text.startsWith(`${status} `) || text.includes(` / ${status}`),
  );
  if (!match) return children;
  return (
    <span className="inline-flex flex-wrap items-center gap-1">
      <Badge
        variant={evidenceBadgeVariant(match)}
        className={evidenceBadgeClassName(match)}
      >
        <span data-status-dot={evidenceStatusDot(match)} aria-hidden />
        {match}
      </Badge>
      {text !== match ? <span>{text.replace(match, "").trim()}</span> : null}
    </span>
  );
}

function evidenceBadgeVariant(_status: (typeof EVIDENCE_STATUSES)[number]) {
  return "outline" as const;
}

function evidenceStatusDot(
  status: (typeof EVIDENCE_STATUSES)[number],
): "positive" | "caution" | "critical" | "info" | "quiet" {
  switch (status) {
    case "Grounded":
    case "User provided":
      return "positive";
    case "Conflict":
      return "critical";
    case "Confirm":
    case "Partial":
    case "Assumption":
    case "Gap":
    case "Not evidenced":
      return "caution";
    case "Profile":
      return "info";
    default:
      return "quiet";
  }
}

function evidenceBadgeClassName(status: (typeof EVIDENCE_STATUSES)[number]): string {
  switch (status) {
    case "Grounded":
    case "User provided":
      return "evidence-status-chip border-transparent bg-[var(--decision-evidenced-bg)] text-[var(--decision-evidenced-text)]";
    case "Partial":
    case "Assumption":
    case "Profile":
      return "evidence-status-chip border-transparent bg-[var(--decision-assumed-bg)] text-[var(--decision-assumed-text)]";
    case "Confirm":
    case "Gap":
    case "Not evidenced":
      return "evidence-status-chip border-[color-mix(in_oklch,var(--sw-caution)_40%,transparent)] bg-[color-mix(in_oklch,var(--sw-caution)_14%,transparent)] text-[var(--sw-caution)]";
    case "Conflict":
      return "evidence-status-chip border-[color-mix(in_oklch,var(--sw-critical)_40%,transparent)] bg-[color-mix(in_oklch,var(--sw-critical)_14%,transparent)] text-[var(--sw-critical)]";
    default:
      return "evidence-status-chip";
  }
}

export function MarkdownContent({
  markdown,
  version,
  projectId,
  decisions,
  projectTitle,
  readOnly = false,
  changedRanges,
  showChanges = false,
  containerRef,
  onDraftUpdated,
  onEditSection,
}: {
  /**
   * Already normalized (see `normalizeDraftMarkdown`). Callers own the
   * transform so that the offsets stamped here and the offsets a caller slices
   * with are the same space — design decision D3.
   */
  markdown: string;
  version?: number;
  projectId?: string;
  decisions?: ProjectDecision[];
  projectTitle?: string;
  readOnly?: boolean;
  changedRanges?: readonly MarkdownRange[];
  showChanges?: boolean;
  containerRef?: React.Ref<HTMLDivElement>;
  onDraftUpdated?: (draft: DraftArtifact) => void;
  onEditSection?: (heading: string) => void;
}) {
  const sections = useMemo(() => splitMarkdownSections(markdown), [markdown]);
  const activeRanges = useMemo(
    () => (showChanges ? (changedRanges ?? []) : []),
    [showChanges, changedRanges],
  );
  const decisionsById = useMemo(
    () =>
      decisions
        ? new Map(decisions.map((decision) => [decision.decision_id, decision]))
        : undefined,
    [decisions],
  );

  return (
    <div
      ref={containerRef}
      className="draft-markdown text-sm text-foreground"
      data-project-title={projectTitle}
      data-draft-version={version}
    >
      <div className="flex gap-6">
        {sections.length > 1 ? (
          <nav
            aria-label="PMP sections"
            className="sticky top-4 hidden h-fit min-w-44 shrink-0 lg:block print:hidden"
          >
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Sections
            </p>
            <ul className="space-y-1 text-xs">
              {sections.map((section) => (
                <li key={section.heading}>
                  <a
                    className="block rounded px-2 py-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                    href={`#${sectionAnchor(section.heading)}`}
                  >
                    {section.heading}
                  </a>
                </li>
              ))}
            </ul>
          </nav>
        ) : null}
        <div className="min-w-0 flex-1">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={markdownComponents(version, {
              projectId,
              decisionsById,
              readOnly,
              changedRanges: activeRanges,
              onDraftUpdated,
              onEditSection,
            })}
          >
            {markdown}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  );
}

function hydrateEmbeddedDecision(
  embedded: ReturnType<typeof parseEmbeddedDecision> & {},
  canonical: ProjectDecision | undefined,
) {
  if (!canonical) return embedded;
  return {
    ...embedded,
    section: canonical.section || embedded.section,
    label: canonical.label || embedded.label,
    options: canonical.options.length ? canonical.options : embedded.options,
    selected: canonical.selected,
    source: canonical.source,
    revision: canonical.revision,
    set_revision: canonical.set_revision,
    evidence_conflict: canonical.evidence_conflict,
    agent_suggestion: canonical.agent_suggestion ?? undefined,
  };
}

// Pure formatting contracts are exported for focused rendering tests.
// `normalizeDraftMarkdown` is also the offset space every anchor is resolved
// against, so callers that need anchors must apply it before slicing.
// eslint-disable-next-line react-refresh/only-export-components
export { EVIDENCE_STATUSES, evidenceBadgeVariant, normalizeDraftMarkdown };
