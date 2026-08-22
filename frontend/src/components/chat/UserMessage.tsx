type UserMessageProps = {
  text: string;
};

export function UserMessage({ text }: UserMessageProps) {
  return (
    <article
      aria-label="Your message"
      className="ml-8 max-w-[88%] self-end rounded-lg border border-border bg-muted px-3 py-2 text-sm"
    >
      <p className="whitespace-pre-wrap leading-relaxed">{text}</p>
    </article>
  );
}
