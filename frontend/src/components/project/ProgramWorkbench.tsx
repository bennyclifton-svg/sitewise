import { useEffect, useRef, useState } from "react";

import { ProgramGantt } from "@/components/project/ProgramGantt";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import {
  applyProgrammeOperationsLocally,
  coalesceProgrammeOperations,
  type ProgrammeOperation,
  type ProgrammeScale,
  type ProgrammeState,
} from "@/lib/programme";
import { queryClient } from "@/lib/query-client";
import { workbenchKeys } from "@/lib/queries/workbench";

const FLUSH_MS = 220;

export function ProgramWorkbench({
  projectId,
  active = true,
}: {
  projectId: string;
  /** False while the workbench is kept mounted but hidden. */
  active?: boolean;
}) {
  const [state, setState] = useState<ProgrammeState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadedId, setLoadedId] = useState(projectId);
  const stateRef = useRef<ProgrammeState | null>(null);
  const versionRef = useRef(0);
  const queueRef = useRef<ProgrammeOperation[]>([]);
  const scaleRef = useRef<ProgrammeScale | null>(null);
  const timerRef = useRef<number | null>(null);
  const flushingRef = useRef(false);

  if (loadedId !== projectId) {
    setLoadedId(projectId);
    setState(null);
    setError(null);
  }

  useEffect(() => {
    let cancelled = false;
    queueRef.current = [];
    scaleRef.current = null;
    stateRef.current = null;
    versionRef.current = 0;
    void queryClient
      .fetchQuery({
        queryKey: workbenchKeys.programme(projectId),
        queryFn: () => api.ensureProgramme(projectId),
      })
      .then(
      (value) => {
        if (cancelled) return;
        stateRef.current = value;
        versionRef.current = value.version;
        setState(value);
      },
      (loadError) => {
        if (!cancelled) {
          setError(
            loadError instanceof ApiError
              ? loadError.message
              : "Programme could not load.",
          );
        }
      },
    );
    return () => {
      cancelled = true;
      if (timerRef.current !== null) window.clearTimeout(timerRef.current);
    };
  }, [projectId]);

  function replaceState(next: ProgrammeState) {
    stateRef.current = next;
    versionRef.current = next.version;
    setState(next);
    queryClient.setQueryData(workbenchKeys.programme(projectId), next);
  }

  function scheduleFlush(immediate = false) {
    if (timerRef.current !== null) window.clearTimeout(timerRef.current);
    if (immediate) {
      timerRef.current = null;
      void flush();
      return;
    }
    timerRef.current = window.setTimeout(() => {
      timerRef.current = null;
      void flush();
    }, FLUSH_MS);
  }

  async function flush() {
    if (flushingRef.current) return;
    const queued = coalesceProgrammeOperations(queueRef.current);
    const scale = scaleRef.current;
    if ((!queued.length && !scale) || !stateRef.current) return;
    queueRef.current = [];
    scaleRef.current = null;
    flushingRef.current = true;
    try {
      let next = stateRef.current;
      if (queued.length) {
        next = await api.applyProgrammeOperations(projectId, versionRef.current, queued);
        versionRef.current = next.version;
      }
      if (scale) {
        next = await api.setProgrammeView(projectId, versionRef.current, {
          view_scale: scale,
        });
        versionRef.current = next.version;
      }
      if (queueRef.current.length === 0 && scaleRef.current === null) {
        replaceState(next);
      } else if (stateRef.current) {
        const merged = { ...stateRef.current, version: next.version };
        stateRef.current = merged;
        setState(merged);
      }
    } catch (flushError) {
      if (flushError instanceof ApiError && flushError.status === 409) {
        try {
          const fresh = await api.getProgrammeState(projectId);
          versionRef.current = fresh.version;
          queueRef.current = [...queued, ...queueRef.current];
          if (scale) scaleRef.current = scaleRef.current ?? scale;
          flushingRef.current = false;
          await flush();
          return;
        } catch {
          // Fall through to the reload path.
        }
      }
      setError(
        flushError instanceof ApiError
          ? flushError.message
          : "Could not update the programme.",
      );
      try {
        replaceState(await api.ensureProgramme(projectId));
        queueRef.current = [];
        scaleRef.current = null;
      } catch {
        // Keep the optimistic state visible.
      }
    } finally {
      flushingRef.current = false;
      if (queueRef.current.length || scaleRef.current) scheduleFlush(true);
    }
  }

  function operate(operations: ProgrammeOperation[]) {
    const current = stateRef.current;
    if (!current) return;
    const next = applyProgrammeOperationsLocally(current, operations);
    stateRef.current = next;
    setState(next);
    setError(null);
    queueRef.current.push(...operations);
    const structural = operations.some((item) => item.operation !== "UPDATE");
    scheduleFlush(structural);
  }

  function changeScale(view_scale: ProgrammeScale) {
    const current = stateRef.current;
    if (!current) return;
    const next = { ...current, view_scale };
    stateRef.current = next;
    setState(next);
    scaleRef.current = view_scale;
    scheduleFlush();
  }

  if (error && !state) {
    return <p className="text-sm text-destructive">{error}</p>;
  }
  if (!state) {
    return <p className="text-sm text-muted-foreground">Loading programme...</p>;
  }

  return (
    <div className="flex min-w-0 flex-col gap-3">
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <ProgramGantt
        state={state}
        mode="edit"
        active={active}
        onOperate={operate}
        onScaleChange={changeScale}
      />
    </div>
  );
}
