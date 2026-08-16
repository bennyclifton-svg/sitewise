import { describe, expect, it } from "vitest";

import { reconcileMountedChatSessions } from "@/lib/chat-session-mounts";
import type { ChatMessage, ChatThread } from "@/lib/types/chat";

function thread(id: string, title = id): ChatThread {
  return {
    id,
    project_id: "project-1",
    title,
    created_at: "2026-08-15T00:00:00Z",
    updated_at: "2026-08-15T00:00:00Z",
  };
}

function message(id: string, content: string): ChatMessage {
  return {
    id,
    role: "user",
    content,
    message_data: null,
    created_at: "2026-08-15T00:00:00Z",
  };
}

describe("reconcileMountedChatSessions", () => {
  it("mounts the incoming thread when nothing is open", () => {
    const incoming = { thread: thread("a"), messages: [message("m1", "hello")] };

    expect(
      reconcileMountedChatSessions({
        current: [],
        activeThreadId: "a",
        incoming,
        busyThreadIds: new Set(),
      }),
    ).toEqual([{ threadId: "a", thread: incoming.thread, messages: incoming.messages }]);
  });

  it("keeps a busy thread mounted when another chat becomes active", () => {
    const liveA = {
      threadId: "a",
      thread: thread("a"),
      messages: [message("m1", "appoint the architect")],
    };
    const incomingB = { thread: thread("b"), messages: [message("m2", "other chat")] };

    const next = reconcileMountedChatSessions({
      current: [liveA],
      activeThreadId: "b",
      incoming: incomingB,
      busyThreadIds: new Set(["a"]),
    });

    expect(next.map((session) => session.threadId)).toEqual(["a", "b"]);
    expect(next[0]).toEqual(liveA);
  });

  it("does not replace a busy thread's live messages when that chat is reopened", () => {
    const liveA = {
      threadId: "a",
      thread: thread("a", "Architectural engagement"),
      messages: [message("m1", "in-flight")],
    };

    const next = reconcileMountedChatSessions({
      current: [liveA],
      activeThreadId: "a",
      incoming: {
        thread: thread("a", "Architectural engagement"),
        messages: [message("stale", "persisted snapshot")],
      },
      busyThreadIds: new Set(["a"]),
    });

    expect(next).toHaveLength(1);
    expect(next[0]?.messages).toEqual(liveA.messages);
  });

  it("drops an idle parked thread once it is no longer live", () => {
    const idleA = {
      threadId: "a",
      thread: thread("a"),
      messages: [message("m1", "done")],
    };
    const activeB = {
      threadId: "b",
      thread: thread("b"),
      messages: [message("m2", "open")],
    };

    expect(
      reconcileMountedChatSessions({
        current: [idleA, activeB],
        activeThreadId: "b",
        incoming: null,
        busyThreadIds: new Set(),
      }).map((session) => session.threadId),
    ).toEqual(["b"]);
  });
});
