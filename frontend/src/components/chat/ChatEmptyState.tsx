type ChatEmptyStateProps = {
  variant: "thread" | "first-time";
};

const suggestions = [
  "What projects are in the corpus?",
  "Summarise the procurement strategy for Block B.",
  "What does the contract say about variations?",
];

export function ChatEmptyState({ variant }: ChatEmptyStateProps) {
  if (variant === "first-time") {
    return (
      <div className="rounded-lg border border-dashed px-6 py-8 text-center">
        <h2 className="text-lg font-semibold">Welcome to Clerk</h2>
        <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
          Ask questions about your project documents. Every factual answer includes
          citations you can verify without leaving the app.
        </p>
        <ul className="mx-auto mt-4 max-w-md space-y-1 text-left text-sm text-muted-foreground">
          {suggestions.map((suggestion) => (
            <li key={suggestion} className="list-inside list-disc">
              {suggestion}
            </li>
          ))}
        </ul>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-dashed px-6 py-8 text-center">
      <h2 className="text-base font-semibold">Start the conversation</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        Ask about contracts, reports, specifications, or programme documents. Clerk
        cites project evidence, doctrine, and reference guides.
      </p>
    </div>
  );
}
