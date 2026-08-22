import { CopyContentButton } from "@/components/project/CopyContentButton";
import type { ProjectEmailRegisterRow } from "@/lib/types/email";
import type {
  PulseAction,
  PulseFeed,
  PulseItem,
} from "@/lib/types/pulse";
import { cn } from "@/lib/utils";

const ACTION_LABEL: Record<PulseAction, string> = {
  review_invoice: "Review invoice",
  classify_document: "Classify",
  view_evidence: "View",
  dismiss: "Dismiss",
  draft_reply: "Draft reply",
  view_thread: "View thread",
};

const CATEGORY_LABEL: Record<string, string> = {
  action_required: "Action",
  decision_required: "Decision",
  design_change: "Design",
  rfi: "RFI",
  instruction: "Instr.",
  programme_change: "Prog.",
  document_transmittal: "Tx",
  approval: "Approval",
  invoice_notice: "Invoice",
  fee_proposal: "Fee",
  tender_submission: "Tender",
  meeting: "Meeting",
  information_only: "Info",
  unknown: "—",
};

type RegisterLine = {
  id: string;
  dateLabel: string;
  subject: string;
  direction: "in" | "out" | null;
  category: string;
  attention: boolean;
  email: ProjectEmailRegisterRow | null;
  item: PulseItem | null;
};

export function attentionHeadline(count: number): string {
  if (count === 0) return "Nothing needs attention";
  if (count === 1) return "1 item needs attention";
  return `${count} items need attention`;
}

function isPulseAction(value: string): value is PulseAction {
  return value in ACTION_LABEL;
}

function primaryPulseAction(item: PulseItem): PulseAction | null {
  return item.actions.find(isPulseAction) ?? null;
}

function attentionEmailIds(feed: PulseFeed): Set<string> {
  const ids = new Set<string>();
  for (const item of feed.attention) {
    for (const ref of item.evidence) {
      if (ref.reference_type === "email") ids.add(ref.reference_id);
    }
  }
  return ids;
}

function shortDate(value: string | null | undefined): string {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  return new Intl.DateTimeFormat("en-AU", {
    day: "numeric",
    month: "short",
  }).format(parsed);
}

function categoryLabel(value: string | null | undefined): string {
  if (!value) return "—";
  return CATEGORY_LABEL[value] ?? value;
}

export function PulsePanel({
  feed,
  emails = [],
  selectedEmailId = null,
  inboundAddress = null,
  onSelectEmail,
  onAction,
}: {
  feed: PulseFeed;
  emails?: ProjectEmailRegisterRow[];
  selectedEmailId?: string | null;
  inboundAddress?: string | null;
  onSelectEmail?: (row: ProjectEmailRegisterRow) => void;
  onAction?: (item: PulseItem, action: PulseAction) => void;
}) {
  const flagged = attentionEmailIds(feed);
  const emailLines: RegisterLine[] = emails.map((email) => ({
    id: email.id,
    dateLabel: shortDate(email.sent_at),
    subject: email.subject,
    direction: email.direction,
    category:
      email.status === "draft"
        ? "Draft"
        : email.status === "send_failed"
          ? "Failed"
          : categoryLabel(email.message_category),
    attention: Boolean(email.email_id && flagged.has(email.email_id)),
    email,
    item: null,
  }));
  const covered = new Set(
    emails.flatMap((email) => (email.email_id ? [email.email_id] : [])),
  );
  const attentionLines: RegisterLine[] = feed.attention
    .filter((item) => {
      const emailId = item.evidence.find((ref) => ref.reference_type === "email")
        ?.reference_id;
      return !emailId || !covered.has(emailId);
    })
    .map((item) => ({
      id: item.id,
      dateLabel: shortDate(item.created_at),
      subject: item.title,
      direction: null,
      category: item.domain,
      attention: true,
      email: null,
      item,
    }));
  const lines = [...attentionLines, ...emailLines];

  return (
    <section
      aria-label="Correspondence"
      className="border-b border-[var(--border-hair)]"
      data-testid="project-pulse"
    >
      {inboundAddress ? (
        <div
          className="flex min-w-0 items-center gap-1 border-b border-[var(--border-hair)] px-1.5 py-1"
          data-testid="pulse-inbound-address"
        >
          <span className="shrink-0 text-[0.6rem] font-mono uppercase tracking-[0.12em] text-[var(--sw-text-quiet)]">
            Send to
          </span>
          <span
            className="min-w-0 flex-1 truncate font-mono text-[0.65rem] text-[var(--sw-text)]"
            title={inboundAddress}
          >
            {inboundAddress}
          </span>
          <CopyContentButton
            content={inboundAddress}
            label="Copy project email address"
          />
        </div>
      ) : null}
      <table className="w-full min-w-0 table-fixed border-collapse text-left text-[0.7rem]">
        <colgroup>
          <col className="w-[3.25rem]" />
          <col />
          <col className="w-[2.25rem]" />
          <col className="w-[4.5rem]" />
        </colgroup>
        <thead className="border-b bg-[var(--sw-panel)]">
          <tr className="text-muted-foreground">
            <th className="px-0.5 py-2 font-medium">Date</th>
            <th className="min-w-0 px-1 py-2 font-medium">Subject</th>
            <th className="px-0.5 py-2 font-medium" aria-label="Direction">
              In/Out
            </th>
            <th className="px-0.5 py-2 font-medium" aria-label="Category">
              Cat
            </th>
          </tr>
        </thead>
        <tbody>
          {lines.length ? (
            lines.map((line) => {
              const selected = Boolean(
                selectedEmailId &&
                  (line.id === selectedEmailId ||
                    line.email?.email_id === selectedEmailId ||
                    line.email?.draft_id === selectedEmailId),
              );
              return (
                <tr
                  key={line.id}
                  className={cn(
                    "sw-table-row cursor-pointer select-none border-b text-muted-foreground hover:text-foreground",
                    selected && "sw-table-row--active",
                    line.attention && !selected && "sw-table-row--accent",
                  )}
                  onClick={() => {
                    if (line.email) {
                      onSelectEmail?.(line.email);
                      return;
                    }
                    if (!line.item) return;
                    const action = primaryPulseAction(line.item);
                    if (action) onAction?.(line.item, action);
                  }}
                >
                  <td className="truncate px-0.5 py-2 tabular-nums">
                    {line.dateLabel}
                  </td>
                  <td className="max-w-0 min-w-0 px-1 py-2 font-medium">
                    <span className="block truncate" title={line.subject}>
                      {line.subject}
                    </span>
                  </td>
                  <td className="truncate px-0.5 py-2">
                    {line.direction === "in"
                      ? "In"
                      : line.direction === "out"
                        ? "Out"
                        : "—"}
                  </td>
                  <td className="truncate px-0.5 py-2" title={line.category}>
                    {line.category || "—"}
                  </td>
                </tr>
              );
            })
          ) : (
            <tr className="text-muted-foreground">
              <td className="px-0.5 py-2 tabular-nums">—</td>
              <td className="px-1 py-2">No correspondence</td>
              <td className="px-0.5 py-2">—</td>
              <td className="px-0.5 py-2">—</td>
            </tr>
          )}
        </tbody>
      </table>
    </section>
  );
}
