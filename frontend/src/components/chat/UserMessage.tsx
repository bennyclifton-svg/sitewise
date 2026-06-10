type UserMessageProps = {
  text: string;
};

export function UserMessage({ text }: UserMessageProps) {
  return (
    <article className="rounded-lg border bg-muted/40 px-4 py-3 text-sm">
      <div className="mb-2 text-xs font-medium tracking-wide text-muted-foreground uppercase">
        You
      </div>
      <p className="whitespace-pre-wrap leading-relaxed">{text}</p>
    </article>
  );
}
