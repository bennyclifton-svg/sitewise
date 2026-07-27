import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProfileProposalStrip } from "@/components/project/ProfileProposalStrip";
import type { ProjectProfileProposal } from "@/lib/types/project";

const acceptProfileProposal = vi.fn();
const rejectProfileProposal = vi.fn();

vi.mock("@/lib/api", () => ({
  api: {
    acceptProfileProposal: (...args: unknown[]) =>
      acceptProfileProposal(...args),
    rejectProfileProposal: (...args: unknown[]) =>
      rejectProfileProposal(...args),
  },
}));

function proposal(
  overrides: Partial<ProjectProfileProposal> = {},
): ProjectProfileProposal {
  return {
    id: "prop-1",
    project_id: "proj-1",
    profile_revision: 2,
    current_values: {},
    proposed_values: {
      client: "Atelier North for David & Emma Walsh",
    },
    evidence_references: [],
    confidence: 0.55,
    state: "pending",
    proposer: "ingest",
    resolver_source: null,
    created_at: "2026-07-21T00:00:00Z",
    updated_at: "2026-07-21T00:00:00Z",
    resolved_at: null,
    ...overrides,
  };
}

describe("ProfileProposalStrip", () => {
  beforeEach(() => {
    acceptProfileProposal.mockReset();
    rejectProfileProposal.mockReset();
    acceptProfileProposal.mockResolvedValue({ proposal: proposal(), profile_change: null });
    rejectProfileProposal.mockResolvedValue({ proposal: proposal({ state: "rejected" }), profile_change: null });
  });

  it("renders pending identity proposals and accepts them", async () => {
    const user = userEvent.setup();
    const onResolved = vi.fn();
    render(
      <ProfileProposalStrip
        projectId="proj-1"
        proposals={[proposal()]}
        onResolved={onResolved}
      />,
    );

    expect(
      screen.getByText(/Confirm project identity from documents/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Client: Atelier North for David & Emma Walsh/i),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Accept" }));
    expect(acceptProfileProposal).toHaveBeenCalledWith("proj-1", "prop-1", 2);
    expect(onResolved).toHaveBeenCalled();
  });
});
