import { useEffect, useMemo, useRef } from "react";

import { api } from "@/lib/api";
import type { ProjectProfileProposal } from "@/lib/types/project";

function isIdentityProposal(proposal: ProjectProfileProposal): boolean {
  const fields = Object.keys(proposal.proposed_values);
  return (
    fields.length > 0 &&
    fields.every((field) => field === "client" || field === "site_address")
  );
}

/** Resolves legacy identity proposals without interrupting the project workspace. */
export function ProfileProposalStrip({
  projectId,
  proposals,
  onResolved,
}: {
  projectId: string;
  proposals: ProjectProfileProposal[];
  onResolved: () => void;
}) {
  const attempted = useRef(new Set<string>());
  const pending = useMemo(
    () =>
      proposals.filter(
        (proposal) => proposal.state === "pending" && isIdentityProposal(proposal),
      ),
    [proposals],
  );
  const pendingKey = pending
    .map((proposal) => `${proposal.id}:${proposal.profile_revision}`)
    .join("|");

  useEffect(() => {
    const unresolved = pending.filter((proposal) => !attempted.current.has(proposal.id));
    if (!unresolved.length) return;

    for (const proposal of unresolved) attempted.current.add(proposal.id);
    void Promise.allSettled(
      unresolved.map((proposal) =>
        api.acceptProfileProposal(
          projectId,
          proposal.id,
          proposal.profile_revision,
        ),
      ),
    ).then((results) => {
      if (results.some((result) => result.status === "fulfilled")) onResolved();
    });
  }, [onResolved, pending, pendingKey, projectId]);

  return null;
}
