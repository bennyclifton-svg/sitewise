import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { SortFileRow, SortFilesSummary } from "@/lib/types/project";
import { cn } from "@/lib/utils";

const OUTCOME_LABELS: Record<string, string> = {
  moved: "Filed",
  "already-filed": "Already filed",
  waiting: "Waiting",
  "needs-review": "Needs review",
  unresolved: "Unresolved",
  skipped: "Skipped",
  failed: "Failed",
  refused: "Refused",
};

const OUTCOME_CLASSES: Record<string, string> = {
  moved:
    "border-[color-mix(in_oklch,var(--sw-positive)_36%,transparent)] bg-[color-mix(in_oklch,var(--sw-positive)_10%,transparent)] text-[var(--sw-positive)]",
  "already-filed":
    "border-[color-mix(in_oklch,var(--sw-beam)_36%,transparent)] bg-[color-mix(in_oklch,var(--sw-beam)_10%,transparent)] text-[var(--sw-beam)]",
  waiting:
    "border-[color-mix(in_oklch,var(--sw-beam)_36%,transparent)] bg-[color-mix(in_oklch,var(--sw-beam)_10%,transparent)] text-[var(--sw-beam)]",
  "needs-review":
    "border-[color-mix(in_oklch,var(--sw-caution)_36%,transparent)] bg-[color-mix(in_oklch,var(--sw-caution)_10%,transparent)] text-[var(--sw-caution)]",
  unresolved:
    "border-[color-mix(in_oklch,var(--sw-caution)_36%,transparent)] bg-[color-mix(in_oklch,var(--sw-caution)_10%,transparent)] text-[var(--sw-caution)]",
  skipped: "border-muted-foreground/20 bg-muted/40 text-muted-foreground",
  failed: "border-destructive/30 bg-destructive/5 text-destructive",
  refused: "border-destructive/30 bg-destructive/5 text-destructive",
};

function countOf(summary: SortFilesSummary, key: keyof SortFilesSummary): number {
  return summary[key] ?? 0;
}

export function sortFilesHeadline(summary: SortFilesSummary): string {
  const waiting = countOf(summary, "waiting");
  const moved = countOf(summary, "moved");
  if (waiting > 0 && moved === 0) {
    const noun = waiting === 1 ? "file is" : "files are";
    return `${waiting} ${noun} still being processed. They will be filed automatically when classification completes.`;
  }
  const total =
    waiting +
    moved +
    countOf(summary, "already_filed") +
    countOf(summary, "unresolved") +
    countOf(summary, "skipped") +
    countOf(summary, "refused") +
    countOf(summary, "needs_review") +
    countOf(summary, "failed");
  return `Sorted ${total} file${total === 1 ? "" : "s"}`;
}

function breakdown(summary: SortFilesSummary): { label: string; value: number; hint: string }[] {
  const filed = countOf(summary, "moved") + countOf(summary, "already_filed");
  return [
    { label: "Filed", value: filed, hint: "" },
    {
      label: "Waiting for ingestion",
      value: countOf(summary, "waiting"),
      hint: "these will file automatically",
    },
    {
      label: "Needs review",
      value: countOf(summary, "needs_review"),
      hint: "low confidence, tap to classify",
    },
    { label: "Failed", value: countOf(summary, "failed"), hint: "retry the upload" },
    { label: "Unresolved", value: countOf(summary, "unresolved"), hint: "" },
    { label: "Refused", value: countOf(summary, "refused"), hint: "" },
    { label: "Skipped", value: countOf(summary, "skipped"), hint: "" },
  ].filter((row) => row.value > 0);
}

export function SortFilesResultPanel({
  summary,
  rows,
  onReviewFile,
  onRetryFailed,
}: {
  summary: SortFilesSummary | null;
  rows: SortFileRow[];
  onReviewFile?: (sourcePath: string) => void;
  onRetryFailed?: (sourcePath: string) => void;
}) {
  if (!summary) {
    return (
      <p className="text-sm text-muted-foreground">
        Run Sort Files to classify inbox uploads into lifecycle folders.
      </p>
    );
  }

  const lines = breakdown(summary);

  return (
    <div className="space-y-4">
      <p className="text-sm font-medium">{sortFilesHeadline(summary)}</p>
      {lines.length ? (
        <ul className="space-y-1 text-sm">
          {lines.map((line) => (
            <li key={line.label}>
              <span className="tabular-nums font-semibold">{line.value}</span>
              {"  "}
              {line.label}
              {line.hint ? (
                <span className="text-muted-foreground"> — {line.hint}</span>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}

      {rows.length ? (
        <div className="overflow-x-auto rounded-md border">
          <table className="w-full min-w-[52rem] text-left text-sm">
            <thead className="border-b bg-muted/40 text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="px-3 py-2 font-medium">File</th>
                <th className="px-3 py-2 font-medium">Outcome</th>
                <th className="px-3 py-2 font-medium">Destination</th>
                <th className="px-3 py-2 font-medium">Doc No</th>
                <th className="px-3 py-2 font-medium">Title</th>
                <th className="px-3 py-2 font-medium">Rev</th>
                <th className="px-3 py-2 font-medium">Category</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.source_path} className="border-b last:border-b-0">
                  <td className="px-3 py-2 align-top">
                    <p className="font-medium">{row.filename}</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">{row.source_path}</p>
                    {row.reason ? (
                      <p className="mt-1 text-xs text-muted-foreground">{row.reason}</p>
                    ) : null}
                    {row.outcome === "needs-review" && onReviewFile ? (
                      <Button
                        variant="link"
                        className="mt-1 h-auto px-0 text-xs"
                        onClick={() => onReviewFile(row.source_path)}
                      >
                        Classify
                      </Button>
                    ) : null}
                    {row.outcome === "failed" && onRetryFailed ? (
                      <Button
                        variant="link"
                        className="mt-1 h-auto px-0 text-xs"
                        onClick={() => onRetryFailed(row.source_path)}
                      >
                        Retry
                      </Button>
                    ) : null}
                  </td>
                  <td className="px-3 py-2 align-top">
                    <Badge
                      variant="outline"
                      className={cn("font-normal", OUTCOME_CLASSES[row.outcome])}
                    >
                      {OUTCOME_LABELS[row.outcome] ?? row.outcome}
                    </Badge>
                  </td>
                  <td className="px-3 py-2 align-top text-xs text-muted-foreground">
                    {row.destination_path ?? "—"}
                  </td>
                  <td className="px-3 py-2 align-top">{row.document_number ?? "—"}</td>
                  <td className="px-3 py-2 align-top">{row.title ?? "—"}</td>
                  <td className="px-3 py-2 align-top">{row.revision ?? "—"}</td>
                  <td className="px-3 py-2 align-top">{row.category ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">No inbox files were inspected.</p>
      )}
    </div>
  );
}
