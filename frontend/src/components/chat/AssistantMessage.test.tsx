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

  it("dedupes citations with the same sourceId", () => {
    const duplicateSourceId =
      "reference:seed/program-scheduling-guide.md#chunk=879de2d7-809b-5cc1-bce2-1ad27e5966d8";

    render(
      <MemoryRouter>
        <AssistantMessage
          message={message}
          messageData={{
            citations: [
              {
                sourceId: duplicateSourceId,
                chunkId: duplicateSourceId,
                documentId: "program-scheduling-guide.md",
                title: "Program scheduling guide",
                excerpt: "First excerpt",
              },
              {
                sourceId: duplicateSourceId,
                chunkId: duplicateSourceId,
                documentId: "program-scheduling-guide.md",
                title: "Program scheduling guide",
                excerpt: "Second excerpt",
              },
            ],
          }}
          selectedCitationId={null}
          onSelectCitation={vi.fn()}
        />
      </MemoryRouter>,
    );

    expect(
      screen.getAllByRole("button", { name: "Citation 1: Program scheduling guide" }),
    ).toHaveLength(1);
  });

  it("renders a subtle answer trace for project context, knowledge, tools, and model reasoning", () => {
    render(
      <MemoryRouter>
        <AssistantMessage
          message={message}
          messageData={{
            agent: {
              runtime: "pi",
              sourceTrace: {
                context: { used: true },
                documents: { used: false, tools: [] },
                knowledge: {
                  used: true,
                  tools: ["read_platform_knowledge"],
                  references: ["seed/nsw/residential-refurb.md"],
                },
                tools: [
                  {
                    name: "read_platform_knowledge",
                    knowledgePath: "seed/nsw/residential-refurb.md",
                  },
                ],
                model: { used: true },
              },
            },
          }}
          toolEvents={[
            {
              kind: "tool",
              tool: "read_platform_knowledge",
              state: "done",
              message: "Read platform knowledge",
              knowledgePath: "seed/nsw/residential-refurb.md",
            },
          ]}
          agentMode
          selectedCitationId={null}
          onSelectCitation={vi.fn()}
        />
      </MemoryRouter>,
    );

    const trace = screen.getByLabelText("Answer trace");
    expect(trace).toHaveTextContent("Project context");
    expect(trace).toHaveTextContent("Clerk knowledge");
    expect(trace).toHaveTextContent("1 tool used");
    expect(trace).toHaveTextContent("LLM reasoning");
  });
});
