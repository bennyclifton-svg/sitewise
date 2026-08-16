import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

type ChatActivityValue = {
  busyThreadIds: ReadonlySet<string>;
  setThreadBusy: (threadId: string, busy: boolean) => void;
};

const ChatActivityContext = createContext<ChatActivityValue>({
  busyThreadIds: new Set(),
  setThreadBusy: () => {},
});

export function ChatActivityProvider({ children }: { children: ReactNode }) {
  const [busyThreadIds, setBusyThreadIds] = useState<ReadonlySet<string>>(
    () => new Set(),
  );

  const setThreadBusy = useCallback((threadId: string, busy: boolean) => {
    setBusyThreadIds((current) => {
      const has = current.has(threadId);
      if (busy === has) return current;
      const next = new Set(current);
      if (busy) next.add(threadId);
      else next.delete(threadId);
      return next;
    });
  }, []);

  const value = useMemo(
    () => ({ busyThreadIds, setThreadBusy }),
    [busyThreadIds, setThreadBusy],
  );

  return (
    <ChatActivityContext.Provider value={value}>
      {children}
    </ChatActivityContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useChatActivity(): ChatActivityValue {
  return useContext(ChatActivityContext);
}
