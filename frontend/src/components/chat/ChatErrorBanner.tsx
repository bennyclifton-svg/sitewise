import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import type { ChatErrorKind } from "@/lib/chat-ui";

type ChatErrorBannerProps = {
  message: string;
  kind: ChatErrorKind;
};

export function ChatErrorBanner({ message, kind }: ChatErrorBannerProps) {
  return (
    <div
      className="rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive"
      role="alert"
    >
      <p className="font-medium">{headingForKind(kind)}</p>
      <p className="mt-1">{message}</p>
      {kind === "auth" ? (
        <Button asChild variant="outline" size="sm" className="mt-3">
          <Link to="/login">Sign in again</Link>
        </Button>
      ) : null}
    </div>
  );
}

function headingForKind(kind: ChatErrorKind): string {
  switch (kind) {
    case "auth":
      return "Session expired";
    case "forbidden":
      return "Access denied";
    case "grounding":
      return "Could not verify sources";
    case "retrieval":
      return "Retrieval failed";
    case "rate_limit":
      return "Rate limit reached";
    case "tool":
      return "Tool failed";
    case "partial_pipeline":
      return "Workflow incomplete";
    case "network":
      return "Connection problem";
    default:
      return "Something went wrong";
  }
}
