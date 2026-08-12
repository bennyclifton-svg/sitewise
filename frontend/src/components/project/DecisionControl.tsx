import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MenuSelect } from "@/components/ui/menu-select";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import type { DraftArtifact, ProjectDecisionOption } from "@/lib/types/project";
import { cn } from "@/lib/utils";

export type EmbeddedDecision = {
  id: string;
  section?: string;
  label: string;
  options: ProjectDecisionOption[];
  selected: string;
  source?: string;
  rationale?: string;
  evidence_conflict?: boolean;
  agent_suggestion?: string;
  revision?: number;
  set_revision?: number;
  /** True when Sources ground the selection; false for AI default/assumption. */
  evidenced?: boolean;
};

const UNEVIDENCED_RATIONALE_RE =
  /\b(?:not evidenced|placeholder|selected default|working assumption|default_hint|do not nominate)\b/i;

// Shared with focused contract tests; this pure helper has no refresh state.
// eslint-disable-next-line react-refresh/only-export-components
export function selectionIsEvidenced(decision: EmbeddedDecision, source: string): boolean {
  if (source === "user") return true;
  if (typeof decision.evidenced === "boolean") return decision.evidenced;
  const rationale = decision.rationale?.trim() ?? "";
  if (!rationale) return false;
  return !UNEVIDENCED_RATIONALE_RE.test(rationale);
}

function provenanceChipClass(kind: "ai" | "user"): string {
  return kind === "user"
    ? "evidence-status-chip border-transparent bg-[var(--ok-bg)] text-[var(--ok-text)]"
    : "evidence-status-chip border-transparent bg-[var(--warn-bg)] text-[var(--warn-text)]";
}

function ProvenanceChip({ source }: { source: string }) {
  const kind = source === "user" ? "user" : "ai";
  return (
    <Badge variant="outline" className={provenanceChipClass(kind)}>
      {kind === "user" ? "[User]" : "[AI]"}
    </Badge>
  );
}

function DecisionRow({
  projectId,
  decision,
  readOnly = false,
  onDraftUpdated,
  bordered = false,
}: {
  projectId: string;
  decision: EmbeddedDecision;
  readOnly?: boolean;
  onDraftUpdated?: (draft: DraftArtifact) => void;
  bordered?: boolean;
}) {
  const [selected, setSelected] = useState(decision.selected);
  const [source, setSource] = useState(decision.source ?? "agent");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const evidenced = selectionIsEvidenced(decision, source);
  const selectedLabel = labelForValue(decision.options, selected);

  async function commit(nextValue: string) {
    if (readOnly || nextValue === selected) return;
    setIsSaving(true);
    setError(null);
    const previous = selected;
    setSelected(nextValue);
    setSource("user");
    try {
      const result = await api.putDecision(
        projectId,
        decision.id,
        nextValue,
        decision.revision ?? 1,
        decision.set_revision ?? 1,
      );
      setSelected(result.decision.selected);
      setSource(result.decision.source);
      onDraftUpdated?.(result.draft);
    } catch (err) {
      setSelected(previous);
      setError(
        err instanceof ApiError && err.status === 409
          ? "This decision changed elsewhere. Reload the PMP and try again."
          : err instanceof ApiError
            ? err.message
            : "Could not save decision.",
      );
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div
      className={cn(bordered && "border-b border-[var(--sw-edge)] pb-3 last:border-b-0 last:pb-0")}
      data-decision-id={decision.id}
      data-evidenced={evidenced ? "true" : "false"}
      data-selected-label={selectedLabel}
    >
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-[7.5rem_minmax(0,1fr)_auto] sm:items-start sm:gap-3">
        <p className="text-sm font-medium leading-snug">{decision.label}</p>

        <div className="flex flex-wrap gap-1.5 print:hidden">
          {decision.options.map((option) => {
            const isSelected = selected === option.value;
            return (
              <Button
                key={option.value}
                type="button"
                size="sm"
                variant="outline"
                disabled={readOnly || isSaving}
                className={cn(
                  "h-auto min-h-8 whitespace-normal px-2.5 py-1 text-left text-xs leading-snug",
                  isSelected &&
                    "border-transparent bg-[var(--decision-evidenced-bg)] text-[var(--decision-evidenced-text)] hover:bg-[var(--decision-evidenced-hover)] hover:text-[var(--decision-evidenced-text)]",
                )}
                onClick={() => void commit(option.value)}
              >
                {option.label}
              </Button>
            );
          })}
        </div>

        <div className="flex justify-start sm:justify-end">
          <ProvenanceChip source={source} />
        </div>
      </div>

      <dl className="decision-export-value mt-2 hidden grid-cols-[8rem_1fr] gap-2 text-sm print:grid">
        <dt className="font-medium text-muted-foreground">Selected position</dt>
        <dd>{selectedLabel}</dd>
      </dl>

      {error ? <p className="mt-2 text-xs text-destructive">{error}</p> : null}
    </div>
  );
}

export function DecisionControl({
  projectId,
  decision,
  readOnly = false,
  onDraftUpdated,
}: {
  projectId: string;
  decision: EmbeddedDecision;
  readOnly?: boolean;
  onDraftUpdated?: (draft: DraftArtifact) => void;
}) {
  return (
    <div className="sw-specular my-4 p-4">
      <DecisionRow
        projectId={projectId}
        decision={decision}
        readOnly={readOnly}
        onDraftUpdated={onDraftUpdated}
      />
    </div>
  );
}

/** Compact Finish-column control for FFE Schedule table rows. */
export function DecisionFinishSelect({
  projectId,
  decision,
  readOnly = false,
  onDraftUpdated,
}: {
  projectId: string;
  decision: EmbeddedDecision;
  readOnly?: boolean;
  onDraftUpdated?: (draft: DraftArtifact) => void;
}) {
  const [selected, setSelected] = useState(decision.selected);
  const [source, setSource] = useState(decision.source ?? "agent");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const evidenced = selectionIsEvidenced(decision, source);
  const selectedLabel = labelForValue(decision.options, selected);

  async function commit(nextValue: string) {
    if (readOnly || nextValue === selected) return;
    setIsSaving(true);
    setError(null);
    const previous = selected;
    setSelected(nextValue);
    setSource("user");
    try {
      const result = await api.putDecision(
        projectId,
        decision.id,
        nextValue,
        decision.revision ?? 1,
        decision.set_revision ?? 1,
      );
      setSelected(result.decision.selected);
      setSource(result.decision.source);
      onDraftUpdated?.(result.draft);
    } catch (err) {
      setSelected(previous);
      setError(
        err instanceof ApiError && err.status === 409
          ? "This decision changed elsewhere. Reload the PMP and try again."
          : err instanceof ApiError
            ? err.message
            : "Could not save decision.",
      );
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div
      className="flex min-w-[12rem] flex-col gap-1 print:hidden"
      data-decision-id={decision.id}
      data-evidenced={evidenced ? "true" : "false"}
      data-selected-label={selectedLabel}
    >
      <div className="flex items-start gap-2">
        <MenuSelect
          value={selected}
          options={decision.options}
          disabled={readOnly || isSaving}
          aria-label={decision.label}
          className="h-8 min-w-0 flex-1 text-xs"
          onChange={(value) => void commit(value)}
        />
        <ProvenanceChip source={source} />
      </div>
      <p className="decision-export-value hidden text-sm print:block">{selectedLabel}</p>
      {error ? <p className="text-xs text-destructive">{error}</p> : null}
    </div>
  );
}

export function DecisionSchedule({
  projectId,
  decisions,
  readOnly = false,
  onDraftUpdated,
}: {
  projectId: string;
  decisions: EmbeddedDecision[];
  readOnly?: boolean;
  onDraftUpdated?: (draft: DraftArtifact) => void;
}) {
  if (!decisions.length) return null;
  if (decisions.length === 1) {
    return (
      <DecisionControl
        projectId={projectId}
        decision={decisions[0]}
        readOnly={readOnly}
        onDraftUpdated={onDraftUpdated}
      />
    );
  }

  return (
    <div className="sw-specular my-4 space-y-3 p-4">
      {decisions.map((decision) => (
        <DecisionRow
          key={`${decision.id}:${decision.revision ?? 0}:${decision.set_revision ?? 0}`}
          projectId={projectId}
          decision={decision}
          readOnly={readOnly}
          onDraftUpdated={onDraftUpdated}
          bordered
        />
      ))}
    </div>
  );
}

function labelForValue(options: ProjectDecisionOption[], value: string): string {
  return options.find((option) => option.value === value)?.label ?? value;
}

// Shared with the markdown parser tests; this pure helper has no refresh state.
// eslint-disable-next-line react-refresh/only-export-components
export function parseEmbeddedDecision(raw: string): EmbeddedDecision | null {
  try {
    const payload = JSON.parse(raw) as Partial<EmbeddedDecision>;
    if (
      typeof payload.id !== "string" ||
      typeof payload.label !== "string" ||
      !Array.isArray(payload.options) ||
      typeof payload.selected !== "string"
    ) {
      return null;
    }
    const options = payload.options
      .map((option) => {
        if (typeof option !== "object" || option === null) return null;
        const candidate = option as Record<string, unknown>;
        const value =
          typeof candidate.value === "string"
            ? candidate.value
            : typeof candidate.id === "string"
              ? candidate.id
              : null;
        const label = typeof candidate.label === "string" ? candidate.label : value;
        if (!value || !label) return null;
        return { value, label };
      })
      .filter((option): option is ProjectDecisionOption => option !== null);
    if (!options.length) return null;
    return {
      id: payload.id,
      section: typeof payload.section === "string" ? payload.section : undefined,
      label: payload.label,
      options,
      selected: payload.selected,
      source: typeof payload.source === "string" ? payload.source : undefined,
      rationale: typeof payload.rationale === "string" ? payload.rationale : undefined,
      evidence_conflict: Boolean(payload.evidence_conflict),
      agent_suggestion:
        typeof payload.agent_suggestion === "string" ? payload.agent_suggestion : undefined,
      revision: typeof payload.revision === "number" ? payload.revision : undefined,
      set_revision:
        typeof payload.set_revision === "number" ? payload.set_revision : undefined,
      evidenced: typeof payload.evidenced === "boolean" ? payload.evidenced : undefined,
    };
  } catch {
    return null;
  }
}

const DECISION_FENCE_RE = /```pmp-decision\s*\n([\s\S]*?)\n```/g;

type DecisionMarkdownSegment =
  | { type: "text"; value: string }
  | { type: "decision"; body: string; raw: string };

/** Collapse consecutive decision fences into one schedule fence for compact rendering. */
// eslint-disable-next-line react-refresh/only-export-components
export function groupConsecutiveDecisionFences(markdown: string): string {
  const segments: DecisionMarkdownSegment[] = [];
  let last = 0;
  const re = new RegExp(DECISION_FENCE_RE.source, "g");
  let match: RegExpExecArray | null;
  while ((match = re.exec(markdown)) !== null) {
    if (match.index > last) {
      segments.push({ type: "text", value: markdown.slice(last, match.index) });
    }
    segments.push({
      type: "decision",
      body: match[1].trim(),
      raw: match[0],
    });
    last = match.index + match[0].length;
  }
  if (last < markdown.length) {
    segments.push({ type: "text", value: markdown.slice(last) });
  }

  const out: string[] = [];
  let i = 0;
  while (i < segments.length) {
    const seg = segments[i];
    if (seg.type !== "decision") {
      out.push(seg.value);
      i += 1;
      continue;
    }

    const bodies: string[] = [seg.body];
    let j = i + 1;
    while (j < segments.length) {
      const next = segments[j];
      if (next.type === "text" && next.value.trim() === "") {
        if (j + 1 < segments.length && segments[j + 1].type === "decision") {
          j += 1;
          continue;
        }
        break;
      }
      if (next.type === "decision") {
        bodies.push(next.body);
        j += 1;
        continue;
      }
      break;
    }

    if (bodies.length === 1) {
      out.push(seg.raw);
    } else {
      out.push(`\`\`\`pmp-decision-group\n${JSON.stringify(bodies)}\n\`\`\``);
    }
    i = j;
  }

  return out.join("");
}
