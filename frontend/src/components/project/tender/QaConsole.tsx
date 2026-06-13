import { AlertCircle, LoaderCircle } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import type {
  TenderQaItem,
  TenderQaResolveRequest,
  TenderTaxonomyCell,
} from "@/lib/types/tender";

import { pageEvidenceFromPayload } from "./evidence";
import { PageImageViewer } from "./PageImageViewer";
import { QaAdjudicationPane, type QaMode } from "./QaAdjudicationPane";
import { QaQueuePane } from "./QaQueuePane";

export function QaConsole({ comparisonId }: { comparisonId: string }) {
  const [items, setItems] = useState<TenderQaItem[]>([]);
  const [taxonomy, setTaxonomy] = useState<TenderTaxonomyCell[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [mode, setMode] = useState<QaMode>("review");
  const [isLoading, setIsLoading] = useState(true);
  const [isResolving, setIsResolving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resolveError, setResolveError] = useState<string | null>(null);

  const selectedItem = useMemo(
    () => items.find((item) => item.id === selectedId) ?? items[0] ?? null,
    [items, selectedId],
  );
  const selectedIndex = selectedItem
    ? items.findIndex((item) => item.id === selectedItem.id)
    : -1;
  const pageEvidence = pageEvidenceFromPayload(selectedItem?.payload ?? {});

  async function loadQueue() {
    const data = await api.getTenderQaQueue(comparisonId);
    setItems(data.items);
    setSelectedId((current) =>
      current && data.items.some((item) => item.id === current)
        ? current
        : data.items[0]?.id ?? null,
    );
  }

  useEffect(() => {
    let cancelled = false;

    async function loadConsole() {
      setIsLoading(true);
      setError(null);
      try {
        const [queue, taxonomyCells] = await Promise.all([
          api.getTenderQaQueue(comparisonId),
          api.getTenderTaxonomy(),
        ]);
        if (cancelled) return;
        setItems(queue.items);
        setTaxonomy(taxonomyCells);
        setSelectedId(queue.items[0]?.id ?? null);
      } catch (loadError) {
        if (!cancelled) {
          setError(
            loadError instanceof ApiError
              ? loadError.message
              : "Could not load QA console.",
          );
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void loadConsole();
    return () => {
      cancelled = true;
    };
  }, [comparisonId]);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.defaultPrevented || isTypingTarget(event.target)) return;
      const key = event.key.toLowerCase();
      if (key === "j") {
        event.preventDefault();
        selectOffset(1);
      } else if (key === "k") {
        event.preventDefault();
        selectOffset(-1);
      } else if (key === "e") {
        event.preventDefault();
        setMode("edit");
      } else if (key === "s") {
        event.preventDefault();
        setMode("split");
      } else if (key === "a" && selectedItem && !isResolving) {
        event.preventDefault();
        void resolveItem({ action: "accept", corrected_value: null, reason: null });
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  });

  function selectOffset(offset: number) {
    if (!items.length) return;
    const current = selectedIndex >= 0 ? selectedIndex : 0;
    const next = Math.max(0, Math.min(items.length - 1, current + offset));
    setSelectedId(items[next].id);
    setMode("review");
    setResolveError(null);
  }

  async function resolveItem(request: TenderQaResolveRequest) {
    if (!selectedItem) return;
    setIsResolving(true);
    setResolveError(null);
    try {
      await api.resolveTenderQaItem(selectedItem.id, request);
      await loadQueue();
      setMode("review");
    } catch (resolveFailure) {
      setResolveError(
        resolveFailure instanceof ApiError
          ? resolveFailure.message
          : "Could not resolve QA item.",
      );
    } finally {
      setIsResolving(false);
    }
  }

  if (isLoading) {
    return (
      <div className="flex min-h-[42rem] items-center justify-center rounded-md border bg-card text-sm text-muted-foreground">
        <LoaderCircle className="mr-2 size-4 animate-spin" aria-hidden />
        Loading QA console
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-[42rem] items-center justify-center rounded-md border bg-card p-6 text-center">
        <div>
          <AlertCircle className="mx-auto size-7 text-destructive" aria-hidden />
          <p className="mt-3 text-sm font-medium text-destructive">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="grid min-h-[calc(100vh-14rem)] gap-3 lg:grid-cols-[19rem_minmax(0,1fr)_22rem]">
      <QaQueuePane
        items={items}
        selectedId={selectedItem?.id ?? null}
        onSelect={(itemId) => {
          setSelectedId(itemId);
          setMode("review");
          setResolveError(null);
        }}
      />
      <PageImageViewer evidence={pageEvidence} />
      <QaAdjudicationPane
        item={selectedItem}
        taxonomy={taxonomy}
        mode={mode}
        isResolving={isResolving}
        error={resolveError}
        onModeChange={setMode}
        onResolve={resolveItem}
      />
    </div>
  );
}

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName.toLowerCase();
  return tag === "input" || tag === "textarea" || tag === "select" || target.isContentEditable;
}
