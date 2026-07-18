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
import type { DraftArtifact } from "@/lib/types/project";

const EVIDENCE_STATUSES = [
  "User provided",
  "Grounded",
  "Partial",
  "Not evidenced",
  "Assumption",
  "Gap",
  "Conflict",
] as const;

const baseComponents: Components = {
  h1: ({ children }) => (
    <h1 className="mb-4 text-2xl font-semibold leading-tight">{children}</h1>
  ),
  h2: ({ children }) => (
    <h2 className="pmp-section-heading mt-8 border-b pb-2 text-lg font-semibold first:mt-0">
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="mt-5 text-base font-semibold">{children}</h3>
  ),
  h4: ({ children }) => (
    <h4 className="mt-4 text-sm font-semibold">{children}</h4>
  ),
  p: ({ children }) => <p className="my-3 leading-relaxed">{children}</p>,
  a: ({ children, href }) => (
    <a className="font-medium text-primary underline underline-offset-2" href={href}>
      {children}
    </a>
  ),
  blockquote: ({ children }) => (
    <blockquote className="my-4 border-l-2 pl-4 text-muted-foreground">{children}</blockquote>
  ),
  hr: () => <hr className="my-6 border-border" />,
  ul: ({ children }) => (
    <ul className="my-3 list-disc space-y-1.5 pl-5 leading-relaxed">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="my-3 list-decimal space-y-1.5 pl-5 leading-relaxed">{children}</ol>
  ),
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
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
  tr: ({ children }) => <tr className="even:bg-muted/20">{children}</tr>,
};

function markdownComponents(
  version?: number,
  options?: {
    projectId?: string;
    readOnly?: boolean;
    onDraftUpdated?: (draft: DraftArtifact) => void;
    onEditSection?: (heading: string) => void;
  },
): Components {
  let isFirstHeading = true;

  return {
    ...baseComponents,
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
        const decision = parseEmbeddedDecision(raw);
        if (decision && options?.projectId) {
          return (
            <DecisionControl
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
    h2: ({ children }) => {
      const heading = flattenText(children);
      return (
        <div className="group mt-8 flex items-start justify-between gap-3 first:mt-0">
          <h2
            id={sectionAnchor(heading)}
            className="pmp-section-heading min-w-0 flex-1 border-b pb-2 text-lg font-semibold"
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
  const match = EVIDENCE_STATUSES.find(
    (status) => text === status || text.startsWith(`${status} `) || text.includes(` / ${status}`),
  );
  if (!match) return children;
  return (
    <span className="inline-flex flex-wrap items-center gap-1">
      <Badge variant={evidenceBadgeVariant(match)} className="evidence-status-chip">
        {match}
      </Badge>
      {text !== match ? <span>{text.replace(match, "").trim()}</span> : null}
    </span>
  );
}

function evidenceBadgeVariant(status: (typeof EVIDENCE_STATUSES)[number]) {
  switch (status) {
    case "Grounded":
    case "User provided":
      return "default" as const;
    case "Partial":
    case "Assumption":
      return "secondary" as const;
    case "Conflict":
      return "destructive" as const;
    default:
      return "outline" as const;
  }
}

export function MarkdownContent({
  markdown,
  version,
  projectId,
  projectTitle,
  readOnly = false,
  onDraftUpdated,
  onEditSection,
}: {
  markdown: string;
  version?: number;
  projectId?: string;
  projectTitle?: string;
  readOnly?: boolean;
  onDraftUpdated?: (draft: DraftArtifact) => void;
  onEditSection?: (heading: string) => void;
}) {
  const normalized = normalizeDraftMarkdown(markdown);
  const sections = useMemo(() => splitMarkdownSections(normalized), [normalized]);

  return (
    <div
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
              readOnly,
              onDraftUpdated,
              onEditSection,
            })}
          >
            {normalized}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  );
}

// Pure formatting contracts are exported for focused rendering tests.
// eslint-disable-next-line react-refresh/only-export-components
export { EVIDENCE_STATUSES, evidenceBadgeVariant };
