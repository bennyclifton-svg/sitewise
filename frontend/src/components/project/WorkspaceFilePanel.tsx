import { Inbox } from "lucide-react";
import { useEffect, useState } from "react";

import { MarkdownContent } from "@/components/project/MarkdownContent";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import { cn } from "@/lib/utils";
import type { EvidencePreview } from "@/lib/types/project";

type DocumentView = "markdown" | "html" | "yaml" | "raw";

const DOCUMENT_VIEWS: { id: DocumentView; label: string }[] = [
  { id: "markdown", label: "Markdown" },
  { id: "html", label: "HTML" },
  { id: "yaml", label: "YAML" },
  { id: "raw", label: "Raw" },
];

export function WorkspaceFilePanel({
  projectId,
  evidence,
}: {
  projectId: string;
  evidence: EvidencePreview | null;
}) {
  const [detail, setDetail] = useState<EvidencePreview | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [documentView, setDocumentView] = useState<DocumentView>("markdown");

  useEffect(() => {
    let cancelled = false;

    async function loadDetail() {
      setDetailError(null);
      if (!evidence) {
        setDetail(null);
        setLoadingDetail(false);
        return;
      }
      if (evidence.content) {
        setDetail(evidence);
        setLoadingDetail(false);
        return;
      }

      setLoadingDetail(true);
      try {
        const data = await api.getProjectEvidenceDocument(projectId, evidence.id);
        if (!cancelled) setDetail(data);
      } catch (error) {
        if (!cancelled) {
          setDetailError(
            error instanceof ApiError ? error.message : "Could not load document content.",
          );
        }
      } finally {
        if (!cancelled) setLoadingDetail(false);
      }
    }

    void loadDetail();
    return () => {
      cancelled = true;
    };
  }, [projectId, evidence]);

  if (!evidence) {
    return (
      <div className="flex min-h-full items-center justify-center p-6">
        <div className="rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">
          <Inbox className="mx-auto mb-3 size-8" aria-hidden />
          Select a file from the explorer.
        </div>
      </div>
    );
  }

  const displayEvidence = detail && detail.id === evidence.id ? detail : evidence;

  return (
    <section className="min-w-0 p-4 lg:p-6">
      <article className="mx-auto max-w-4xl space-y-4">
        <header className="rounded-md border bg-background p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <h1 className="text-xl font-semibold">{displayEvidence.title}</h1>
              <p className="mt-1 break-all text-sm text-muted-foreground">
                {displayEvidence.relative_path}
              </p>
            </div>
            <Badge variant="outline">{displayEvidence.document_class}</Badge>
          </div>
          <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
            <MetaItem label="Doc No" value={displayEvidence.document_number?.trim() || "-"} />
            <MetaItem label="Title" value={displayEvidence.title} />
            <MetaItem label="Revision" value={displayEvidence.revision?.trim() || "-"} />
            <MetaItem label="Category" value={displayEvidence.category?.trim() || "-"} />
            <MetaItem label="Filename" value={displayEvidence.filename} />
            <MetaItem label="Source type" value={displayEvidence.source_type ?? "Unknown"} />
          </dl>
        </header>
        <section className="rounded-md border bg-background">
          <header className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3">
            <h2 className="text-sm font-semibold">
              {displayEvidence.content ? "Document content" : "Extracted excerpt"}
            </h2>
            {displayEvidence.content ? (
              <div
                className="inline-flex rounded-md border bg-muted p-0.5"
                role="tablist"
                aria-label="Document content views"
              >
                {DOCUMENT_VIEWS.map((view) => (
                  <button
                    key={view.id}
                    type="button"
                    role="tab"
                    aria-selected={documentView === view.id}
                    className={cn(
                      "rounded-sm px-2.5 py-1 text-xs font-medium text-muted-foreground transition-colors",
                      documentView === view.id
                        ? "bg-background text-foreground shadow-xs"
                        : "hover:text-foreground",
                    )}
                    onClick={() => setDocumentView(view.id)}
                  >
                    {view.label}
                  </button>
                ))}
              </div>
            ) : null}
          </header>
          {detailError ? (
            <p className="p-4 text-sm text-destructive">{detailError}</p>
          ) : loadingDetail ? (
            <p className="p-4 text-sm text-muted-foreground" role="status">
              Loading document content...
            </p>
          ) : displayEvidence.content ? (
            <div className="p-4">
              <DocumentContentView evidence={displayEvidence} view={documentView} />
            </div>
          ) : (
            <p className="whitespace-pre-wrap p-4 text-sm leading-relaxed">
              {displayEvidence.excerpt}
            </p>
          )}
        </section>
      </article>
    </section>
  );
}

function DocumentContentView({
  evidence,
  view,
}: {
  evidence: EvidencePreview;
  view: DocumentView;
}) {
  const content = evidence.content ?? "";

  if (view === "markdown") {
    return (
      <div className="max-h-[65vh] overflow-auto">
        <MarkdownContent markdown={content} />
      </div>
    );
  }

  if (view === "html") {
    return <HtmlDocumentView html={documentHtml(evidence, content)} />;
  }

  if (view === "yaml") {
    return <YamlDocumentView yaml={documentYaml(evidence, content)} />;
  }

  return (
    <pre className="max-h-[65vh] overflow-auto whitespace-pre-wrap break-words font-mono text-xs leading-relaxed text-foreground">
      {content}
    </pre>
  );
}

function HtmlDocumentView({ html }: { html: string }) {
  return (
    <div
      className="document-html max-h-[65vh] overflow-auto text-sm text-foreground [&_h1]:mb-4 [&_h1]:text-2xl [&_h1]:font-semibold [&_h2]:mt-8 [&_h2]:border-b [&_h2]:pb-2 [&_h2]:text-lg [&_h2]:font-semibold [&_p]:my-3 [&_p]:leading-relaxed [&_table]:my-4 [&_table]:w-full [&_table]:min-w-[36rem] [&_table]:border-collapse [&_table]:text-left [&_tbody_tr:nth-child(even)]:bg-muted/20 [&_td]:border-b [&_td]:px-3 [&_td]:py-2 [&_td]:align-top [&_th]:border-b [&_th]:bg-muted/50 [&_th]:px-3 [&_th]:py-2 [&_th]:text-left [&_th]:font-medium"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

function YamlDocumentView({ yaml }: { yaml: string }) {
  const lines = yaml.split("\n");

  return (
    <pre className="max-h-[65vh] overflow-auto whitespace-pre-wrap break-words rounded-md bg-muted/30 p-3 font-mono text-xs leading-relaxed text-foreground">
      {lines.map((line, index) => (
        <span key={`${index}-${line}`}>
          <YamlLine line={line} />
          {index < lines.length - 1 ? "\n" : null}
        </span>
      ))}
    </pre>
  );
}

function YamlLine({ line }: { line: string }) {
  const match = line.match(/^(\s*(?:-\s*)?)([A-Za-z0-9_ -]+)(:)(.*)$/);
  if (!match) {
    return <span className="text-muted-foreground">{line}</span>;
  }

  return (
    <>
      {match[1]}
      <span className="text-sky-700 dark:text-sky-300">{match[2]}</span>
      <span className="text-muted-foreground">{match[3]}</span>
      <YamlValue value={match[4]} />
    </>
  );
}

function YamlValue({ value }: { value: string }) {
  const trimmed = value.trim();
  if (!trimmed) return <>{value}</>;

  const leading = value.slice(0, value.indexOf(trimmed));
  let valueClass = "text-foreground";
  if (trimmed === "null") {
    valueClass = "text-muted-foreground";
  } else if (trimmed === "|") {
    valueClass = "text-amber-700 dark:text-amber-300";
  } else if (/^".*"$/.test(trimmed)) {
    valueClass = "text-emerald-700 dark:text-emerald-300";
  } else if (/^-?\d+(?:\.\d+)?$/.test(trimmed)) {
    valueClass = "text-violet-700 dark:text-violet-300";
  }

  return (
    <>
      {leading}
      <span className={valueClass}>{trimmed}</span>
    </>
  );
}

function MetaItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-1 truncate font-medium" title={value}>
        {value}
      </dd>
    </div>
  );
}

function documentHtml(evidence: EvidencePreview, content: string): string {
  const body: string[] = [];
  const lines = content.split("\n");

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    if (isMarkdownTableStart(lines, index)) {
      const tableLines: string[] = [];
      while (index < lines.length && lines[index].trim().startsWith("|")) {
        tableLines.push(lines[index]);
        index += 1;
      }
      index -= 1;
      body.push(markdownTableHtml(tableLines));
      continue;
    }

    const renderedLine = (() => {
      if (!line.trim()) return "";
      const pageHeading = line.match(/^##\s+(.+)$/);
      if (pageHeading) return `  <h2>${escapeHtml(pageHeading[1])}</h2>`;
      const heading = line.match(/^#\s+(.+)$/);
      if (heading) return `  <h1>${escapeHtml(heading[1])}</h1>`;
      return `  <p>${escapeHtml(line)}</p>`;
    })();
    if (renderedLine) body.push(renderedLine);
  }

  return [
    "<article>",
    `  <header>`,
    `    <h1>${escapeHtml(evidence.title)}</h1>`,
    `    <p>${escapeHtml(evidence.relative_path)}</p>`,
    `  </header>`,
    body.join("\n"),
    "</article>",
  ].join("\n");
}

function isMarkdownTableStart(lines: string[], index: number): boolean {
  const line = lines[index]?.trim();
  const next = lines[index + 1]?.trim();
  return Boolean(
    line?.startsWith("|") &&
      next?.startsWith("|") &&
      /^(\|\s*:?-{3,}:?\s*)+\|?$/.test(next),
  );
}

function markdownTableHtml(lines: string[]): string {
  const rows = lines
    .filter((line, index) => index !== 1 && line.trim().startsWith("|"))
    .map((line) =>
      line
        .trim()
        .replace(/^\|/, "")
        .replace(/\|$/, "")
        .split("|")
        .map((cell) => cell.trim()),
    );

  if (rows.length === 0) return "";
  const [header, ...bodyRows] = rows;
  const head = header
    .map((cell) => `<th>${escapeHtml(cell)}</th>`)
    .join("");
  const body = bodyRows
    .map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join("")}</tr>`)
    .join("\n");
  return [
    "  <table>",
    `    <thead><tr>${head}</tr></thead>`,
    "    <tbody>",
    body,
    "    </tbody>",
    "  </table>",
  ].join("\n");
}

function documentYaml(evidence: EvidencePreview, content: string): string {
  const pages = contentPages(content);
  const lines = [
    "document:",
    `  title: ${yamlValue(evidence.title)}`,
    `  filename: ${yamlValue(evidence.filename)}`,
    `  relative_path: ${yamlValue(evidence.relative_path)}`,
    `  source_type: ${yamlValue(evidence.source_type)}`,
    `  document_class: ${yamlValue(evidence.document_class)}`,
    `  document_number: ${yamlValue(evidence.document_number)}`,
    `  revision: ${yamlValue(evidence.revision)}`,
    `  category: ${yamlValue(evidence.category)}`,
    "pages:",
  ];

  if (pages.length === 0) {
    lines.push("  []");
    return lines.join("\n");
  }

  for (const page of pages) {
    lines.push(`  - heading: ${yamlValue(page.heading)}`);
    lines.push("    content: |");
    lines.push(indentBlock(page.content || "", 6));
  }
  return lines.join("\n");
}

function contentPages(content: string): { heading: string; content: string }[] {
  const pages: { heading: string; content: string }[] = [];
  let current: { heading: string; lines: string[] } | null = null;

  for (const line of content.split("\n")) {
    const heading = line.match(/^##\s+(.+)$/);
    if (heading) {
      if (current) {
        pages.push({ heading: current.heading, content: current.lines.join("\n").trim() });
      }
      current = { heading: heading[1], lines: [] };
      continue;
    }
    if (current) current.lines.push(line);
  }

  if (current) {
    pages.push({ heading: current.heading, content: current.lines.join("\n").trim() });
  }
  if (pages.length > 0) return pages;
  return [{ heading: "Document", content }];
}

function yamlValue(value: string | null | undefined): string {
  if (value == null || value.trim() === "") return "null";
  return JSON.stringify(value);
}

function indentBlock(text: string, spaces: number): string {
  const prefix = " ".repeat(spaces);
  if (!text) return `${prefix}`;
  return text.split("\n").map((line) => `${prefix}${line}`).join("\n");
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
