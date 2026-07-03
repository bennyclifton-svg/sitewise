import { AlertCircle, ArrowRight, FilePlus2, FileSearch, LoaderCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import type { TenderComparison } from "@/lib/types/tender";

import { formatTenderDate, formatTenderMoney, formatTenderStage } from "./format";
import { TenderIntakePanel } from "./TenderIntakePanel";

export function ComparisonList({ projectId }: { projectId: string }) {
  const [comparisons, setComparisons] = useState<TenderComparison[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isIntakeOpen, setIsIntakeOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadComparisons() {
      setIsLoading(true);
      setError(null);
      try {
        const data = await api.listTenderComparisons(projectId);
        if (!cancelled) setComparisons(data);
      } catch (loadError) {
        if (!cancelled) {
          setError(
            loadError instanceof ApiError
              ? loadError.message
              : "Could not load tender comparisons.",
          );
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void loadComparisons();
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  if (isLoading) {
    return (
      <div className="flex min-h-72 items-center justify-center rounded-md border bg-card text-sm text-muted-foreground">
        <LoaderCircle className="mr-2 size-4 animate-spin" aria-hidden />
        Loading comparisons
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-72 items-center justify-center rounded-md border bg-card p-6">
        <div className="max-w-md text-center">
          <AlertCircle className="mx-auto size-7 text-destructive" aria-hidden />
          <p className="mt-3 text-sm font-medium text-destructive">{error}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            This route is ready; it needs the project-scoped comparison list API for
            live rows.
          </p>
        </div>
      </div>
    );
  }

  if (!comparisons.length) {
    return (
      <div className="space-y-4">
        <TenderIntakePanel projectId={projectId} />
        <div className="flex min-h-32 items-center justify-center rounded-md border border-dashed bg-card p-6 text-center">
          <div className="max-w-sm">
            <FileSearch className="mx-auto size-8 text-muted-foreground" aria-hidden />
            <p className="mt-3 text-sm font-medium">No tender comparisons yet</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {isIntakeOpen ? (
        <TenderIntakePanel projectId={projectId} onCancel={() => setIsIntakeOpen(false)} />
      ) : null}

      <section className="rounded-md border bg-card shadow-sm">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3">
          <p className="cockpit-zone-title">Comparisons</p>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => setIsIntakeOpen(true)}
          >
            <FilePlus2 className="size-4" aria-hidden />
            New comparison
          </Button>
        </header>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[52rem] table-fixed text-left text-sm">
            <colgroup>
              <col className="w-[15rem]" />
              <col className="w-[7rem]" />
              <col />
              <col className="w-[8rem]" />
              <col className="w-[7rem]" />
            </colgroup>
            <thead className="border-b text-xs text-muted-foreground">
              <tr>
                <th className="px-4 py-2 font-medium">Comparison</th>
                <th className="px-3 py-2 font-medium">Status</th>
                <th className="px-3 py-2 font-medium">Quotes</th>
                <th className="px-3 py-2 font-medium">Target</th>
                <th className="px-3 py-2 font-medium" aria-label="Open" />
              </tr>
            </thead>
            <tbody>
              {comparisons.map((comparison) => (
                <tr key={comparison.id} className="border-b last:border-b-0">
                  <td className="px-4 py-3 align-top">
                    <p className="font-medium">{formatTenderDate(comparison.created_at)}</p>
                    <p className="mt-1 truncate text-xs text-muted-foreground">
                      {comparison.id}
                    </p>
                  </td>
                  <td className="px-3 py-3 align-top">
                    <Badge variant="outline">{formatTenderStage(comparison.status)}</Badge>
                  </td>
                  <td className="px-3 py-3 align-top">
                    <div className="flex flex-wrap gap-1.5">
                      {comparison.quotes.map((quote) => (
                        <Badge key={quote.id} variant="secondary">
                          {quote.builder_name}
                        </Badge>
                      ))}
                    </div>
                  </td>
                  <td className="px-3 py-3 align-top tabular-nums">
                    {formatTenderMoney(comparison.context.target_budget_cents)}
                  </td>
                  <td className="px-3 py-3 align-top">
                    <Button asChild size="sm" variant="outline">
                      <Link to={`/projects/${projectId}/tender/${comparison.id}`}>
                        Open
                        <ArrowRight className="size-4" aria-hidden />
                      </Link>
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
