type StreamingIndicatorProps = {
  message?: string | null;
};

export function StreamingIndicator({ message }: StreamingIndicatorProps) {
  const label = message?.trim() ? message : "Clerk is writing…";
  return (
    <div
      className="mr-8 flex max-w-[92%] items-center gap-2 self-start text-sm text-muted-foreground"
      role="status"
      aria-live="polite"
    >
      <span className="inline-flex gap-1" aria-hidden>
        <span className="size-1.5 animate-pulse rounded-full bg-muted-foreground/70 [animation-delay:0ms]" />
        <span className="size-1.5 animate-pulse rounded-full bg-muted-foreground/70 [animation-delay:150ms]" />
        <span className="size-1.5 animate-pulse rounded-full bg-muted-foreground/70 [animation-delay:300ms]" />
      </span>
      {label}
    </div>
  );
}
