import { FileText } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import type { ArtefactEvent } from "@/lib/chat-events";

type ArtefactCardProps = {
  artefact: ArtefactEvent;
  projectId?: string | null;
};

function artefactHref(artefact: ArtefactEvent, projectId?: string | null): string | null {
  const resolvedProjectId = artefact.projectId ?? projectId;
  if (!resolvedProjectId) return null;
  if (artefact.workflowType === "tender_report" && artefact.comparisonId) {
    return `/projects/${resolvedProjectId}/tender/${artefact.comparisonId}/report`;
  }
  if (artefact.draftId) {
    return `/projects/${resolvedProjectId}`;
  }
  return null;
}

export function ArtefactCard({ artefact, projectId }: ArtefactCardProps) {
  const href = artefactHref(artefact, projectId);

  return (
    <div className="mt-3 flex items-center justify-between gap-3 rounded-md border bg-muted/30 p-3">
      <div className="flex min-w-0 items-center gap-2">
        <FileText className="size-4 shrink-0 text-muted-foreground" aria-hidden />
        <div className="min-w-0">
          <p className="truncate text-sm font-medium">{artefact.title}</p>
          {artefact.workflowType ? (
            <p className="truncate text-xs text-muted-foreground">
              {artefact.workflowType.replaceAll("_", " ")}
            </p>
          ) : null}
        </div>
      </div>
      {href ? (
        <Button asChild size="sm" variant="outline">
          <Link to={href}>Open</Link>
        </Button>
      ) : null}
    </div>
  );
}
