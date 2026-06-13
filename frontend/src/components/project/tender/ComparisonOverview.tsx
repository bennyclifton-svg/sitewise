import {
  AlertCircle,
  FileText,
  LoaderCircle,
  RefreshCw,
  Table2,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import type { TenderComparison, TenderJob, TenderQuote } from "@/lib/types/tender";

import {
  TENDER_QUOTE_STAGES,
  formatTenderDate,
  formatTenderMoney,
  formatTenderStage,
} from "./format";

export function ComparisonOverview({
  projectId,
  comparisonId,
}: {
  projectId: string;
  comparisonId: string;
}) {
  const [comparison, setComparison] = useState<TenderComparison | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState<string | null>(null);
  const [job, setJob] = useState<TenderJob | null>(null);

  async function loadComparison() {
    const data = await api.getTenderComparison(comparisonId);
    setComparison(data);
  }

  useEffect(() => {
    let cancelled = false;

    async function loadInitial() {
      setIsLoading(true);
      setError(null);
      try {
        const data = await api.getTenderComparison(comparisonId);
        if (!cancelled) setComparison(data);
      } catch (loadError) {
        if (!cancelled) {
          setError(
            loadError instanceof ApiError
              ? loadError.message
              : "Could not load tender comparison.",
          );
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void loadInitial();
    return () => {
      cancelled = true;
    };
  }, [comparisonId]);

  async function retryStage(quote: TenderQuote, stage: string) {
    setRetrying(`${quote.id}:${stage}`);
    setError(null);
    setJob(null);
    try {
      const queued = await api.retryTenderQuoteStage(quote.id, stage);
      setJob(queued);
      await loadComparison();
    } catch (retryError) {
      setError(
        retryError instanceof ApiError
          ? retryError.message
          : "Could not retry tender stage.",
      );
    } finally {
      setRetrying(null);
    }
  }

  if (isLoading) {
    return (
      <div className="flex min-h-72 items-center justify-center rounded-md border bg-card text-sm text-muted-foreground">
        <LoaderCircle className="mr-2 size-4 animate-spin" aria-hidden />
        Loading overview
      </div>
    );
  }

  if (error && !comparison) {
    return (
      <div className="flex min-h-72 items-center justify-center rounded-md border bg-card p-6 text-center">
        <div>
          <AlertCircle className="mx-auto size-7 text-destructive" aria-hidden />
          <p className="mt-3 text-sm font-medium text-destructive">{error}</p>
        </div>
      </div>
    );
  }

  if (!comparison) return null;

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_20rem]">
      <section className="rounded-md border bg-card shadow-sm">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3">
          <div>
            <p className="cockpit-zone-title">Stage status</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Created {formatTenderDate(comparison.created_at)}
            </p>
          </div>
          <Badge variant="outline">{formatTenderStage(comparison.status)}</Badge>
        </header>

        {error ? (
          <p className="mx-4 mt-4 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
            {error}
          </p>
        ) : null}

        {job ? (
          <p className="mx-4 mt-4 rounded-md border bg-muted px-3 py-2 text-sm">
            Queued {formatTenderStage(job.kind)} ({job.status})
          </p>
        ) : null}

        <div className="divide-y">
          {comparison.quotes.map((quote) => (
            <article key={quote.id} className="p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <h2 className="truncate text-lg font-semibold">{quote.builder_name}</h2>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {quote.quote_ref ?? "No reference"} / {formatTenderDate(quote.quote_date)}
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-mono text-sm tabular-nums">
                    {formatTenderMoney(quote.stated_total_cents)}
                  </p>
                  <Badge variant="secondary" className="mt-1">
                    {formatTenderStage(quote.stage)}
                  </Badge>
                </div>
              </div>

              <div className="mt-3 grid gap-3 md:grid-cols-3">
                <Metric label="GST" value={formatTenderStage(quote.gst_treatment)} />
                <Metric label="Contract" value={formatTenderStage(quote.contract_type)} />
                <Metric label="Documents" value={String(quote.documents?.length ?? 0)} />
              </div>

              <div className="mt-3 flex flex-wrap gap-1.5">
                {TENDER_QUOTE_STAGES.map((stage) => {
                  const key = `${quote.id}:${stage}`;
                  return (
                    <Button
                      key={stage}
                      type="button"
                      size="xs"
                      variant={stage === quote.stage ? "secondary" : "outline"}
                      disabled={retrying !== null}
                      onClick={() => void retryStage(quote, stage)}
                    >
                      {retrying === key ? (
                        <LoaderCircle className="size-3 animate-spin" aria-hidden />
                      ) : (
                        <RefreshCw className="size-3" aria-hidden />
                      )}
                      {formatTenderStage(stage)}
                    </Button>
                  );
                })}
              </div>
            </article>
          ))}
        </div>
      </section>

      <aside className="space-y-4">
        <section className="rounded-md border bg-card p-4 shadow-sm">
          <p className="cockpit-zone-title">Context</p>
          <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
            <Metric label="State" value={comparison.context.state} />
            <Metric label="Region" value={comparison.context.region} />
            <Metric label="Build" value={formatTenderStage(comparison.context.build_type)} />
            <Metric label="Spec" value={formatTenderStage(comparison.context.spec_level)} />
            <Metric label="Storeys" value={String(comparison.context.storeys)} />
            <Metric label="Budget" value={formatTenderMoney(comparison.context.target_budget_cents)} />
          </dl>
        </section>

        <section className="rounded-md border bg-card p-4 shadow-sm">
          <p className="cockpit-zone-title">Review surfaces</p>
          <div className="mt-3 grid gap-2">
            <Button asChild variant="outline" className="justify-start">
              <Link to={`/projects/${projectId}/tender/${comparison.id}/qa`}>
                <FileText className="size-4" aria-hidden />
                QA console
              </Link>
            </Button>
            <Button asChild variant="outline" className="justify-start">
              <Link to={`/projects/${projectId}/tender/${comparison.id}/matrix`}>
                <Table2 className="size-4" aria-hidden />
                Matrix
              </Link>
            </Button>
          </div>
        </section>
      </aside>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-md border bg-background px-3 py-2">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-1 truncate font-medium" title={value}>
        {value}
      </dd>
    </div>
  );
}
