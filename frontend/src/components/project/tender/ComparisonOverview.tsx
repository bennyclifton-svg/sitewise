import {
  AlertCircle,
  AlertTriangle,
  Check,
  ChevronDown,
  ChevronRight,
  FileText,
  LoaderCircle,
  Play,
  RefreshCw,
  Table2,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import { useTenderComparison, useTenderProgress } from "@/lib/queries/tender";
import type {
  TenderProgressMilestone,
  TenderQuote,
} from "@/lib/types/tender";

import {
  TENDER_COMPARISON_STAGES,
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
  const comparisonQuery = useTenderComparison(comparisonId);
  const progressQuery = useTenderProgress(comparisonId);
  const comparison = comparisonQuery.data ?? null;
  const progress = progressQuery.data ?? null;
  const isLoading = comparisonQuery.isLoading || progressQuery.isLoading;
  const queryError = comparisonQuery.error ?? progressQuery.error;
  const [error, setError] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [processNotes, setProcessNotes] = useState<string[]>([]);
  const [retrying, setRetrying] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const isProcessingNow = progress?.is_processing ?? false;
  const wasProcessing = useRef(false);
  useEffect(() => {
    if (wasProcessing.current && !isProcessingNow) {
      void comparisonQuery.refetch();
    }
    wasProcessing.current = isProcessingNow;
  }, [comparisonQuery, isProcessingNow]);

  async function loadAll() {
    await Promise.all([comparisonQuery.refetch(), progressQuery.refetch()]);
  }

  async function startProcessing() {
    setProcessing(true);
    setError(null);
    setProcessNotes([]);
    try {
      const result = await api.processTenderComparison(comparisonId);
      setProcessNotes(result.notes);
      await loadAll();
    } catch (processError) {
      setError(
        processError instanceof ApiError
          ? processError.message
          : "Could not start processing.",
      );
    } finally {
      setProcessing(false);
    }
  }

  async function retryStage(quote: TenderQuote, stage: string) {
    setRetrying(`${quote.id}:${stage}`);
    setError(null);
    try {
      await api.retryTenderQuoteStage(quote.id, stage);
      await loadAll();
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

  async function retryComparisonStage(stage: string) {
    setRetrying(`comparison:${stage}`);
    setError(null);
    try {
      await api.retryTenderComparisonStage(comparisonId, stage);
      await loadAll();
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

  const visibleError = error ?? (
    queryError instanceof ApiError
      ? queryError.message
      : queryError
        ? "Could not load tender comparison."
        : null
  );

  if (visibleError && !comparison) {
    return (
      <div className="flex min-h-72 items-center justify-center rounded-md border bg-card p-6 text-center">
        <div>
          <AlertCircle className="mx-auto size-7 text-destructive" aria-hidden />
          <p className="mt-3 text-sm font-medium text-destructive">{visibleError}</p>
        </div>
      </div>
    );
  }

  if (!comparison) return null;

  const milestones = progress?.milestones ?? [];
  const pipelineMilestones = milestones.filter(
    (m) => m.key !== "review" && m.key !== "report",
  );
  const hasFailure = pipelineMilestones.some((m) => m.state === "failed");
  const pipelineDone =
    pipelineMilestones.length > 0 &&
    pipelineMilestones.every((m) => m.state === "done");
  const isRunning = progress?.is_processing ?? false;
  const showProcessButton = !isRunning && !pipelineDone;

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_20rem]">
      <div className="space-y-4">
        <section className="rounded-md border bg-card p-4 shadow-sm">
          <header className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="cockpit-zone-title">Progress</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Created {formatTenderDate(comparison.created_at)}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {isRunning ? (
                <span className="flex items-center gap-1.5 text-sm text-[var(--info-text)]">
                  <LoaderCircle className="size-4 animate-spin" aria-hidden />
                  Processing
                </span>
              ) : null}
              {showProcessButton ? (
                <Button
                  type="button"
                  disabled={processing}
                  onClick={() => void startProcessing()}
                >
                  {processing ? (
                    <LoaderCircle className="size-4 animate-spin" aria-hidden />
                  ) : (
                    <Play className="size-4" aria-hidden />
                  )}
                  {hasFailure ? "Retry processing" : "Process quotes"}
                </Button>
              ) : null}
            </div>
          </header>

          <ProgressGates milestones={milestones} percent={progress?.percent ?? 0} />

          {visibleError ? (
            <p className="mt-4 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              {visibleError}
            </p>
          ) : null}
          {processNotes.map((note) => (
            <p
              key={note}
              className="mt-2 rounded-md border bg-muted px-3 py-2 text-sm text-muted-foreground"
            >
              {note}
            </p>
          ))}

          {progress && progress.qa_pending > 0 && !isRunning ? (
            <div className="mt-4 flex flex-wrap items-center justify-between gap-2 rounded-md border border-[var(--warn-text)]/30 bg-[var(--warn-bg)] px-3 py-2">
              <p className="text-sm text-[var(--warn-text)]">
                {progress.qa_pending} finding{progress.qa_pending === 1 ? "" : "s"} need
                your review before the report can be built.
              </p>
              <Button asChild size="sm" variant="outline">
                <Link to={`/projects/${projectId}/tender/${comparison.id}/matrix`}>
                  Review in matrix
                </Link>
              </Button>
            </div>
          ) : null}
        </section>

        <section className="rounded-md border bg-card shadow-sm">
          <header className="border-b px-4 py-3">
            <p className="cockpit-zone-title">Quotes</p>
          </header>
          <div className="divide-y">
            {(progress?.quotes ?? []).map((quote) => (
              <article key={quote.quote_id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
                <div className="min-w-0">
                  <h2 className="truncate font-semibold">{quote.builder_name}</h2>
                  {quote.documents.map((doc) => (
                    <p
                      key={doc.filename}
                      className={
                        doc.ingest_status === "ingested"
                          ? "mt-0.5 truncate text-xs text-muted-foreground"
                          : "mt-0.5 flex items-center gap-1 truncate text-xs text-[var(--alert-text)]"
                      }
                      title={doc.filename}
                    >
                      {doc.ingest_status !== "ingested" ? (
                        <AlertTriangle className="size-3 shrink-0" aria-hidden />
                      ) : null}
                      {doc.filename}
                      {doc.ingest_status !== "ingested"
                        ? ` - ${formatTenderStage(doc.ingest_status)}`
                        : ""}
                    </p>
                  ))}
                </div>
                <div className="text-right">
                  <p className="font-mono text-sm tabular-nums">
                    {formatTenderMoney(quote.stated_total_cents)}
                  </p>
                  <Badge variant="secondary" className="mt-1">
                    {formatTenderStage(quote.stage)}
                  </Badge>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="rounded-md border bg-card shadow-sm">
          <button
            type="button"
            className="flex w-full items-center gap-2 px-4 py-3 text-left text-sm text-muted-foreground hover:text-foreground"
            onClick={() => setShowAdvanced((value) => !value)}
          >
            {showAdvanced ? (
              <ChevronDown className="size-4" aria-hidden />
            ) : (
              <ChevronRight className="size-4" aria-hidden />
            )}
            Advanced pipeline controls
          </button>
          {showAdvanced ? (
            <div className="space-y-4 border-t px-4 py-3">
              <p className="text-xs text-muted-foreground">
                Stages chain automatically. Use these only to re-run a single stage
                manually.
              </p>
              {comparison.quotes.map((quote) => (
                <div key={quote.id}>
                  <p className="text-xs font-medium">{quote.builder_name}</p>
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {TENDER_QUOTE_STAGES.map((stage) => {
                      const key = `${quote.id}:${stage}`;
                      return (
                        <Button
                          key={stage}
                          type="button"
                          size="xs"
                          variant="outline"
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
                </div>
              ))}
              <div>
                <p className="text-xs font-medium">Comparison stages</p>
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  {TENDER_COMPARISON_STAGES.map((stage) => {
                    const key = `comparison:${stage}`;
                    return (
                      <Button
                        key={stage}
                        type="button"
                        size="xs"
                        variant="outline"
                        disabled={retrying !== null}
                        onClick={() => void retryComparisonStage(stage)}
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
              </div>
            </div>
          ) : null}
        </section>
      </div>

      <aside className="space-y-4">
        <section className="rounded-md border bg-card p-4 shadow-sm">
          <p className="cockpit-zone-title">Context</p>
          <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
            <Metric label="State" value={comparison.context.state} />
            <Metric label="Region" value={comparison.context.region} />
            <Metric label="Build" value={formatTenderStage(comparison.context.build_type)} />
            <Metric label="Spec" value={formatTenderStage(comparison.context.spec_level)} />
            <Metric label="Storeys" value={comparison.context.storeys} />
            <Metric label="Budget" value={formatTenderMoney(comparison.context.target_budget_cents)} />
          </dl>
        </section>

        <section className="rounded-md border bg-card p-4 shadow-sm">
          <p className="cockpit-zone-title">Review surfaces</p>
          <div className="mt-3 grid gap-2">
            <Button asChild variant="outline" className="justify-start">
              <Link to={`/projects/${projectId}/tender/${comparison.id}/matrix`}>
                <Table2 className="size-4" aria-hidden />
                Matrix and QA
                {progress && progress.qa_pending > 0 ? (
                  <Badge variant="secondary" className="ml-auto">
                    {progress.qa_pending}
                  </Badge>
                ) : null}
              </Link>
            </Button>
            <Button asChild variant="outline" className="justify-start">
              <Link to={`/projects/${projectId}/tender/${comparison.id}/report`}>
                <FileText className="size-4" aria-hidden />
                Report
              </Link>
            </Button>
          </div>
        </section>
      </aside>
    </div>
  );
}

function ProgressGates({
  milestones,
  percent,
}: {
  milestones: TenderProgressMilestone[];
  percent: number;
}) {
  if (milestones.length === 0) return null;

  const activeDetail = milestones.find(
    (m) => m.state === "running" || m.state === "failed" || m.state === "attention",
  );

  return (
    <div className="mt-4">
      <ol className="flex items-start gap-0" aria-label={`Progress ${percent}%`}>
        {milestones.map((milestone, index) => (
          <li key={milestone.key} className="flex min-w-0 flex-1 flex-col items-center">
            <div className="flex w-full items-center">
              <div
                className={`h-0.5 flex-1 ${
                  index === 0 ? "bg-transparent" : connectorTone(milestones[index - 1])
                }`}
              />
              <GateDot milestone={milestone} />
              <div
                className={`h-0.5 flex-1 ${
                  index === milestones.length - 1
                    ? "bg-transparent"
                    : connectorTone(milestone)
                }`}
              />
            </div>
            <p
              className={`mt-1.5 w-full truncate px-1 text-center text-[11px] ${gateLabelTone(milestone)}`}
              title={milestone.detail ?? milestone.label}
            >
              {milestone.label}
            </p>
          </li>
        ))}
      </ol>
      {activeDetail?.detail ? (
        <p
          className={`mt-2 text-center text-xs ${
            activeDetail.state === "failed"
              ? "text-[var(--alert-text)]"
              : activeDetail.state === "attention"
                ? "text-[var(--warn-text)]"
                : "text-[var(--info-text)]"
          }`}
        >
          {activeDetail.detail}
        </p>
      ) : null}
    </div>
  );
}

function GateDot({ milestone }: { milestone: TenderProgressMilestone }) {
  const base =
    "flex size-6 shrink-0 items-center justify-center rounded-full border text-[10px]";
  if (milestone.state === "done") {
    return (
      <span className={`${base} border-transparent bg-[var(--ok-bg)] text-[var(--ok-text)]`}>
        <Check className="size-3.5" aria-hidden />
      </span>
    );
  }
  if (milestone.state === "running") {
    return (
      <span className={`${base} border-transparent bg-[var(--info-bg)] text-[var(--info-text)]`}>
        <LoaderCircle className="size-3.5 animate-spin" aria-hidden />
      </span>
    );
  }
  if (milestone.state === "failed") {
    return (
      <span className={`${base} border-transparent bg-[var(--alert-bg)] text-[var(--alert-text)]`}>
        <AlertCircle className="size-3.5" aria-hidden />
      </span>
    );
  }
  if (milestone.state === "attention") {
    return (
      <span className={`${base} border-transparent bg-[var(--warn-bg)] text-[var(--warn-text)]`}>
        <AlertTriangle className="size-3.5" aria-hidden />
      </span>
    );
  }
  return <span className={`${base} border-border bg-muted text-muted-foreground`} />;
}

function connectorTone(previous: TenderProgressMilestone): string {
  if (previous.state === "done") return "bg-[var(--ok-text)]/40";
  if (previous.state === "running") return "bg-[var(--info-text)]/40";
  return "bg-border";
}

function gateLabelTone(milestone: TenderProgressMilestone): string {
  if (milestone.state === "done") return "text-[var(--ok-text)]";
  if (milestone.state === "running") return "text-[var(--info-text)] font-medium";
  if (milestone.state === "failed") return "text-[var(--alert-text)] font-medium";
  if (milestone.state === "attention") return "text-[var(--warn-text)] font-medium";
  return "text-muted-foreground";
}

function Metric({
  label,
  value,
}: {
  label: string;
  value: string | number | null | undefined;
}) {
  const displayValue = value === null || value === undefined || value === ""
    ? "Not stated"
    : String(value);

  return (
    <div className="min-w-0 rounded-md border bg-background px-3 py-2">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-1 truncate font-medium" title={displayValue}>
        {displayValue}
      </dd>
    </div>
  );
}
