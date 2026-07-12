import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
  /** True when Sources ground the selection; false for AI default/assumption. */
  evidenced?: boolean;
};

const UNEVIDENCED_RATIONALE_RE =
  /\b(?:not evidenced|placeholder|selected default|working assumption|default_hint)\b/i;

export function selectionIsEvidenced(decision: EmbeddedDecision, source: string): boolean {
  if (source === "user") return true;
  if (typeof decision.evidenced === "boolean") return decision.evidenced;
  const rationale = decision.rationale?.trim() ?? "";
  if (!rationale) return false;
  return !UNEVIDENCED_RATIONALE_RE.test(rationale);
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
  const [selected, setSelected] = useState(decision.selected);
  const [source, setSource] = useState(decision.source ?? "agent");
  const [evidenceConflict, setEvidenceConflict] = useState(Boolean(decision.evidence_conflict));
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const evidenced = selectionIsEvidenced(decision, source);
  const badgeLabel =
    source === "user" ? "Your selection" : evidenced ? "From evidence" : "AI selection";

  async function commit(nextValue: string) {
    if (readOnly || nextValue === selected) return;
    setIsSaving(true);
    setError(null);
    const previous = selected;
    setSelected(nextValue);
    setSource("user");
    setEvidenceConflict(false);
    try {
      const result = await api.putDecision(projectId, decision.id, nextValue);
      setSelected(result.decision.selected);
      setSource(result.decision.source);
      setEvidenceConflict(result.decision.evidence_conflict);
      onDraftUpdated?.(result.draft);
    } catch (err) {
      setSelected(previous);
      setError(err instanceof ApiError ? err.message : "Could not save decision.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div
      className="my-4 rounded-md border bg-background p-4"
      data-decision-id={decision.id}
      data-evidenced={evidenced ? "true" : "false"}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold">{decision.label}</p>
          {decision.rationale ? (
            <p className="mt-1 text-xs text-muted-foreground">{decision.rationale}</p>
          ) : null}
        </div>
        <Badge
          variant={source === "user" || evidenced ? "default" : "secondary"}
          className={cn(
            !evidenced && source !== "user" && "bg-[var(--decision-assumed)] text-white",
          )}
        >
          {badgeLabel}
        </Badge>
      </div>

      {evidenceConflict ? (
        <p className="mt-2 text-xs text-amber-700 dark:text-amber-300">
          Current corpus evidence suggests a different option
          {decision.agent_suggestion
            ? ` (${labelForValue(decision.options, decision.agent_suggestion)}).`
            : "."}{" "}
          Your selection is kept — review the latest workflow run in Activity.
        </p>
      ) : null}

      <div className="mt-3 flex flex-wrap gap-2">
        {decision.options.map((option) => {
          const isSelected = selected === option.value;
          return (
            <Button
              key={option.value}
              type="button"
              size="sm"
              variant={isSelected ? "default" : "outline"}
              disabled={readOnly || isSaving}
              className={cn(
                isSelected &&
                  evidenced &&
                  "border-transparent bg-[var(--decision-evidenced)] text-white hover:bg-[var(--decision-evidenced-hover)]",
                isSelected &&
                  !evidenced &&
                  "border-transparent bg-[var(--decision-assumed)] text-white hover:bg-[var(--decision-assumed-hover)]",
              )}
              onClick={() => void commit(option.value)}
            >
              {option.label}
            </Button>
          );
        })}
      </div>

      {error ? <p className="mt-2 text-xs text-destructive">{error}</p> : null}
    </div>
  );
}

function labelForValue(options: ProjectDecisionOption[], value: string): string {
  return options.find((option) => option.value === value)?.label ?? value;
}

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
        const value =
          typeof option.value === "string"
            ? option.value
            : typeof option.id === "string"
              ? option.id
              : null;
        const label = typeof option.label === "string" ? option.label : value;
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
      evidenced: typeof payload.evidenced === "boolean" ? payload.evidenced : undefined,
    };
  } catch {
    return null;
  }
}
