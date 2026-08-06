import { cn } from "@/lib/utils";

type StreamingIndicatorProps = {
  message?: string | null;
  /** Overrides the chat bubble layout when reused outside the message list. */
  className?: string;
};

const TRACE_POINT_DELAYS = ["0ms", "90ms", "180ms", "270ms", "360ms", "450ms"];

export function StreamingIndicator({ message, className }: StreamingIndicatorProps) {
  const label = message?.trim() ? message : "Pi is writing…";

  return (
    <div
      className={cn(
        "flex items-center gap-2.5 text-sm text-muted-foreground",
        className ?? "mr-8 max-w-[92%] self-start",
      )}
      role="status"
      aria-live="polite"
    >
      <span className="streaming-trace" aria-hidden="true">
        {TRACE_POINT_DELAYS.map((animationDelay) => (
          <span
            className="streaming-trace__point"
            key={animationDelay}
            style={{ animationDelay }}
          />
        ))}
      </span>
      <span>{label}</span>
    </div>
  );
}
