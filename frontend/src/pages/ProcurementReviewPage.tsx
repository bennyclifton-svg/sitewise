import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useOutletContext, useParams } from "react-router-dom";

import { CopyContentButton } from "@/components/project/CopyContentButton";
import { DraftDownloadMenu } from "@/components/project/DraftDownloadMenu";
import { DraftReviewPanel } from "@/components/project/DraftReviewPanel";
import { ProcurementReviewProgress } from "@/components/project/ProcurementReviewProgress";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import { queryClient } from "@/lib/query-client";
import { projectKeys } from "@/lib/queries/project-data";
import type { ProjectCockpitOutletContext } from "@/pages/ProjectCockpitPage";

function inaccessible(error: unknown) {
  return error instanceof ApiError && error.status !== undefined && error.status >= 400 && error.status < 500 && ![408, 429].includes(error.status);
}

export function ProcurementReviewPage() {
  const { projectId = "", comparisonId = "" } = useParams();
  const { project } = useOutletContext<ProjectCockpitOutletContext>();
  const [showEvidence, setShowEvidence] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [retryError, setRetryError] = useState<string | null>(null);
  const query = useQuery({ queryKey: ["procurement-review", projectId, comparisonId], queryFn: () => api.getProcurementReview(comparisonId),
    retry: false,
    refetchInterval: (query) => inaccessible(query.state.error) || ["complete", "failed"].includes(query.state.data?.phase ?? "") ? false : query.state.error ? 10000 : 3000,
  }, queryClient);
  const evidence = useQuery({ queryKey: ["procurement-review-evidence", projectId, comparisonId], queryFn: () => api.getProcurementReviewEvidence(comparisonId), enabled: showEvidence }, queryClient);
  const unavailable = inaccessible(query.error);
  const connectionIssue = query.fetchStatus === "paused" || query.errorUpdatedAt > query.dataUpdatedAt;
  const run = unavailable ? undefined : query.data;
  const draft = run?.draft;
  const draftId = draft?.id;
  const sourceFacts = new Map(evidence.data?.documents.flatMap((doc, documentIndex) => doc.facts.map((fact, index) => [String(`f${documentIndex + 1}:${index}`), { ...fact, filename: doc.filename }] as const)) ?? []);
  useEffect(() => {
    if (draftId) void queryClient.invalidateQueries({ queryKey: projectKeys.root(projectId) });
  }, [draftId, projectId]);

  async function retry() {
    setRetrying(true); setRetryError(null);
    try { await api.retryProcurementReview(comparisonId); await query.refetch(); }
    catch { setRetryError("Could not restart the review. Try again."); }
    finally { setRetrying(false); }
  }

  return <section className="min-w-0 space-y-4 p-4 lg:p-6">
    <header className="flex items-center justify-between gap-3">
      <Button variant="ghost" size="sm" asChild><Link to={`/projects/${projectId}?workflow=procurement-requests`}><ArrowLeft className="size-4" aria-hidden />Procurement</Link></Button>
      {draft && <div className="flex items-center gap-2"><DraftDownloadMenu projectId={projectId} draft={draft} /><CopyContentButton loadContent={async () => draft.content_markdown} /></div>}
    </header>
    {draft ? <>
      <DraftReviewPanel projectId={projectId} projectTitle={project?.title} draft={draft} workflowType={draft.workflow_type} onDraftUpdated={() => void query.refetch()} />
      <Button variant="ghost" size="sm" onClick={() => setShowEvidence((value) => !value)} aria-expanded={showEvidence}>{showEvidence ? "Hide" : "View"} source ledger</Button>
      {showEvidence && <div className="space-y-4">
        {evidence.isLoading && <p role="status">Opening source ledger…</p>}
        {evidence.isError && <p role="alert">Could not load the source ledger. <Button variant="link" onClick={() => void evidence.refetch()}>Try again</Button></p>}
        {evidence.data?.review?.selection.matrix.map((row, index) => <details key={index} className="rounded-md border p-3"><summary className="cursor-pointer text-sm font-medium">{row.label} — price sources</summary><ul className="mt-2 space-y-2 text-xs">{row.cells.map((cell) => <li key={cell.quote_id}><strong>{evidence.data?.quotes.find((quote) => quote.id === cell.quote_id)?.name}</strong>{cell.fact_ids.map((id) => { const fact = sourceFacts.get(id); return fact ? <p key={id}>{fact.label}: {fact.amount_printed ?? fact.excerpt} · {fact.filename}, p. {fact.page_no}</p> : null; })}</li>)}</ul></details>)}
        {evidence.data?.documents.map((doc) => <details key={doc.id} className="rounded-md border p-3"><summary className="cursor-pointer text-sm font-medium">{doc.filename} · {doc.page_count} pages</summary><div className="mt-3 overflow-x-auto"><table className="w-full text-left text-xs"><thead><tr><th className="p-2">Page</th><th className="p-2">Item</th><th className="p-2">As printed</th><th className="p-2">Source wording</th></tr></thead><tbody>{doc.facts.map((fact, index) => <tr key={index} className="border-t"><td className="p-2">{fact.page_no}</td><td className="p-2">{fact.label}</td><td className="p-2">{fact.amount_printed ?? "—"}</td><td className="p-2">{fact.excerpt}</td></tr>)}</tbody></table></div></details>)}
      </div>}
    </> : <ProcurementReviewProgress run={run} connectionIssue={connectionIssue} unavailable={unavailable} checking={query.isFetching} lastUpdated={query.dataUpdatedAt} retrying={retrying} retryError={retryError} onCheck={() => void query.refetch()} onRetry={() => void retry()} />}
  </section>;
}
