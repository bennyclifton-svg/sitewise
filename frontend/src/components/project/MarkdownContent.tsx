import type { Components } from "react-markdown";
import {
  Children,
  cloneElement,
  isValidElement,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { ChevronRight, PencilLine } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import {
  DecisionControl,
  DecisionSchedule,
  groupConsecutiveDecisionFences,
  parseEmbeddedDecision,
  type EmbeddedDecision,
} from "@/components/project/DecisionControl";
import { InlineMarkdownEditor } from "@/components/project/InlineMarkdownEditor";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { splitTraceQa } from "@/lib/artifact-markdown";
import { sourceRangeForRenderedBlock } from "@/lib/inline-markdown";
import {
  splitMarkdownSections,
  type MarkdownSectionSlice,
} from "@/lib/markdown-sections";
import type { MarkdownRange } from "@/lib/markdown-selection";
import type {
  DraftArtifact,
  ProjectDecision,
} from "@/lib/types/project";

const EVIDENCE_STATUSES = [
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
 * Paragraph actions slice quoted text out of the *source* using these offsets
 * and never read rendered text back (design decision D1): evidence-cell and
 * decision-fence renderers replace source text with synthesized elements, so
 * rendered text does not map back to markdown.
 */
type MdPositionAttributes = {
  "data-md-start": number;
  "data-md-end": number;
  "data-md-changed"?: string;
};

type InlineEditOptions = {
  sourceMarkdown: string;
  renderedMarkdown: string;
  sourceSections: MarkdownSectionSlice[];
  activeParagraph?: ParagraphTarget | null;
  editingRange?: MarkdownRange | null;
  isSavingEdit?: boolean;
  editError?: string | null;
  onActivateParagraph?: (target: ParagraphTarget) => void;
  onEditSelection?: (range: MarkdownRange) => void;
  onEditWithAi?: (range: MarkdownRange, rect: DOMRect) => void;
  onCancelSelectionEdit?: () => void;
  onSaveSelectionEdit?: (range: MarkdownRange, markdown: string) => Promise<void>;
  informationRegisterOpen?: boolean;
  onToggleInformationRegister?: () => void;
};

type ParagraphTarget = {
  range: MarkdownRange;
  sectionStart: number;
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

function baseComponents(
  changedRanges: readonly MarkdownRange[],
  projectTitle?: string,
  editOptions?: InlineEditOptions,
): Components {
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
    h3: ({ children, node }) =>
      flattenText(children).trim().toLowerCase() === "critical current position" ? null : (
        <h3 className="mt-5 text-base font-semibold" {...position(node)}>
          {children}
        </h3>
      ),
    h4: ({ children, node }) => (
      <h4 className="mt-4 text-sm font-semibold" {...position(node)}>
        {children}
      </h4>
    ),
    p: ({ children, node }) => {
      const text = flattenText(children);
      if (isPmpGovernanceDisclaimer(text)) return null;
      const ownerBrief = stripOwnerBriefLeadIn(text);
      const visibleText = stripEvidenceOnFileLabel(stripUserProvidedLabel(ownerBrief));
      if (visibleText !== text && !visibleText) return null;

      const attributes = position(node);
      const renderedRange = attributes
        ? {
            start: attributes["data-md-start"],
            end: attributes["data-md-end"],
          }
        : null;
      const sourceRange =
        renderedRange && editOptions
          ? sourceRangeForRenderedBlock(
              editOptions.sourceMarkdown,
              editOptions.renderedMarkdown,
              renderedRange,
            )
          : null;
      const isEditing = rangesEqual(editOptions?.editingRange, sourceRange);
      const section = sourceRange
        ? editOptions?.sourceSections.find(
            (item) => item.start <= sourceRange.start && sourceRange.start < item.end,
          )
        : null;
      const paragraphTarget =
        sourceRange && section
          ? { range: sourceRange, sectionStart: section.start }
          : null;
      const canTargetParagraph =
        visibleText === text &&
        paragraphTarget !== null &&
        Boolean(editOptions?.onEditSelection || editOptions?.onEditWithAi) &&
        (!editOptions?.editingRange || isEditing);

      if (
        isEditing &&
        sourceRange &&
        editOptions?.onCancelSelectionEdit &&
        editOptions.onSaveSelectionEdit
      ) {
        return (
          <InlineMarkdownEditor
            sectionStart={section?.start ?? sourceRange.start}
            sourceStart={sourceRange.start}
            sourceEnd={sourceRange.end}
            isChanged={attributes?.["data-md-changed"] !== undefined}
            isSaving={Boolean(editOptions.isSavingEdit)}
            error={editOptions.editError}
            onCancel={editOptions.onCancelSelectionEdit}
            onSave={(markdown) => editOptions.onSaveSelectionEdit?.(sourceRange, markdown) ?? Promise.resolve()}
          >
            {children}
          </InlineMarkdownEditor>
        );
      }

      if (canTargetParagraph && paragraphTarget && sourceRange) {
        return (
          <p
            className="my-3 leading-relaxed"
            {...attributes}
            onMouseEnter={() => editOptions?.onActivateParagraph?.(paragraphTarget)}
            onClick={() => editOptions?.onActivateParagraph?.(paragraphTarget)}
            onDoubleClick={(event) => {
              if (!editOptions?.onEditSelection) return;
              event.preventDefault();
              editOptions.onEditSelection(sourceRange);
            }}
          >
            {children}
          </p>
        );
      }

      return (
        <p className="my-3 leading-relaxed" {...attributes}>
          {visibleText === text ? children : visibleText}
        </p>
      );
    },
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
    li: ({ children, node }) => {
      const text = flattenText(children);
      const visibleText = stripEvidenceOnFileLabel(stripUserProvidedLabel(text));
      if (visibleText !== text && !visibleText) return null;
      return (
        <li className="leading-relaxed" {...position(node)}>
          {visibleText === text ? children : visibleText}
        </li>
      );
    },
    strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
    code: ({ children, className }) => {
      const language = className?.replace("language-", "") ?? "";
      if (language === "pmp-decision" || language === "pmp-decision-group") {
        return (
          <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">{children}</code>
        );
      }
      return (
        <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">{children}</code>
      );
    },
    table: ({ children }) => {
      const isInformationRegister = informationRegisterTable(children);
      const collapsed =
        isInformationRegister && editOptions?.informationRegisterOpen === false;
      return (
        <div
          id={isInformationRegister ? "project-documents-register" : undefined}
          className={[
            "my-4 overflow-x-auto border pmp-table-wrap",
            collapsed ? "hidden print:block" : "",
          ].join(" ")}
        >
          <table className="w-full min-w-[32rem] border-collapse text-left text-sm">
            {normalizeSummaryTable(children, projectTitle)}
          </table>
        </div>
      );
    },
    thead: ({ children }) => <thead className="bg-muted/50">{children}</thead>,
    th: ({ children }) => (
      <th className="border-b px-3 py-2 align-top font-medium text-foreground">
        {children}
      </th>
    ),
    td: ({ children }) => (
      <td className="border-b px-3 py-2 align-top text-foreground">
        {children}
      </td>
    ),
    // `tr` is the addressable unit for a table, never `td`/`th` — renderEvidenceCell
    // replaces cell content with badges, so a cell's rendered text is not its source.
    tr: ({ children, node }) => {
      const firstCell = Children.toArray(children)[0];
      const label = summaryLabel(firstCell);
      if (label === "critical current position" || label === "field") return null;
      const conflicted = rowHasConflict(children);
      const cells = Children.toArray(children).map((cell, index) => {
        if (!isValidElement<{ children?: ReactNode }>(cell)) return cell;
        return cloneElement(
          cell,
          { key: `cell-${index}` },
          renderEvidenceCell(cell.props.children, { conflicted }),
        );
      });
      return (
        <tr className="sw-table-row even:bg-muted/20" {...position(node)}>
          {normalizeSummaryRow(cells, projectTitle)}
        </tr>
      );
    },
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
    projectTitle?: string;
  } & InlineEditOptions,
): Components {
  let isFirstHeading = true;
  const changedRanges = options?.changedRanges ?? [];
  const position = (node: unknown) => mdPosition(node, changedRanges);

  return {
    ...baseComponents(changedRanges, options?.projectTitle, options),
    pre: ({ children }) => {
      const child = Array.isArray(children) ? children[0] : children;
      if (
        typeof child === "object" &&
        child !== null &&
        "props" in child &&
        typeof child.props === "object" &&
        child.props !== null &&
        "className" in child.props &&
        typeof child.props.className === "string"
      ) {
        const className = child.props.className;
        const raw = String("children" in child.props ? child.props.children : "").trim();

        if (className.includes("language-pmp-decision-group")) {
          if (options?.projectId) {
            const decisions = parseDecisionGroup(raw, options.decisionsById);
            if (decisions.length) {
              return (
                <DecisionSchedule
                  projectId={options.projectId}
                  decisions={decisions}
                  readOnly={options.readOnly}
                  onDraftUpdated={options.onDraftUpdated}
                />
              );
            }
          }
          return (
            <pre className="my-4 overflow-x-auto border bg-muted/30 p-3 text-xs">
              {children}
            </pre>
          );
        }

        if (/\blanguage-pmp-decision\b/.test(className)) {
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
            <pre className="my-4 overflow-x-auto border bg-muted/30 p-3 text-xs">
              {children}
            </pre>
          );
        }
      }
      return (
        <pre className="my-4 overflow-x-auto border bg-muted/30 p-3 text-xs">
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
      const isInformationRegister = /^(?:Project Documents|Information to review)\b/i.test(
        heading.trim(),
      );
      const attributes = position(node);
      const renderedRange = attributes
        ? {
            start: attributes["data-md-start"],
            end: attributes["data-md-end"],
          }
        : null;
      const sourceRange =
        renderedRange && options
          ? sourceRangeForRenderedBlock(
              options.sourceMarkdown,
              options.renderedMarkdown,
              renderedRange,
            )
          : null;
      const section = sourceRange
        ? options?.sourceSections.find((item) => item.start === sourceRange.start)
        : null;
      const activeParagraph =
        section && options?.activeParagraph?.sectionStart === section.start
          ? options.activeParagraph
          : null;
      const isEditingSection = Boolean(
        section &&
        options?.editingRange &&
        section.start <= options.editingRange.start &&
        options.editingRange.start < section.end,
      );
      const showActions = Boolean(
        section && (isEditingSection || (activeParagraph && !options?.editingRange)),
      );
      if (isInformationRegister) {
        const open = options?.informationRegisterOpen ?? false;
        return (
          <div className="mt-8 border-b pb-2 first:mt-0 print:break-before-page">
            <h2
              id={sectionAnchor(heading)}
              className="pmp-section-heading text-lg font-semibold"
              {...attributes}
            >
              <button
                type="button"
                className="flex min-h-11 w-full items-center gap-2 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring print:pointer-events-none"
                aria-expanded={open}
                aria-controls="project-documents-register"
                onClick={options?.onToggleInformationRegister}
              >
                <ChevronRight
                  className={[
                    "size-4 shrink-0 transition-transform",
                    open ? "rotate-90" : "",
                  ].join(" ")}
                  aria-hidden
                />
                <span>{children}</span>
              </button>
            </h2>
          </div>
        );
      }
      return (
        <div className="mt-8 flex min-h-8 items-center gap-2 border-b pb-2 first:mt-0">
          <h2
            id={sectionAnchor(heading)}
            className="pmp-section-heading min-w-0 text-lg font-semibold"
            {...attributes}
          >
            {children}
          </h2>
          {showActions && section ? (
            <div
              className="ml-auto flex shrink-0 items-center gap-1 print:hidden"
              data-instruction-ui
              data-paragraph-actions={section.start}
            >
              {activeParagraph && !isEditingSection && options?.onEditSelection ? (
                <Button
                  type="button"
                  size="icon-xs"
                  variant="outline"
                  aria-label="Edit paragraph manually"
                  title="Edit paragraph"
                  onClick={() => options.onEditSelection?.(activeParagraph.range)}
                >
                  <PencilLine aria-hidden />
                </Button>
              ) : null}
              {activeParagraph && !isEditingSection && options?.onEditWithAi ? (
                <Button
                  type="button"
                  size="icon-xs"
                  variant="outline"
                  aria-label="Edit paragraph with AI"
                  title="Edit with AI"
                  onClick={(event) =>
                    options.onEditWithAi?.(
                      activeParagraph.range,
                      event.currentTarget.getBoundingClientRect(),
                    )
                  }
                >
                  <img
                    src="/style-guide/logo/mark-solid.svg"
                    alt=""
                    aria-hidden
                    className="size-3.5"
                  />
                </Button>
              ) : null}
            </div>
          ) : null}
        </div>
      );
    },
  };
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

function informationRegisterTable(children: ReactNode): boolean {
  const text = flattenText(children).toLowerCase();
  return (
    text.includes("document number") &&
    text.includes("title") &&
    text.includes("rev") &&
    text.includes("category")
  );
}

function rangesEqual(
  left: MarkdownRange | null | undefined,
  right: MarkdownRange | null | undefined,
): boolean {
  return Boolean(left && right && left.start === right.start && left.end === right.end);
}

function isPmpGovernanceDisclaimer(value: string): boolean {
  const normalized = value.toLowerCase().replace("owner-side", "owner side");
  return (
    normalized.includes("owner side review and governance plan") &&
    normalized.includes("not an instruction") &&
    normalized.includes("statutory submission") &&
    normalized.includes("construction management plan")
  );
}

function stripOwnerBriefLeadIn(value: string): string {
  return value.replace(
    /^\s*draft owner project brief\s*(?:—|–|-|:)\s*formal sign[- ]off pending\.?\s*/i,
    "",
  );
}

function sectionAnchor(heading: string): string {
  return heading.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

function citationBadgeClassName(conflicted: boolean): string {
  return conflicted
    ? "evidence-status-chip border-[color-mix(in_oklch,var(--sw-critical)_40%,transparent)] bg-[color-mix(in_oklch,var(--sw-critical)_14%,transparent)] text-[var(--sw-critical)]"
    : "evidence-status-chip border-transparent bg-[var(--decision-evidenced-bg)] text-[var(--decision-evidenced-text)]";
}

function renderEvidenceCell(
  children: ReactNode,
  options?: { conflicted?: boolean },
): ReactNode {
  const text = flattenText(children).trim();
  let cleaned = stripEvidenceOnFileLabel(stripUserProvidedLabel(text));
  cleaned = stripRequiringResolution(cleaned);
  cleaned = stripConfirmedPrefix(cleaned);
  if (/^conflict\b/i.test(cleaned)) {
    return "";
  }
  if (cleaned !== text && !cleaned) return "—";
  if (/^\[\d+\]$/.test(cleaned)) {
    return (
      <Badge
        variant="outline"
        className={citationBadgeClassName(Boolean(options?.conflicted))}
      >
        {cleaned}
      </Badge>
    );
  }
  const match = EVIDENCE_STATUSES.find(
    (status) =>
      status !== "Conflict" &&
      (cleaned === status ||
        cleaned.startsWith(`${status} `) ||
        cleaned.includes(` / ${status}`)),
  );
  if (!match) {
    if (cleaned !== text) return cleaned || "—";
    return children;
  }
  return (
    <span className="inline-flex flex-wrap items-center gap-1">
      <Badge
        variant="outline"
        className={evidenceBadgeClassName(match)}
      >
        <span data-status-dot={evidenceStatusDot(match)} aria-hidden />
        {match}
      </Badge>
      {cleaned !== match ? <span>{cleaned.replace(match, "").trim()}</span> : null}
    </span>
  );
}

function rowHasConflict(children: ReactNode): boolean {
  return Children.toArray(children).some((cell) => {
    const text = flattenText(cell).trim();
    return (
      /^conflict\b/i.test(text) ||
      /\brequiring resolution\b/i.test(text) ||
      /\bconflict:\b/i.test(text)
    );
  });
}

function normalizeSummaryRow(children: ReactNode, projectTitle?: string): ReactNode {
  const cells = Children.toArray(children);
  if (cells.length < 2) return children;
  const label = flattenText(cells[0]).trim().toLowerCase().replace(/\s+/g, " ");
  const citation = flattenText(cells.at(-1)).trim();
  if (citation && !/^(?:\[\d+\]|\u2014|-)$/.test(citation)) return children;
  const originalDetail = stripConfirmedPrefix(
    stripEvidenceOnFileLabel(stripUserProvidedLabel(flattenText(cells[1]).trim())),
  );
  const legacyDescription =
    ["project", "project title"].includes(label) &&
    Boolean(projectTitle) &&
    originalDetail.toLowerCase() !== projectTitle?.trim().toLowerCase();
  const isProject = ["project", "project title"].includes(label) && !legacyDescription;
  const isOwner = [
    "client / owner",
    "client/owner",
    "owners",
    "owner",
    "client",
  ].includes(label);
  const isAddress = [
    "site / asset",
    "site/asset",
    "site / address",
    "address",
  ].includes(label);
  const isDescription =
    ["description", "project description"].includes(label) || legacyDescription;
  if (!isProject && !isOwner && !isAddress && !isDescription) return children;

  return cells.map((cell, index) => {
    if (!isValidElement<{ children?: ReactNode }>(cell)) return cell;
    if (index === 0) {
      let normalizedLabel = "Description";
      if (isProject) normalizedLabel = "Project";
      else if (isOwner) normalizedLabel = "Owner";
      else if (isAddress) normalizedLabel = "Address";
      return cloneElement(cell, undefined, normalizedLabel);
    }
    if (index === cells.length - 1) {
      if (isProject || legacyDescription || citation === "—" || citation === "-") {
        return cloneElement(cell, undefined, "");
      }
      return cell;
    }
    if (index !== 1) return cell;
    const detail = isProject && projectTitle ? projectTitle : originalDetail;
    const cleaned = isOwner
      ? stripProposalAddressee(detail)
      : isAddress
        ? summaryAddressDetail(detail)
        : detail;
    return cloneElement(cell, undefined, cleaned);
  });
}

function normalizeSummaryTable(children: ReactNode, projectTitle?: string): ReactNode {
  const tableChildren = Children.toArray(children);
  const desiredOrder = ["project", "address", "owner", "description"];
  const collectedRows: ReactNode[] = [];

  for (const tableChild of tableChildren) {
    if (!isValidElement<{ children?: ReactNode }>(tableChild)) continue;
    for (const row of Children.toArray(tableChild.props.children)) {
      const label = summaryLabelFromRow(row);
      if (label === "critical current position" || label === "field") continue;
      if (isCombinedIdentityLabel(label)) {
        collectedRows.push(...expandCombinedIdentityRow(row, projectTitle));
        continue;
      }
      collectedRows.push(row);
    }
  }

  // Drop non-table bridge content: identity summary is rows only.
  const rowKinds = collectedRows.map((row) => summaryRowKind(row, projectTitle));
  const identityKinds = desiredOrder.slice(0, 3);
  const isIdentitySummary =
    rowKinds.includes("address") &&
    rowKinds.includes("owner") &&
    (rowKinds.includes("project") ||
      rowKinds.includes("description") ||
      Boolean(projectTitle));

  if (!isIdentitySummary) {
    // Keep ordinary thead/tbody structure; only drop review-only rows.
    return tableChildren.map((tableChild) => {
      if (!isValidElement<{ children?: ReactNode }>(tableChild)) return tableChild;
      const rows = Children.toArray(tableChild.props.children).filter((row) => {
        const label = summaryLabelFromRow(row);
        return label !== "critical current position" && label !== "field";
      });
      return cloneElement(tableChild, undefined, rows);
    });
  }

  const bodyRows = collectedRows.map((row, index) =>
    asSummaryBodyRow(row, projectTitle, index),
  );
  const bodyKinds = bodyRows.map((row) => summaryRowKind(row, projectTitle));
  const rowsByKind = new Map<string, ReactNode>();
  bodyKinds.forEach((kind, index) => {
    if (!kind || rowsByKind.has(kind)) return;
    rowsByKind.set(kind, bodyRows[index]);
  });
  if (!rowsByKind.has("project") && projectTitle) {
    rowsByKind.set("project", summaryProjectRow(projectTitle));
  }
  const orderedKinds = desiredOrder.filter((kind) => rowsByKind.has(kind));
  if (!identityKinds.every((kind) => rowsByKind.has(kind))) {
    return <tbody key="summary-body">{bodyRows}</tbody>;
  }
  const knownRows = new Set(rowsByKind.values());
  const otherRows = bodyRows.filter((row) => !knownRows.has(row));
  const orderedRows = orderedKinds.map((kind) => rowsByKind.get(kind) as ReactNode);
  return (
    <tbody key="summary-body">{[...orderedRows, ...otherRows]}</tbody>
  );
}

function isCombinedIdentityLabel(label: string): boolean {
  return /^project\s*\/\s*(?:owners?|clients?)\s*\/\s*(?:site|address)$/i.test(label);
}

function expandCombinedIdentityRow(
  row: ReactNode,
  projectTitle?: string,
): ReactNode[] {
  if (!isValidElement<{ children?: ReactNode }>(row)) return [row];
  const cells = Children.toArray(row.props.children);
  if (cells.length < 2) return [row];
  const detail = stripConfirmedPrefix(flattenText(cells[1]).trim());
  const citation = flattenText(cells.at(-1)).trim();
  const citationValue = /^(?:\[\d+\]|\u2014|-)?$/.test(citation) ? citation : "";
  const parts = detail.split(/\s*\/\s*/).map((part) => stripConfirmedPrefix(part.trim()));
  while (parts.length < 3) parts.push("");
  const projectValue = projectTitle || parts[0];
  return [
    summaryIdentityRow("Project", projectValue, "", "combined-project"),
    summaryIdentityRow("Address", parts[2], citationValue, "combined-address"),
    summaryIdentityRow("Owner", parts[1], citationValue, "combined-owner"),
  ];
}

function summaryIdentityRow(
  label: string,
  detail: string,
  citation: string,
  key: string,
): ReactNode {
  return (
    <tr key={key} className="sw-table-row even:bg-muted/20">
      <td className="border-b px-3 py-2 align-top text-foreground">{label}</td>
      <td className="border-b px-3 py-2 align-top text-foreground">{detail}</td>
      <td className="border-b px-3 py-2 align-top text-foreground">{citation}</td>
    </tr>
  );
}

function asSummaryBodyRow(
  row: ReactNode,
  projectTitle: string | undefined,
  index: number,
): ReactNode {
  if (!isValidElement<{ children?: ReactNode }>(row)) return row;
  const conflicted = rowHasConflict(Children.toArray(row.props.children));
  const cells = Children.toArray(row.props.children).map((cell, cellIndex) => {
    if (!isValidElement<{ children?: ReactNode }>(cell)) return cell;
    return (
      <td
        key={`summary-cell-${index}-${cellIndex}`}
        className="border-b px-3 py-2 align-top text-foreground"
      >
        {renderEvidenceCell(cell.props.children, { conflicted })}
      </td>
    );
  });
  return (
    <tr key={`summary-row-${index}`} className="sw-table-row even:bg-muted/20">
      {normalizeSummaryRow(cells, projectTitle)}
    </tr>
  );
}

function summaryRowKind(row: ReactNode, projectTitle?: string): string | null {
  if (!isValidElement<{ children?: ReactNode }>(row)) return null;
  const cells = Children.toArray(row.props.children);
  if (!cells.length) return null;
  const label = flattenText(cells[0]).trim().toLowerCase().replace(/\s+/g, " ");
  if (
    ["site / asset", "site/asset", "site / address", "site", "address"].includes(
      label,
    )
  ) {
    return "address";
  }
  if (
    ["client / owner", "client/owner", "owners", "owner", "client"].includes(label)
  ) {
    return "owner";
  }
  if (["project", "project title"].includes(label)) {
    const detail = stripConfirmedPrefix(
      stripUserProvidedLabel(flattenText(cells[1]).trim()),
    );
    return projectTitle && detail.toLowerCase() !== projectTitle.trim().toLowerCase()
      ? "description"
      : "project";
  }
  return ["description", "project description"].includes(label) ? "description" : null;
}

function summaryLabel(node: ReactNode): string {
  return flattenText(node).trim().toLowerCase().replace(/\s+/g, " ");
}

function summaryLabelFromRow(row: ReactNode): string {
  if (!isValidElement<{ children?: ReactNode }>(row)) return "";
  return summaryLabel(Children.toArray(row.props.children)[0]);
}

function summaryProjectRow(projectTitle: string): ReactNode {
  return (
    <tr key="project-profile-title" className="sw-table-row even:bg-muted/20">
      <td className="border-b px-3 py-2 align-top text-foreground">Project</td>
      <td className="border-b px-3 py-2 align-top text-foreground">{projectTitle}</td>
      <td className="border-b px-3 py-2 align-top text-foreground" />
    </tr>
  );
}

function stripProposalAddressee(value: string): string {
  return value
    .replace(/\s*(?:\.\s*)?proposal addressed to\s+[^.]+\.?/gi, "")
    .replace(/[.\s]+$/, "");
}

function stripUserProvidedLabel(value: string): string {
  if (
    /^\s*\*{0,2}user[- ]provided\*{0,2}(?:\s*\/\s*(?:assumption|not evidenced))?\.?\s*$/i.test(
      value,
    )
  ) {
    return "—";
  }
  return value
    .replace(
      /\s*(?:\u2014|\u2013|-|\/|;|,)\s*(?:is\s+)?\*{0,2}user[- ]provided\*{0,2}(?:\s*\/\s*(?:assumption|not evidenced))?\.?/gi,
      "",
    )
    .replace(/(:\s*)\*{0,2}user[- ]provided\*{0,2}\s*/gi, "$1")
    .replace(/\s*,?\s*is\s+\*{0,2}user[- ]provided\*{0,2}\.?/gi, "")
    .trim();
}

function stripEvidenceOnFileLabel(value: string): string {
  if (/^\s*\*{0,2}evidence on file\*{0,2}\s*:?\s*\*{0,2}\s*\.?\s*$/i.test(value)) {
    return "";
  }
  return value
    .replace(/^\s*\*{0,2}evidence on file\*{0,2}\s*:\s*\*{0,2}\s*/i, "")
    .replace(
      /\s*(?:(?:\u2014|\u2013|-|\/|;|,)\s*)?\*{0,2}\bevidence on file\b\*{0,2}\s*:?\s*\*{0,2}\s*\.?/gi,
      "",
    )
    .trim();
}

function stripConfirmedPrefix(value: string): string {
  return value.replace(/^\s*\*?confirmed\b[:\s,\u2014\u2013-]*/i, "").trim();
}

function stripRequiringResolution(value: string): string {
  return value.replace(/\s*(?:,\s*)?\brequiring resolution\b\.?/gi, "").trim();
}

/** Blank non-table Project Summary prose so offsets stay aligned for selection. */
function blankProjectSummaryProse(markdown: string): string {
  const lines = markdown.split("\n");
  const out: string[] = [];
  let inSummary = false;
  let inCitationKey = false;
  let skippingCoverageRegister = false;
  let skippingCitationTable = false;
  for (const line of lines) {
    const trimmed = line.trim();
    if (/^##\s+/.test(trimmed)) {
      const heading = trimmed.replace(/^##\s+/, "").trim();
      skippingCoverageRegister = /evidence coverage register/i.test(heading);
      inSummary = /^project summary$/i.test(heading);
      inCitationKey = /^citation key$/i.test(heading);
      skippingCitationTable = false;
      if (skippingCoverageRegister) {
        out.push(" ".repeat(line.length));
        continue;
      }
      out.push(line);
      continue;
    }
    if (skippingCoverageRegister) {
      out.push(" ".repeat(line.length));
      continue;
    }
    if (inSummary && trimmed && !trimmed.startsWith("|")) {
      out.push(" ".repeat(line.length));
      continue;
    }
    if (inCitationKey) {
      if (/^\|\s*section\s*\|\s*evidence status\s*\|\s*(?:citation|ref)\s*\|$/i.test(trimmed)) {
        skippingCitationTable = true;
        out.push(" ".repeat(line.length));
        continue;
      }
      if (skippingCitationTable) {
        if (trimmed.startsWith("|")) {
          out.push(" ".repeat(line.length));
          continue;
        }
        skippingCitationTable = false;
      }
      if (/^\*\*documents cited:\*\*$/i.test(trimmed) || /^documents cited:$/i.test(trimmed)) {
        out.push(" ".repeat(line.length));
        continue;
      }
    }
    out.push(line);
  }
  return out.join("\n");
}

function summaryAddressDetail(detail: string): string {
  const withoutScope = detail
    .split(/(?<=\.)\s+/)
    .filter((sentence) => {
      const normalized = sentence.toLowerCase();
      return (
        !normalized.includes("upper metal roof") &&
        !normalized.includes("stormwater drainage")
      );
    })
    .join(" ")
    .trim();
  return stripConfirmedPrefix(withoutScope.replace(/[.\s]+$/, ""));
}

function evidenceStatusDot(
  status: (typeof EVIDENCE_STATUSES)[number],
): "positive" | "caution" | "critical" | "info" | "quiet" {
  switch (status) {
    case "Grounded":
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
  showTraceQa = true,
  containerRef,
  onDraftUpdated,
  editingRange,
  isSavingEdit = false,
  editError,
  onEditSelection,
  onEditWithAi,
  onCancelSelectionEdit,
  onSaveSelectionEdit,
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
  showTraceQa?: boolean;
  containerRef?: React.Ref<HTMLDivElement>;
  onDraftUpdated?: (draft: DraftArtifact) => void;
  editingRange?: MarkdownRange | null;
  isSavingEdit?: boolean;
  editError?: string | null;
  onEditSelection?: (range: MarkdownRange) => void;
  onEditWithAi?: (range: MarkdownRange, rect: DOMRect) => void;
  onCancelSelectionEdit?: () => void;
  onSaveSelectionEdit?: (range: MarkdownRange, markdown: string) => Promise<void>;
}) {
  const [paragraphTarget, setParagraphTarget] = useState<{
    sourceMarkdown: string;
    target: ParagraphTarget;
  } | null>(null);
  const [informationRegisterOpen, setInformationRegisterOpen] = useState(false);
  const traceQa = useMemo(() => splitTraceQa(markdown), [markdown]);
  const presentedPrimary = useMemo(
    () => groupConsecutiveDecisionFences(blankProjectSummaryProse(traceQa.primary)),
    [traceQa.primary],
  );
  const sections = useMemo(
    () => splitMarkdownSections(presentedPrimary),
    [presentedPrimary],
  );
  const sourceSections = useMemo(
    () => splitMarkdownSections(traceQa.primary),
    [traceQa.primary],
  );
  const activeParagraph =
    paragraphTarget?.sourceMarkdown === traceQa.primary
      ? paragraphTarget.target
      : null;
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
            aria-label="Document sections"
            className="sticky top-4 hidden h-fit min-w-44 shrink-0 lg:block print:hidden"
          >
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Sections
            </p>
            <ul className="space-y-1 text-xs">
              {sections.map((section) => (
                <li key={section.heading}>
                  <a
                    className="block px-2 py-1 text-muted-foreground hover:bg-muted hover:text-foreground"
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
              projectTitle,
              sourceMarkdown: traceQa.primary,
              renderedMarkdown: presentedPrimary,
              sourceSections,
              activeParagraph,
              editingRange,
              isSavingEdit,
              editError,
              onActivateParagraph: (target) =>
                setParagraphTarget((current) =>
                  current?.sourceMarkdown === traceQa.primary &&
                  current.target.sectionStart === target.sectionStart &&
                  rangesEqual(current.target.range, target.range)
                    ? current
                    : { sourceMarkdown: traceQa.primary, target },
                ),
              onEditSelection,
              onEditWithAi,
              onCancelSelectionEdit,
              onSaveSelectionEdit,
              informationRegisterOpen,
              onToggleInformationRegister: () =>
                setInformationRegisterOpen((current) => !current),
            })}
          >
            {presentedPrimary}
          </ReactMarkdown>
          {showTraceQa && traceQa.qa ? (
            <details className="trace-qa mt-10 border-t border-[var(--sw-edge)] pt-4 print:hidden">
              <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-4 font-medium text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                <span>Trace &amp; QA</span>
                <span className="font-mono text-xs uppercase tracking-[0.12em]">Review only</span>
              </summary>
              <div className="mt-3 border border-[var(--sw-edge)] bg-[var(--sw-panel)] p-4 text-muted-foreground">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={baseComponents([])}
                >
                  {traceQa.qa}
                </ReactMarkdown>
              </div>
            </details>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function hydrateEmbeddedDecision(
  embedded: EmbeddedDecision,
  canonical: ProjectDecision | undefined,
): EmbeddedDecision {
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

function parseDecisionGroup(
  raw: string,
  decisionsById?: ReadonlyMap<string, ProjectDecision>,
): EmbeddedDecision[] {
  try {
    const payloads = JSON.parse(raw) as unknown;
    if (!Array.isArray(payloads)) return [];
    return payloads
      .map((payload) => {
        const embedded = parseEmbeddedDecision(
          typeof payload === "string" ? payload : JSON.stringify(payload),
        );
        if (!embedded) return null;
        return hydrateEmbeddedDecision(embedded, decisionsById?.get(embedded.id));
      })
      .filter((decision): decision is EmbeddedDecision => decision !== null);
  } catch {
    return [];
  }
}
