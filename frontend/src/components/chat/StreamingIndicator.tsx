type StreamingIndicatorProps = {
  message?: string | null;
};

const TRACE_POINT_DELAYS = ["0ms", "90ms", "180ms", "270ms", "360ms", "450ms"];

export function StreamingIndicator({ message }: StreamingIndicatorProps) {
  const label = message?.trim() ? message : "Clerk is writing…";

  return (
    <div
      className="mr-8 flex max-w-[92%] items-center gap-2.5 self-start text-sm text-muted-foreground"
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
