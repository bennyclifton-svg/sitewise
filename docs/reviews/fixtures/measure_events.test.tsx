// Isolated diagnostic: no application server, credentials or external requests.
// Before running, save the reviewed project-data.ts to the path imported below.
import { writeFileSync } from "node:fs";
import { QueryClient, QueryClientProvider, QueryObserver } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { expect, it, vi } from "vitest";
import { api } from "@/lib/api";
import { useProjectEventCursor as after } from "@/lib/queries/project-data";
import { useProjectEventCursor as before } from "./project-data.before";
import type { ProjectEvent } from "@/lib/types/project";

vi.mock("@/lib/api", () => ({ api: { getProjectEvents: vi.fn() } }));

it("measures event-page refresh work with identical warm query fixtures", async () => {
  vi.useFakeTimers();
  const results: object[] = [];
  try {
    for (const [label, useCursor] of [["before", before], ["after", after]] as const) {
      for (const workflows of [1, 2, 4]) {
        for (let sample = 0; sample < 10; sample++) {
          const events = Array.from({ length: workflows * 10 }, (_, i) => ({
            id: `event-${i}`, sequence: i + 1, project_id: "fixture",
            resource_type: "workflow_run", payload: {
              changedResources: ["project_evidence", "workflow_run"],
            },
          } as ProjectEvent));
          vi.mocked(api.getProjectEvents).mockResolvedValue({ events, next_after: events.length });
          const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
          let requests = 0;
          let aborts = 0;
          const unsubscribe = ["detail", "evidence", "evidence-document", "workspace-tree", "activity", "pulse"].map((key) => {
            const observer = new QueryObserver(queryClient, {
              queryKey: ["project", "fixture", key], initialData: {}, staleTime: Infinity,
              queryFn: ({ signal }) => {
                requests++;
                return new Promise<object>((resolve, reject) => {
                  const timer = setTimeout(() => resolve({}), 20);
                  signal.addEventListener("abort", () => {
                    aborts++;
                    clearTimeout(timer);
                    reject(new DOMException("Aborted", "AbortError"));
                  }, { once: true });
                });
              },
            });
            return observer.subscribe(() => {});
          });
          const invalidate = vi.spyOn(queryClient, "invalidateQueries");
          const onEvent = vi.fn();
          const hook = renderHook(() => useCursor({ projectId: "fixture", enabled: true, active: true, onEvent }), {
            wrapper: ({ children }: { children: ReactNode }) => <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>,
          });
          await act(async () => { await vi.advanceTimersByTimeAsync(25); });
          results.push({ label, workflows, sample, events: events.length,
            invalidations: invalidate.mock.calls.length, requests, aborts });
          expect(onEvent).toHaveBeenCalledTimes(events.length);
          hook.unmount();
          unsubscribe.forEach((stop) => stop());
          queryClient.clear();
        }
      }
    }
    writeFileSync("../.tmp/architecture-review/events-measurements.json", JSON.stringify(results, null, 2));
  } finally {
    vi.useRealTimers();
  }
});

