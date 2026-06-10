import { Badge } from "@/components/ui/badge";
import type { SortFileRow, SortFilesSummary } from "@/lib/types/project";
import { cn } from "@/lib/utils";

const OUTCOME_LABELS: Record<string, string> = {
  moved: "Moved",
  "already-filed": "Already filed",
  unresolved: "Unresolved",
  skipped: "Skipped",
  refused: "Refused",
};

const OUTCOME_CLASSES: Record<string, string> = {
  moved: "border-emerald-500/30 bg-emerald-500/5 text-emerald-700 dark:text-emerald-300",
  "already-filed": "border-sky-500/30 bg-sky-500/5 text-sky-700 dark:text-sky-300",
  unresolved: "border-amber-500/30 bg-amber-500/5 text-amber-800 dark:text-amber-200",
  skipped: "border-muted-foreground/20 bg-muted/40 text-muted-foreground",
  refused: "border-destructive/30 bg-destructive/5 text-destructive",
};

export function SortFilesResultPanel({
  summary,
  rows,
}: {
  summary: SortFilesSummary | null;
  rows: SortFileRow[];
}) {
  if (!summary) {
    return (
      <p className="text-sm text-muted-foreground">
        Run Sort Files to classify inbox uploads into lifecycle folders.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-2 sm:grid-cols-3 lg:grid-cols-6">
        <SummaryMetric label="Inspected" value={summary.inspected} />
        <SummaryMetric label="Moved" value={summary.moved} />
        <SummaryMetric label="Unresolved" value={summary.unresolved} />
        <SummaryMetric label="Refused" value={summary.refused} />
        <SummaryMetric label="Already filed" value={summary.already_filed} />
        <SummaryMetric label="Skipped" value={summary.skipped} />
      </div>

      {rows.length ? (
        <div className="overflow-x-auto rounded-md border">
          <table className="w-full min-w-[40rem] text-left text-sm">
            <thead className="border-b bg-muted/40 text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="px-3 py-2 font-medium">File</th>
                <th className="px-3 py-2 font-medium">Outcome</th>
                <th className="px-3 py-2 font-medium">Destination</th>
                <th className="px-3 py-2 font-medium">Doc No</th>
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

function SummaryMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border bg-muted/20 px-3 py-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-lg font-semibold tabular-nums">{value}</p>
    </div>
  );
}
