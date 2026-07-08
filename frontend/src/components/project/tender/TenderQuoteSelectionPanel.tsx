import { AlertCircle, FileCheck2, LoaderCircle } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import type { EvidencePreview } from "@/lib/types/project";

export function TenderQuoteSelectionPanel({
  projectId,
  selectedEvidence,
}: {
  projectId: string;
  selectedEvidence: EvidencePreview[];
}) {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const count = selectedEvidence.length;
  const canSave = count >= 2 && count <= 5 && !isSubmitting;

  async function saveSelection() {
    if (!canSave) return;
    setError(null);
    setIsSubmitting(true);
    try {
      const comparison = await api.createTenderComparisonFromProjectFiles({
        project_id: projectId,
        workspace_paths: selectedEvidence.map((item) => item.relative_path),
      });
      navigate(`/projects/${projectId}/tender/${comparison.id}`);
    } catch (saveError) {
      setError(
        saveError instanceof ApiError
          ? saveError.message
          : "Could not save the selected quotes.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="rounded-md border bg-card shadow-sm">
      <header className="flex flex-wrap items-start justify-between gap-3 border-b px-4 py-3">
        <div className="min-w-0">
          <p className="cockpit-zone-title">Tender intake</p>
          <h2 className="mt-1 text-lg font-semibold tracking-tight">
            Quote selection
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">
            {selectionStatus(count)}
          </p>
        </div>
        <Button type="button" onClick={() => void saveSelection()} disabled={!canSave}>
          {isSubmitting ? (
            <LoaderCircle className="size-4 animate-spin" aria-hidden />
          ) : (
            <FileCheck2 className="size-4" aria-hidden />
          )}
          {isSubmitting ? "Saving" : "Save quote selection"}
        </Button>
      </header>

      {error ? (
        <p className="mx-4 mt-4 flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden />
          <span>{error}</span>
        </p>
      ) : null}

      <div className="p-4">
        {selectedEvidence.length ? (
          <div className="divide-y rounded-md border bg-background">
            {selectedEvidence.map((document, index) => (
              <article
                key={document.id}
                className="grid gap-3 px-3 py-2.5 text-sm md:grid-cols-[5rem_minmax(0,1fr)]"
              >
                <p className="font-medium text-muted-foreground">Quote {index + 1}</p>
                <div className="min-w-0">
                  <p className="truncate font-medium">{document.title}</p>
                  <p className="mt-0.5 truncate text-xs text-muted-foreground">
                    {document.relative_path}
                  </p>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="rounded-md border border-dashed bg-background p-6 text-center">
            <p className="text-sm font-medium">No quote files selected</p>
          </div>
        )}
      </div>
    </section>
  );
}

function selectionStatus(count: number): string {
  if (count === 0) return "Select 2-5 quote files from the repository.";
  if (count === 1) return "1 selected / minimum 2";
  if (count > 5) return `${count} selected / maximum 5`;
  return `${count} selected`;
}
