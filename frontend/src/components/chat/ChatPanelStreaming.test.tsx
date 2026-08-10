import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ChatPanel } from "@/components/chat/ChatPanel";

// This suite deliberately uses the real `useChat` + `DefaultChatTransport`
// (ChatPanel.test.tsx mocks them) so that per-delta React updates are
// exercised. A long answer used to abort at part 50 with "Maximum update
// depth exceeded" because the pin-to-bottom effect called setState on every
// delta while the fiber already had pending work from the message store.
vi.mock("@/lib/auth", () => ({
  getAccessToken: vi.fn().mockResolvedValue("test-token"),
}));

vi.mock("@/lib/api", () => ({
  api: { cancelAgentTurn: vi.fn() },
}));

vi.mock("@/lib/queries/agent-configuration", () => ({
  useAgentConfiguration: () => ({
    data: {
      agent: {
        agent_runtime_enabled: false,
        default_model: "openai:gpt-5.6-terra",
        models: [],
      },
      legacy: { default_model: "gpt-5.6-luna", models: [] },
    },
    isPending: false,
    error: null,
  }),
}));

const DELTA_COUNT = 400;

function uiMessageStreamBody(deltaCount: number): string {
  const lines: string[] = [];
  const push = (part: unknown) => lines.push(`data: ${JSON.stringify(part)}\n\n`);
  push({ type: "start" });
  push({ type: "start-step" });
  push({ type: "text-start", id: "t1" });
  for (let index = 0; index < deltaCount; index += 1) {
    push({ type: "text-delta", id: "t1", delta: `chunk ${index} ` });
    if (index % 10 === 0) {
      push({
        type: "data-clerk-status",
        data: {
          kind: "tool",
          tool: "search_documents",
          state: "running",
          message: `searching ${index}`,
        },
      });
    }
  }
  push({ type: "text-end", id: "t1" });
  push({ type: "finish-step" });
  push({ type: "finish" });
  lines.push("data: [DONE]\n\n");
  return lines.join("");
}

describe("ChatPanel long answer streaming", () => {
  it("sends the selected document-register rows with an agent message", async () => {
    const fetchMock = vi.fn<
      (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
    >(
      async () =>
        new Response(new TextEncoder().encode(uiMessageStreamBody(1)), {
          status: 200,
          headers: { "content-type": "text/event-stream" },
        }),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(
      <ChatPanel
        threadId="thread-1"
        initialMessages={[]}
        agentMode
        projectId="project-1"
        layout="main"
        selectedDocumentIds={["document-1", "document-2"]}
      />,
    );

    fireEvent.change(screen.getByLabelText("Message"), {
      target: { value: "Create a transmittal with the selected files" },
    });
    fireEvent.click(screen.getByLabelText("Ask SiteWise"));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());

    const request = fetchMock.mock.calls[0]?.[1];
    expect(request).toBeDefined();
    expect(JSON.parse(String(request?.body))).toMatchObject({
      thread_id: "thread-1",
      selected_document_ids: ["document-1", "document-2"],
    });
  });

  it("uses documents selected after the chat initially mounts", async () => {
    const fetchMock = vi.fn<
      (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
    >(
      async () =>
        new Response(new TextEncoder().encode(uiMessageStreamBody(1)), {
          status: 200,
          headers: { "content-type": "text/event-stream" },
        }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const { rerender } = render(
      <ChatPanel
        threadId="thread-1"
        initialMessages={[]}
        agentMode
        projectId="project-1"
        layout="main"
        selectedDocumentIds={[]}
      />,
    );

    rerender(
      <ChatPanel
        threadId="thread-1"
        initialMessages={[]}
        agentMode
        projectId="project-1"
        layout="main"
        selectedDocumentIds={["document-1", "document-2"]}
      />,
    );

    fireEvent.change(screen.getByLabelText("Message"), {
      target: { value: "Create a transmittal with the selected files" },
    });
    fireEvent.click(screen.getByLabelText("Ask SiteWise"));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());

    const request = fetchMock.mock.calls[0]?.[1];
    expect(request).toBeDefined();
    expect(JSON.parse(String(request?.body))).toMatchObject({
      thread_id: "thread-1",
      selected_document_ids: ["document-1", "document-2"],
    });
  });

  it("streams a long agent answer to completion", async () => {
    const body = uiMessageStreamBody(DELTA_COUNT);
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(new TextEncoder().encode(body), {
            status: 200,
            headers: { "content-type": "text/event-stream" },
          }),
      ),
    );

    render(
      <ChatPanel
        threadId="thread-1"
        initialMessages={[]}
        agentMode
        projectId="project-1"
        layout="main"
      />,
    );

    fireEvent.change(screen.getByLabelText("Message"), {
      target: { value: "identify risks not captured in the profile" },
    });
    fireEvent.click(screen.getByLabelText("Ask SiteWise"));

    await waitFor(
      () => {
        expect(
          screen.getByLabelText("Conversation history").textContent,
        ).toContain(`chunk ${DELTA_COUNT - 1}`);
      },
      { timeout: 15000 },
    );

    expect(screen.queryByRole("alert")).toBeNull();
  }, 30000);
});
