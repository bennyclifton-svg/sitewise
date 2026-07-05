import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import type { DraftArtifact, ProjectDecisionOption } from "@/lib/types/project";

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
};

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

  const useSelect = decision.options.length > 4;

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
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold">{decision.label}</p>
          {decision.rationale ? (
            <p className="mt-1 text-xs text-muted-foreground">{decision.rationale}</p>
          ) : null}
        </div>
        <Badge variant={source === "user" ? "default" : "secondary"}>
          {source === "user" ? "Your selection" : "AI selection"}
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

      {useSelect ? (
        <label className="mt-3 block text-sm">
          <span className="sr-only">{decision.label}</span>
          <select
            className="w-full rounded-md border bg-background px-3 py-2 text-sm"
            value={selected}
            disabled={readOnly || isSaving}
            onChange={(event) => void commit(event.target.value)}
          >
            {decision.options.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      ) : (
        <div className="mt-3 flex flex-wrap gap-2">
          {decision.options.map((option) => (
            <Button
              key={option.value}
              type="button"
              size="sm"
              variant={selected === option.value ? "default" : "outline"}
              disabled={readOnly || isSaving}
              onClick={() => void commit(option.value)}
            >
              {option.label}
            </Button>
          ))}
        </div>
      )}

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
    };
  } catch {
    return null;
  }
}
