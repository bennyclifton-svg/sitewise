import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PulsePanel } from "@/components/project/PulsePanel";
import { api } from "@/lib/api";
import type { ProjectEmailRegisterRow } from "@/lib/types/email";
import type { PulseFeed, PulseItem } from "@/lib/types/pulse";

vi.mock("@/lib/api", () => ({
  api: {
    decideInvoice: vi.fn(),
    putDocumentClassification: vi.fn(),
    sendProjectEmailDraft: vi.fn(),
  },
}));

function item(overrides: Partial<PulseItem> = {}): PulseItem {
  return {
    id: "drawing_revision:source_document:doc-1",
    kind: "attention",
    signal_type: "drawing_revision",
    title: "S203 Rev C supersedes Rev B",
    body: "S203 Rev C supersedes Rev B",
    domain: "STRUCTURE",
    evidence: [
      {
        reference_type: "source_document",
        reference_id: "doc-1",
        label: "S203.pdf",
      },
    ],
    actions: ["view_evidence", "dismiss"],
    created_at: "2026-08-19T00:00:00Z",
    ...overrides,
  };
}

function feed(overrides: Partial<PulseFeed> = {}): PulseFeed {
  const attention = overrides.attention ?? [item()];
  return {
    attention,
    other: [
      {
        id: "other:rollup",
        kind: "other",
        signal_type: null,
        title: "Other activity",
        body: "48 emails · 26 documents · 12 events",
        domain: "ACTIVITY",
        evidence: [],
        actions: [],
        created_at: "2026-08-19T00:00:00Z",
      },
    ],
    attention_count: attention.length,
    generated_at: "2026-08-19T00:00:00Z",
    since: "2026-08-12T00:00:00Z",
    ...overrides,
  };
}

function emailRow(
  overrides: Partial<ProjectEmailRegisterRow> = {},
): ProjectEmailRegisterRow {
  return {
    id: "mail-1",
    kind: "inbound",
    direction: "in",
    subject: "RFI-12 slab thickness",
    party: "qs@consultant.com",
    sent_at: "2026-08-14T00:00:00Z",
    message_category: "rfi",
    status: null,
    email_id: "mail-1",
    draft_id: null,
    ...overrides,
  };
}

describe("PulsePanel", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("renders the correspondence register instead of a time-window headline", () => {
    render(
      <PulsePanel
        feed={feed({ attention: [], attention_count: 0 })}
        emails={[
          emailRow(),
          emailRow({
            id: "draft-1",
            kind: "outbound",
            direction: "out",
            subject: "Re: RFI-12 slab thickness",
            party: "qs@consultant.com",
            sent_at: "2026-08-15T09:00:00Z",
            message_category: null,
            status: "sent",
            email_id: "mail-1",
            draft_id: "draft-1",
          }),
        ]}
      />,
    );

    expect(screen.getByRole("columnheader", { name: "Date" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Subject" })).toBeInTheDocument();
    expect(screen.getByText("RFI-12 slab thickness")).toBeInTheDocument();
    expect(screen.getByText("Re: RFI-12 slab thickness")).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Direction" })).toBeInTheDocument();
    expect(screen.getByText("In")).toBeInTheDocument();
    expect(screen.getByText("Out")).toBeInTheDocument();
    expect(screen.getByText("RFI")).toBeInTheDocument();
    expect(screen.queryByText("Nothing needs attention")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Last 7 days" })).not.toBeInTheDocument();
    expect(screen.queryByText("48 emails · 26 documents · 12 events")).not.toBeInTheDocument();
  });

  it("shows an empty register when there is no mail", () => {
    render(<PulsePanel feed={feed({ attention: [], attention_count: 0 })} emails={[]} />);
    expect(screen.getByText("No correspondence")).toBeInTheDocument();
  });

  it("slots non-email attention into the same register", async () => {
    const user = userEvent.setup();
    const onAction = vi.fn();
    render(
      <PulsePanel
        feed={feed({
          attention: [
            item({
              id: "potential_cost_change:cost_invoice:inv-1:ready_for_review",
              signal_type: "potential_cost_change",
              title: "Builder Invoice 009 includes $8,400 against an unapproved variation",
              domain: "COMMERCIAL",
              evidence: [
                {
                  reference_type: "cost_invoice",
                  reference_id: "inv-1",
                  label: "Builder 009",
                },
              ],
              actions: ["review_invoice", "dismiss"],
            }),
          ],
        })}
        emails={[emailRow()]}
        onAction={onAction}
      />,
    );

    expect(
      screen.getByText(
        "Builder Invoice 009 includes $8,400 against an unapproved variation",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("COMMERCIAL")).toBeInTheDocument();

    await user.click(
      screen.getByText(
        "Builder Invoice 009 includes $8,400 against an unapproved variation",
      ),
    );
    expect(onAction).toHaveBeenCalledWith(
      expect.objectContaining({
        actions: expect.arrayContaining(["review_invoice"]),
      }),
      "review_invoice",
    );
    expect(api.decideInvoice).not.toHaveBeenCalled();
  });

  it("selects a mail row without sending", async () => {
    const user = userEvent.setup();
    const onSelectEmail = vi.fn();
    render(
      <PulsePanel
        feed={feed({ attention: [], attention_count: 0 })}
        emails={[emailRow()]}
        onSelectEmail={onSelectEmail}
      />,
    );

    await user.click(screen.getByText("RFI-12 slab thickness"));
    expect(onSelectEmail).toHaveBeenCalledWith(
      expect.objectContaining({ email_id: "mail-1", direction: "in" }),
    );
    expect(api.sendProjectEmailDraft).not.toHaveBeenCalled();
  });
});
