import { ChevronDown, ChevronRight, FileQuestion } from "lucide-react";
import { useState } from "react";

import type {
  TenderQaItem,
  TenderQaResolveRequest,
  TenderTaxonomyCell,
} from "@/lib/types/tender";

import { MatrixQaItemRow } from "./MatrixQaPanel";

/**
 * Review strip for QA items that have no matrix cell to anchor to: document
 * classifications and quote-level flags. Accept-all skips unclassified
 * documents on purpose, so this strip is the only way to clear them and
 * unblock the report build.
 */
export function MatrixQaStrip({
  items,
  taxonomy,
  resolving,
  error,
  onAccept,
  onResolve,
}: {
  items: TenderQaItem[];
  taxonomy: TenderTaxonomyCell[];
  resolving: string | null;
  error: string | null;
  onAccept: (item: TenderQaItem) => void;
  onResolve: (item: TenderQaItem, request: TenderQaResolveRequest) => Promise<void>;
}) {
  const [isExpanded, setIsExpanded] = useState(true);
  if (!items.length) return null;

  const documentCount = items.filter(
    (item) => item.entity_type === "document_classification",
  ).length;
  const otherCount = items.length - documentCount;
  const summaryParts = [
    documentCount > 0
      ? `${documentCount} document${documentCount === 1 ? "" : "s"} need${documentCount === 1 ? "s" : ""} classification`
      : null,
    otherCount > 0
      ? `${otherCount} quote-level finding${otherCount === 1 ? "" : "s"}`
      : null,
  ].filter(Boolean);

  return (
    <div className="border-b bg-background px-4 py-2">
      <button
        type="button"
        className="flex w-full cursor-pointer items-center gap-1.5 text-left text-sm font-medium"
        aria-expanded={isExpanded}
        onClick={() => setIsExpanded((current) => !current)}
      >
        {isExpanded ? (
          <ChevronDown className="size-4 shrink-0 text-muted-foreground" aria-hidden />
        ) : (
          <ChevronRight className="size-4 shrink-0 text-muted-foreground" aria-hidden />
        )}
        <FileQuestion className="size-4 shrink-0 text-[var(--warn-text)]" aria-hidden />
        {summaryParts.join(", ")}
      </button>
      {isExpanded ? (
        <ul className="mt-2 space-y-1.5">
          {items.map((item) => (
            <MatrixQaItemRow
              key={item.id}
              item={item}
              taxonomy={taxonomy}
              resolving={resolving}
              error={error}
              onAccept={onAccept}
              onResolve={onResolve}
              adjudicateLabel={
                item.entity_type === "document_classification" ? "Classify" : "Adjudicate"
              }
              allowQuickAccept={item.entity_type !== "document_classification"}
            />
          ))}
        </ul>
      ) : null}
    </div>
  );
}
