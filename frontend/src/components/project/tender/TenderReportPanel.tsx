import { AlertCircle, Check, ExternalLink, FileText, LoaderCircle, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";

import { DraftReviewPanel } from "@/components/project/DraftReviewPanel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import type { DraftArtifact } from "@/lib/types/project";
import type { TenderReportLifecycle } from "@/lib/types/tender";

export function TenderReportPanel({
  projectId,
  comparisonId,
}: {
  projectId: string;
  comparisonId: string;
}) {
  const [report, setReport] = useState<TenderReportLifecycle | null>(null);
  const [draft, setDraft] = useState<DraftArtifact | null>(null);
  const [isLoadingDraft, setIsLoadingDraft] = useState(true);
  const [isBuilding, setIsBuilding] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadDraft() {
      setIsLoadingDraft(true);
      setError(null);
      try {
        const latest = await api.getLatestDraft(projectId, "tender_report");
        if (!cancelled) setDraft(latest);
      } catch (loadError) {
        if (!cancelled) {
          setError(
            loadError instanceof ApiError
              ? loadError.message
              : "Could not load tender report draft.",
          );
        }
      } finally {
        if (!cancelled) setIsLoadingDraft(false);
      }
    }

    void loadDraft();
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  async function buildReport() {
    setIsBuilding(true);
    setError(null);
    try {
      const built = await api.buildTenderReport(comparisonId);
      setReport(built);
      setDraft(await api.getProjectDraft(projectId, built.draft_id));
    } catch (buildError) {
      setError(
        buildError instanceof ApiError
          ? buildError.message
          : "Could not build tender report.",
      );
    } finally {
      setIsBuilding(false);
    }
  }

  async function approveReport() {
    setIsApproving(true);
    setError(null);
    try {
      const approved = await api.approveTenderReport(comparisonId);
      setReport(approved);
      setDraft(await api.getProjectDraft(projectId, approved.draft_id));
    } catch (approveError) {
      setError(
        approveError instanceof ApiError
          ? approveError.message
          : "Could not approve tender report.",
      );
    } finally {
      setIsApproving(false);
    }
  }

  const htmlSrc = report?.html_path ? browserArtifactSrc(report.html_path) : null;
  const pdfHref = report?.pdf_path ? browserArtifactSrc(report.pdf_path) : null;

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_24rem]">
      <section className="rounded-md border bg-card shadow-sm">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3">
          <div>
            <p className="cockpit-zone-title">Report preview</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Build regenerates structured tables; narrative edits stay in the draft.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {report ? <Badge variant="outline">v{report.version}</Badge> : null}
            {report ? <Badge variant="secondary">{report.status}</Badge> : null}
          </div>
        </header>

        {error ? (
          <p className="mx-4 mt-4 flex items-center gap-2 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
            <AlertCircle className="size-4" aria-hidden />
            {error}
          </p>
        ) : null}

        <div className="flex flex-wrap gap-2 border-b px-4 py-3">
          <Button type="button" onClick={() => void buildReport()} disabled={isBuilding || isApproving}>
            {isBuilding ? (
              <LoaderCircle className="size-4 animate-spin" aria-hidden />
            ) : (
              <RefreshCw className="size-4" aria-hidden />
            )}
            {draft ? "Rebuild draft" : "Build draft"}
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => void approveReport()}
            disabled={isApproving || isBuilding || !draft}
          >
            {isApproving ? (
              <LoaderCircle className="size-4 animate-spin" aria-hidden />
            ) : (
              <Check className="size-4" aria-hidden />
            )}
            Approve
          </Button>
          {pdfHref ? (
            <Button asChild variant="outline">
              <a href={pdfHref} target="_blank" rel="noreferrer">
                <ExternalLink className="size-4" aria-hidden />
                Frozen PDF
              </a>
            </Button>
          ) : null}
        </div>

        {htmlSrc ? (
          <iframe
            title="Tender report HTML preview"
            src={htmlSrc}
            className="h-[48rem] w-full bg-white"
          />
        ) : (
          <div className="flex min-h-[30rem] items-center justify-center p-6 text-center">
            <div className="max-w-sm">
              <FileText className="mx-auto size-8 text-muted-foreground" aria-hidden />
              <p className="mt-3 text-sm font-medium">
                {isLoadingDraft ? "Loading report draft" : "No HTML preview yet"}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Build the report to generate an HTML artifact and draft content.
              </p>
            </div>
          </div>
        )}
      </section>

      <aside className="min-w-0 rounded-md border bg-card shadow-sm">
        <DraftReviewPanel
          projectId={projectId}
          draft={draft}
          workflowType="tender_report"
          onDraftUpdated={setDraft}
        />
      </aside>
    </div>
  );
}

function browserArtifactSrc(path: string): string | null {
  if (/^(https?:|blob:|data:)/.test(path)) return path;
  if (path.startsWith("/")) return path;
  return null;
}
