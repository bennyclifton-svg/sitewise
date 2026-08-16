import type { ChatMessage, ChatThread } from "@/lib/types/chat";

export type MountedChatSession = {
  threadId: string;
  thread: ChatThread;
  messages: ChatMessage[];
};

export function reconcileMountedChatSessions({
  current,
  activeThreadId,
  incoming,
  busyThreadIds,
}: {
  current: MountedChatSession[];
  activeThreadId: string | null;
  incoming: { thread: ChatThread; messages: ChatMessage[] } | null;
  busyThreadIds: ReadonlySet<string>;
}): MountedChatSession[] {
  const byId = new Map(current.map((session) => [session.threadId, session]));

  if (incoming) {
    const existing = byId.get(incoming.thread.id);
    if (existing && busyThreadIds.has(incoming.thread.id)) {
      byId.set(incoming.thread.id, {
        ...existing,
        thread: incoming.thread,
      });
    } else {
      byId.set(incoming.thread.id, {
        threadId: incoming.thread.id,
        thread: incoming.thread,
        messages: incoming.messages,
      });
    }
  }

  const keep = new Set(busyThreadIds);
  if (activeThreadId) keep.add(activeThreadId);
  if (incoming) keep.add(incoming.thread.id);

  return [...byId.values()].filter((session) => keep.has(session.threadId));
}

export function mountedSessionsEqual(
  left: MountedChatSession[],
  right: MountedChatSession[],
): boolean {
  if (left.length !== right.length) return false;
  return left.every((session, index) => {
    const other = right[index];
    return (
      other !== undefined &&
      session.threadId === other.threadId &&
      session.thread === other.thread &&
      session.messages === other.messages
    );
  });
}
