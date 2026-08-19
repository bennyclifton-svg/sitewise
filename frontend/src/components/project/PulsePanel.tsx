import { Button } from "@/components/ui/button";
import type { PulseAction, PulseFeed, PulseItem } from "@/lib/types/pulse";
import { cn } from "@/lib/utils";

const ACTION_LABEL: Record<PulseAction, string> = {
  review_invoice: "Review invoice",
  classify_document: "Classify",
  view_evidence: "View",
  dismiss: "Dismiss",
};

function attentionHeadline(count: number): string {
  if (count === 0) return "Nothing needs attention";
  if (count === 1) return "1 item needs attention";
  return `${count} items need attention`;
}

function isPulseAction(value: string): value is PulseAction {
  return value in ACTION_LABEL;
}

export function PulsePanel({
  feed,
  onAction,
}: {
  feed: PulseFeed;
  onAction?: (item: PulseItem, action: PulseAction) => void;
}) {
  return (
    <section
      aria-label="Project pulse"
      className="border-b border-[var(--border-hair)] bg-[var(--bg-surface)] px-4 py-3 lg:px-6"
      data-testid="project-pulse"
    >
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="cockpit-eyebrow text-[var(--sw-text-quiet)]">Project Pulse</p>
        <h1 className="font-display text-base font-medium tracking-tight text-[var(--sw-text-primary)]">
          {attentionHeadline(feed.attention_count)}
        </h1>
      </header>

      {feed.attention.length > 0 ? (
        <ol className="mt-3 grid gap-2">
          {feed.attention.map((item, index) => (
            <li
              key={item.id}
              className="grid gap-1 border border-[var(--border-hair)] px-3 py-2"
            >
              <div className="flex min-w-0 items-baseline gap-2">
                <span className="font-mono text-[0.65rem] text-[var(--sw-text-quiet)]">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <span className="font-mono text-[0.65rem] uppercase tracking-[0.14em] text-[var(--sw-text-secondary)]">
                  {item.domain}
                </span>
                <p className="min-w-0 flex-1 text-sm text-[var(--sw-text-primary)]">
                  {item.title}
                </p>
              </div>
              {item.body !== item.title ? (
                <p className="pl-7 text-xs text-[var(--sw-text-secondary)]">{item.body}</p>
              ) : null}
              <div className="flex flex-wrap gap-1 pl-7">
                {item.actions.filter(isPulseAction).map((action) => (
                  <Button
                    key={action}
                    type="button"
                    size="xs"
                    variant={action === "dismiss" ? "ghost" : "outline"}
                    onClick={() => onAction?.(item, action)}
                  >
                    {ACTION_LABEL[action]}
                  </Button>
                ))}
              </div>
            </li>
          ))}
        </ol>
      ) : null}

      {feed.other.map((item) => (
        <p
          key={item.id}
          className={cn(
            "mt-3 text-xs text-[var(--sw-text-secondary)]",
          )}
          data-testid="pulse-other-activity"
        >
          <span className="font-mono uppercase tracking-[0.14em] text-[var(--sw-text-quiet)]">
            Other activity
          </span>
          <span className="mx-2 text-[var(--sw-text-quiet)]">·</span>
          {item.body}
        </p>
      ))}
    </section>
  );
}
