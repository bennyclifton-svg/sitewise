import type { UIMessage } from "ai";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AssistantMessage } from "@/components/chat/AssistantMessage";

const message: UIMessage = {
  id: "message-1",
  role: "assistant",
  parts: [{ type: "text", text: "Tender review complete." }],
};

describe("AssistantMessage", () => {
  it("renders text, tool chips, artefacts, and citations", () => {
    render(
      <MemoryRouter>
        <AssistantMessage
          message={message}
          messageData={{
            citations: [
              {
                sourceId: "source-1",
                chunkId: "chunk-1",
                documentId: "document-1",
                title: "Quote A.pdf",
                excerpt: "Tender excerpt",
              },
            ],
          }}
          toolEvents={[
            {
              kind: "tool",
              tool: "list_tender_comparisons",
              state: "done",
              message: "Listed tender comparisons",
            },
          ]}
          artefacts={[
            {
              kind: "artefact",
              workflowType: "tender_report",
              comparisonId: "comparison-1",
              draftId: "draft-1",
              title: "Tender comparison report",
            },
          ]}
          projectId="project-1"
          selectedCitationId={null}
          onSelectCitation={vi.fn()}
        />
      </MemoryRouter>,
    );

    expect(screen.getByText("Tender review complete.")).toBeInTheDocument();
    expect(screen.getByText("list_tender_comparisons")).toBeInTheDocument();
    expect(screen.getByText("Tender comparison report")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Citation 1: Quote A.pdf" })).toBeInTheDocument();
  });
});
