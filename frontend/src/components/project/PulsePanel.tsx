import { Button } from "@/components/ui/button";
import type {
  PulseAction,
  PulseFeed,
  PulseItem,
  PulseSincePreset,
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

const SINCE_PRESETS: { id: PulseSincePreset; label: string }[] = [
  { id: "yesterday", label: "Since yesterday" },
  { id: "7d", label: "Last 7 days" },
  { id: "30d", label: "Last 30 days" },
];

export function attentionHeadline(count: number): string {
  if (count === 0) return "Nothing needs attention";
  if (count === 1) return "1 item needs attention";
  return `${count} items need attention`;
}

function isPulseAction(value: string): value is PulseAction {
  return value in ACTION_LABEL;
}

export function PulsePanel({
  feed,
  sincePreset = "7d",
  onSinceChange,
  onAction,
}: {
  feed: PulseFeed;
  sincePreset?: PulseSincePreset;
  onSinceChange?: (preset: PulseSincePreset) => void;
  onAction?: (item: PulseItem, action: PulseAction) => void;
}) {
  return (
    <section
      aria-label="Project pulse"
      className="border-b border-[var(--border-hair)] px-1.5 py-2"
      data-testid="project-pulse"
    >
      <header className="flex items-baseline justify-between gap-2">
        <h2 className="text-[0.7rem] font-medium text-[var(--sw-text-primary)]">
          {attentionHeadline(feed.attention_count)}
        </h2>
      </header>

      <div
        className="mt-1.5 flex flex-wrap gap-0.5"
        role="group"
        aria-label="Pulse time window"
      >
        {SINCE_PRESETS.map((preset) => (
          <Button
            key={preset.id}
            type="button"
            size="xs"
            variant={sincePreset === preset.id ? "outline" : "ghost"}
            className="h-5 px-1.5 text-[0.65rem]"
            aria-pressed={sincePreset === preset.id}
            onClick={() => onSinceChange?.(preset.id)}
          >
            {preset.label}
          </Button>
        ))}
      </div>

      {feed.attention.length > 0 ? (
        <ol className="mt-2">
          {feed.attention.map((item, index) => (
            <li
              key={item.id}
              className="border-t border-[var(--border-hair)] py-1.5"
            >
              <div className="flex min-w-0 items-baseline gap-1.5">
                <span className="shrink-0 font-mono text-[0.6rem] text-[var(--sw-text-quiet)]">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <span className="shrink-0 font-mono text-[0.6rem] uppercase tracking-[0.12em] text-[var(--sw-text-secondary)]">
                  {item.domain}
                </span>
                <p
                  className="min-w-0 flex-1 truncate text-[0.7rem] text-[var(--sw-text-primary)]"
                  title={item.title}
                >
                  {item.title}
                </p>
              </div>
              {item.body !== item.title ? (
                <p
                  className="mt-0.5 truncate pl-6 text-[0.65rem] text-[var(--sw-text-secondary)]"
                  title={item.body}
                >
                  {item.body}
                </p>
              ) : null}
              <div className="mt-1 flex flex-wrap gap-0.5 pl-6">
                {item.actions.filter(isPulseAction).map((action) => (
                  <Button
                    key={action}
                    type="button"
                    size="xs"
                    variant={action === "dismiss" ? "ghost" : "outline"}
                    className="h-5 px-1.5 text-[0.65rem]"
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
            "mt-2 truncate text-[0.65rem] text-[var(--sw-text-secondary)]",
          )}
          data-testid="pulse-other-activity"
          title={item.body}
        >
          <span className="font-mono uppercase tracking-[0.12em] text-[var(--sw-text-quiet)]">
            Other activity
          </span>
          <span className="mx-1.5 text-[var(--sw-text-quiet)]">·</span>
          {item.body}
        </p>
      ))}
    </section>
  );
}
