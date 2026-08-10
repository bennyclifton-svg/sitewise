import type { UIMessage } from "ai";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AssistantMessage } from "@/components/chat/AssistantMessage";

const message: UIMessage = {
  id: "message-1",
  role: "assistant",
  parts: [{ type: "text", text: "Tender review complete." }],
};

describe("AssistantMessage", () => {
  beforeEach(() => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });
  });

  it("copies the response text from the hover copy control", async () => {
    render(
      <MemoryRouter>
        <AssistantMessage
          message={message}
          selectedCitationId={null}
          onSelectCitation={vi.fn()}
        />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Copy response" }));

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        "Tender review complete.",
      );
    });
    expect(screen.getByRole("button", { name: "Copied" })).toBeInTheDocument();
  });

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
    expect(screen.getByLabelText("Tool activity")).toHaveTextContent(
      "Listed tender comparisons",
    );
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
    expect(trace).toHaveTextContent("SiteWise knowledge");
    expect(trace).toHaveTextContent("1 tool used");
    expect(trace).toHaveTextContent("LLM reasoning");
  });

  it("shows a globe trace and citation only after an official web source was read", () => {
    render(
      <MemoryRouter>
        <AssistantMessage
          message={message}
          messageData={{
            agent: {
              runtime: "pi",
              sourceTrace: {
                context: { used: true },
                web: {
                  used: true,
                  tools: ["search_web", "read_web_source"],
                  sources: [
                    {
                      url: "https://www.legislation.qld.gov.au/current-act",
                      title: "Planning Act 2016",
                      publisher: "Queensland Government",
                      jurisdiction: "QLD",
                      authority_class: "official_legislation",
                      source_type: "web_legislation",
                      version_status: "current",
                      effective_date: "29 November 2024",
                      section: "section 8",
                      excerpt: "A planning instrument sets out policies.",
                      content_hash: "abc123",
                      retrieved_at: "2026-08-08T10:00:00+00:00",
                    },
                  ],
                },
                tools: [
                  { name: "search_web" },
                  { name: "read_web_source" },
                ],
                model: { used: true },
              },
            },
          }}
          agentMode
          selectedCitationId={null}
          onSelectCitation={vi.fn()}
        />
      </MemoryRouter>,
    );

    expect(screen.getByLabelText("Internet source")).toBeInTheDocument();
    expect(screen.getByLabelText("Answer trace")).toHaveTextContent("Web source");
    expect(
      screen.getByRole("button", { name: "Citation 1: Planning Act 2016" }),
    ).toBeInTheDocument();
  });

  it("shows an internet-search globe when search informed the answer but source read failed", () => {
    render(
      <MemoryRouter>
        <AssistantMessage
          message={message}
          toolEvents={[
            {
              kind: "tool",
              tool: "search_web",
              state: "done",
              message: "Searched official web sources",
            },
            {
              kind: "tool",
              tool: "read_web_source",
              state: "error",
              message: "Official web source read failed",
            },
          ]}
          agentMode
          selectedCitationId={null}
          onSelectCitation={vi.fn()}
        />
      </MemoryRouter>,
    );

    expect(screen.getByLabelText("Internet source")).toBeInTheDocument();
    expect(screen.getByLabelText("Answer trace")).toHaveTextContent(
      "Internet search",
    );
    expect(screen.queryByText("Web source")).not.toBeInTheDocument();
  });

  it("does not show a globe while an internet search is still running", () => {
    render(
      <MemoryRouter>
        <AssistantMessage
          message={message}
          toolEvents={[
            {
              kind: "tool",
              tool: "search_web",
              state: "running",
              message: "Searching official web sources",
            },
          ]}
          agentMode
          selectedCitationId={null}
          onSelectCitation={vi.fn()}
        />
      </MemoryRouter>,
    );

    expect(screen.queryByLabelText("Internet source")).not.toBeInTheDocument();
  });
});
