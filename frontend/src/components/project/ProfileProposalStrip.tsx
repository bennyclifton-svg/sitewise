import { useState } from "react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import type { ProjectProfileProposal } from "@/lib/types/project";

function formatProposedValues(values: Record<string, unknown>): string {
  return Object.entries(values)
    .filter(([key]) => key === "client" || key === "site_address")
    .map(([key, value]) => {
      const label = key === "site_address" ? "Site address" : "Client";
      return `${label}: ${String(value)}`;
    })
    .join(" · ");
}

export function ProfileProposalStrip({
  projectId,
  proposals,
  onResolved,
}: {
  projectId: string;
  proposals: ProjectProfileProposal[];
  onResolved: () => void;
}) {
  const pending = proposals.filter((item) => item.state === "pending");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!pending.length) {
    return null;
  }

  async function resolve(
    proposal: ProjectProfileProposal,
    action: "accept" | "reject",
  ) {
    setBusyId(proposal.id);
    setError(null);
    try {
      if (action === "accept") {
        await api.acceptProfileProposal(
          projectId,
          proposal.id,
          proposal.profile_revision,
        );
      } else {
        await api.rejectProfileProposal(
          projectId,
          proposal.id,
          proposal.profile_revision,
        );
      }
      onResolved();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Could not resolve profile proposal.",
      );
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      {pending.map((proposal) => {
        const summary = formatProposedValues(proposal.proposed_values);
        if (!summary) {
          return null;
        }
        const busy = busyId === proposal.id;
        return (
          <div
            key={proposal.id}
            className="flex flex-col gap-3 rounded-lg border border-amber-200 bg-amber-50/70 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
          >
            <div className="min-w-0 space-y-1">
              <p className="text-sm font-medium text-foreground">
                Confirm project identity from documents
              </p>
              <p className="text-sm text-muted-foreground">{summary}</p>
              {proposal.confidence != null ? (
                <p className="text-xs text-muted-foreground">
                  Confidence {(proposal.confidence * 100).toFixed(0)}%
                  {proposal.proposer ? ` · ${proposal.proposer}` : ""}
                </p>
              ) : null}
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={busy}
                onClick={() => void resolve(proposal, "reject")}
              >
                Reject
              </Button>
              <Button
                type="button"
                size="sm"
                disabled={busy}
                onClick={() => void resolve(proposal, "accept")}
              >
                Accept
              </Button>
            </div>
          </div>
        );
      })}
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
    </div>
  );
}
