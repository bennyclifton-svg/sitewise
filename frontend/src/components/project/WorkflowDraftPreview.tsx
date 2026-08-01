import { Loader2 } from "lucide-react";

import { MarkdownContent } from "@/components/project/MarkdownContent";
import type { WorkflowRunPreview } from "@/lib/workflow-progress";

const PREVIEW_STAGE_LABELS: Record<string, string> = {
  scaffold: "Drafting — structure and evidence in place, writing the narrative…",
};

/**
 * The document as it is being built.
 *
 * The deterministic scaffold exists minutes before the narrative model returns,
 * so it is shown as soon as the run publishes it. This is provisional content:
 * it is deliberately read-only and visually distinct from an accepted draft.
 */
export function WorkflowDraftPreview({
  preview,
  title,
}: {
  preview: WorkflowRunPreview;
  title: string;
}) {
  return (
    <section
      data-testid="workflow-draft-preview"
      aria-busy="true"
      aria-label={`${title} in progress`}
      className="rounded-md border border-dashed border-primary/25 bg-primary/[0.03]"
    >
      <header className="flex items-center gap-2 border-b border-dashed border-primary/20 px-3 py-2 text-xs text-muted-foreground">
        <Loader2
          className="size-3 shrink-0 animate-spin text-primary/70 motion-reduce:animate-none"
          aria-hidden
        />
        <span className="truncate">
          {PREVIEW_STAGE_LABELS[preview.stage] ?? "Drafting…"}
        </span>
      </header>
      <div className="px-3 py-2 opacity-70">
        <MarkdownContent markdown={preview.markdown} readOnly />
      </div>
    </section>
  );
}
