import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PulsePanel } from "@/components/project/PulsePanel";
import { api } from "@/lib/api";
import type { PulseFeed, PulseItem, PulseSincePreset } from "@/lib/types/pulse";

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
  const attention = overrides.attention ?? [
    item(),
    item({
      id: "potential_cost_change:cost_invoice:inv-1:ready_for_review",
      signal_type: "potential_cost_change",
      title: "Builder Invoice 009 includes $8,400 against an unapproved variation",
      body: "Builder Invoice 009 includes $8,400 against an unapproved variation",
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
  ];
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

describe("PulsePanel", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("test_pulse_does_not_headline_raw_event_counts", () => {
    render(<PulsePanel feed={feed({ attention_count: 3 })} />);
    const heading = screen.getByRole("heading", { level: 2 });
    expect(heading).toHaveTextContent("3 items need attention");
    expect(heading).not.toHaveTextContent("48");
    expect(heading).not.toHaveTextContent("26 documents");
    expect(heading).not.toHaveTextContent("12 events");
    expect(screen.getByTestId("pulse-other-activity")).toHaveTextContent(
      "48 emails · 26 documents · 12 events",
    );
  });

  it("labels the since window in product language", async () => {
    const user = userEvent.setup();
    const onSinceChange = vi.fn();
    render(
      <PulsePanel
        feed={feed()}
        sincePreset={"7d" as PulseSincePreset}
        onSinceChange={onSinceChange}
      />,
    );

    expect(screen.getByRole("button", { name: "Last 7 days" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await user.click(screen.getByRole("button", { name: "Since yesterday" }));
    expect(onSinceChange).toHaveBeenCalledWith("yesterday");
    await user.click(screen.getByRole("button", { name: "Last 30 days" }));
    expect(onSinceChange).toHaveBeenCalledWith("30d");
  });

  it("test_review_invoice_action_is_a_button_not_inline_logic", async () => {
    const user = userEvent.setup();
    const onAction = vi.fn();
    render(<PulsePanel feed={feed()} onAction={onAction} />);

    await user.click(screen.getByRole("button", { name: "Review invoice" }));

    expect(onAction).toHaveBeenCalledTimes(1);
    expect(onAction.mock.calls[0]?.[1]).toBe("review_invoice");
    expect(onAction.mock.calls[0]?.[0].evidence[0]?.reference_id).toBe("inv-1");
    expect(api.decideInvoice).not.toHaveBeenCalled();
  });

  it("clicking Review invoice selects the invoice id and does not fire hold/reject/approve", async () => {
    const user = userEvent.setup();
    const onAction = vi.fn();
    render(<PulsePanel feed={feed()} onAction={onAction} />);
    await user.click(screen.getByRole("button", { name: "Review invoice" }));
    expect(onAction).toHaveBeenCalledWith(
      expect.objectContaining({
        actions: expect.arrayContaining(["review_invoice"]),
      }),
      "review_invoice",
    );
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Hold" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reject" })).not.toBeInTheDocument();
    expect(api.decideInvoice).not.toHaveBeenCalled();
  });

  it("test_draft_reply_action_does_not_send", async () => {
    const user = userEvent.setup();
    const onAction = vi.fn();
    render(
      <PulsePanel
        feed={feed({
          attention: [
            item({
              id: "unanswered_correspondence:email:mail-1",
              signal_type: "unanswered_correspondence",
              title: "Unanswered RFI: slab thickness",
              body: "Unanswered RFI: slab thickness",
              domain: "CORRESPONDENCE",
              evidence: [
                {
                  reference_type: "email",
                  reference_id: "mail-1",
                  label: "RFI-12",
                },
              ],
              actions: ["draft_reply", "view_thread", "dismiss"],
            }),
          ],
        })}
        onAction={onAction}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Draft reply" }));

    expect(onAction).toHaveBeenCalledWith(
      expect.objectContaining({
        actions: expect.arrayContaining(["draft_reply"]),
      }),
      "draft_reply",
    );
    expect(api.sendProjectEmailDraft).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: "Send" })).not.toBeInTheDocument();
  });
});
