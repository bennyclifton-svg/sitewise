import { Check, LoaderCircle, Pencil, X } from "lucide-react";
import { useState } from "react";
import type { ChangeEvent } from "react";

import { Button } from "@/components/ui/button";
import type {
  TenderMatrixMappingChoice,
  TenderQaItem,
  TenderQaResolveRequest,
  TenderTaxonomyCell,
} from "@/lib/types/tender";

import { pageEvidenceFromPayload } from "./evidence";
import { formatTenderMoney, formatTenderPercent } from "./format";
import { PageImageViewer } from "./PageImageViewer";
import { QaAdjudicationPane, type QaMode } from "./QaAdjudicationPane";
import { qaQuestion } from "./qa";

/**
 * Expanded panel for one matrix cell: multi-candidate mapping choices plus the
 * QA items anchored to that cell, each expandable to the full adjudication
 * surface (source-page evidence + edit controls).
 */
export function MatrixQaPanel({
  cellCode,
  cellName,
  quoteName,
  items,
  choices,
  taxonomy,
  resolving,
  error,
  onClose,
  onAccept,
  onResolve,
  onMappingChoice,
}: {
  cellCode: string;
  cellName: string;
  quoteName: string | null;
  items: TenderQaItem[];
  choices: TenderMatrixMappingChoice[];
  taxonomy: TenderTaxonomyCell[];
  resolving: string | null;
  error: string | null;
  onClose: () => void;
  onAccept: (item: TenderQaItem) => void;
  onResolve: (item: TenderQaItem, request: TenderQaResolveRequest) => Promise<void>;
  onMappingChoice: (mappingId: string, cellCode: string) => Promise<void>;
}) {
  return (
    <div className="border-b bg-background px-4 py-3">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium">
          {cellName}
          <span className="ml-2 font-mono text-xs text-muted-foreground">{cellCode}</span>
          {quoteName ? (
            <span className="ml-2 text-xs text-muted-foreground">{quoteName}</span>
          ) : null}
        </p>
        <button
          type="button"
          className="cursor-pointer rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
          aria-label="Close questions"
          onClick={onClose}
        >
          <X className="size-4" aria-hidden />
        </button>
      </div>
      {choices.length && quoteName ? (
        <div className="mt-2 space-y-2">
          {choices.map((choice) => (
            <MappingChoiceControl
              key={choice.mapping_id}
              choice={choice}
              quoteName={quoteName}
              cellName={cellName}
              onChange={onMappingChoice}
            />
          ))}
        </div>
      ) : null}
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
          />
        ))}
      </ul>
    </div>
  );
}

/**
 * One QA item: question line with quick Accept, plus an Adjudicate toggle that
 * embeds the source-page viewer and the full adjudication pane inline. Shared
 * by the cell panel and the quote/document-level strip.
 */
export function MatrixQaItemRow({
  item,
  taxonomy,
  resolving,
  error,
  onAccept,
  onResolve,
  adjudicateLabel = "Adjudicate",
  allowQuickAccept = true,
}: {
  item: TenderQaItem;
  taxonomy: TenderTaxonomyCell[];
  resolving: string | null;
  error: string | null;
  onAccept: (item: TenderQaItem) => void;
  onResolve: (item: TenderQaItem, request: TenderQaResolveRequest) => Promise<void>;
  adjudicateLabel?: string;
  allowQuickAccept?: boolean;
}) {
  const [isAdjudicating, setIsAdjudicating] = useState(false);
  const [mode, setMode] = useState<QaMode>("review");

  function toggleAdjudication() {
    setIsAdjudicating((current) => !current);
    setMode("review");
  }

  return (
    <li className="rounded-md border bg-card px-3 py-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-sm">{qaQuestion(item)}</p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Impact {formatTenderMoney(item.report_impact_cents)} · Confidence{" "}
            {formatTenderPercent(item.confidence)}
          </p>
        </div>
        <div className="flex shrink-0 gap-1.5">
          {allowQuickAccept ? (
            <Button
              type="button"
              size="xs"
              variant="secondary"
              disabled={resolving !== null}
              onClick={() => onAccept(item)}
            >
              {resolving === item.id ? (
                <LoaderCircle className="size-3 animate-spin" aria-hidden />
              ) : (
                <Check className="size-3" aria-hidden />
              )}
              Accept
            </Button>
          ) : null}
          <Button
            type="button"
            size="xs"
            variant={isAdjudicating ? "secondary" : "ghost"}
            onClick={toggleAdjudication}
          >
            <Pencil className="size-3" aria-hidden />
            {adjudicateLabel}
          </Button>
        </div>
      </div>
      {isAdjudicating ? (
        <div className="mt-2 grid gap-3 lg:grid-cols-[minmax(0,1fr)_22rem]">
          <PageImageViewer evidence={pageEvidenceFromPayload(item.payload)} />
          <QaAdjudicationPane
            item={item}
            taxonomy={taxonomy}
            mode={mode}
            isResolving={resolving === item.id}
            error={error}
            onModeChange={setMode}
            onResolve={(request) => onResolve(item, request)}
          />
        </div>
      ) : null}
    </li>
  );
}

export function MappingChoiceControl({
  choice,
  quoteName,
  cellName,
  onChange,
}: {
  choice: TenderMatrixMappingChoice;
  quoteName: string;
  cellName: string;
  onChange: (mappingId: string, cellCode: string) => Promise<void>;
}) {
  const [selected, setSelected] = useState(choice.selected_cell_code);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleChange(event: ChangeEvent<HTMLSelectElement>) {
    const nextCellCode = event.target.value;
    setSelected(nextCellCode);
    setIsSaving(true);
    setError(null);
    try {
      await onChange(choice.mapping_id, nextCellCode);
    } catch {
      setSelected(choice.selected_cell_code);
      setError("Could not save");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div>
      <select
        aria-label={`Mapping choice for ${quoteName} ${cellName}`}
        className="w-full rounded-md border border-border bg-background px-2 py-1 text-xs text-foreground"
        value={selected}
        disabled={choice.locked || isSaving}
        onChange={handleChange}
      >
        {choice.candidates.map((candidate) => (
          <option
            key={candidate.cell_code}
            value={candidate.cell_code}
            className="bg-white text-neutral-900"
            style={{ color: "#111111", backgroundColor: "#ffffff" }}
          >
            {candidate.name ?? candidate.cell_code}
          </option>
        ))}
      </select>
      {choice.locked ? (
        <p className="mt-1 text-[0.68rem] text-muted-foreground">Locked</p>
      ) : null}
      {error ? <p className="mt-1 text-[0.68rem] text-destructive">{error}</p> : null}
    </div>
  );
}
