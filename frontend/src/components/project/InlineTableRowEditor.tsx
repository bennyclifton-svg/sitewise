import {
  useLayoutEffect,
  useRef,
  useState,
  type FocusEvent,
  type KeyboardEvent,
} from "react";

import { editableTableCells, formatTableRow } from "@/lib/table-row-edit";

export function InlineTableRowEditor({
  sourceRow,
  sourceStart,
  sourceEnd,
  isSaving,
  error,
  focusCellIndex = 0,
  onCancel,
  onSave,
}: {
  sourceRow: string;
  sourceStart: number;
  sourceEnd: number;
  isSaving: boolean;
  error?: string | null;
  focusCellIndex?: number;
  onCancel: () => void;
  onSave: (markdown: string) => Promise<void>;
}) {
  const cells = editableTableCells(sourceRow);
  const rowRef = useRef<HTMLTableRowElement>(null);
  const cellRefs = useRef<Array<HTMLTableCellElement | null>>([]);
  const [isDirty, setIsDirty] = useState(false);
  const savingRef = useRef(false);

  useLayoutEffect(() => {
    const focusIndex = Math.min(Math.max(focusCellIndex, 0), Math.max(cells.length - 1, 0));
    const cell = cellRefs.current[focusIndex];
    if (!cell) return;
    cell.focus();
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(cell);
    range.collapse(false);
    selection?.removeAllRanges();
    selection?.addRange(range);
  }, [cells.length, focusCellIndex]);

  async function save() {
    const row = rowRef.current;
    if (!row || !isDirty || isSaving || savingRef.current) return;
    savingRef.current = true;
    try {
      const nextCells = Array.from(
        row.querySelectorAll<HTMLElement>("[data-table-cell-editor]"),
      ).map((cell) => (cell.textContent ?? "").replace(/\u00a0/g, " ").trim());
      await onSave(formatTableRow(nextCells));
    } finally {
      savingRef.current = false;
    }
  }

  function handleBlur(event: FocusEvent<HTMLTableRowElement>) {
    const next = event.relatedTarget;
    if (next instanceof Node && rowRef.current?.contains(next)) return;
    if (!isDirty) {
      onCancel();
      return;
    }
    void save();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTableCellElement>) {
    if (event.nativeEvent.isComposing) return;
    if (event.key === "Escape") {
      event.preventDefault();
      onCancel();
      return;
    }
    if (event.key === "Enter") {
      event.preventDefault();
      void save();
    }
  }

  return (
    <>
      <tr
        ref={rowRef}
        className="sw-table-row even:bg-muted/20"
        data-instruction-ui
        data-block-type="table_row"
        data-md-start={sourceStart}
        data-md-end={sourceEnd}
        onBlur={handleBlur}
      >
        {cells.map((cell, index) => (
          <td
            key={`edit-cell-${index}`}
            ref={(node) => {
              cellRefs.current[index] = node;
            }}
            role="textbox"
            aria-label={`Edit table cell ${index + 1}`}
            aria-multiline="false"
            aria-busy={isSaving}
            contentEditable={!isSaving}
            suppressContentEditableWarning
            spellCheck
            data-table-cell-editor
            className="border-b px-3 py-2 align-top text-foreground caret-[var(--sw-beam-hex)] outline-none"
            onInput={() => setIsDirty(true)}
            onKeyDown={handleKeyDown}
          >
            {cell}
          </td>
        ))}
      </tr>
      {error ? (
        <tr>
          <td
            className="px-3 py-2 text-sm text-destructive"
            colSpan={Math.max(cells.length, 1)}
            role="alert"
          >
            {error}
          </td>
        </tr>
      ) : null}
    </>
  );
}
