import {
  useCallback,
  useEffect,
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
  const unmountingRef = useRef(false);
  const [editCells] = useState(() => editableTableCells(sourceRow));
  const rowRef = useRef<HTMLTableRowElement>(null);
  const cellRefs = useRef<Array<HTMLTableCellElement | null>>([]);
  const dirtyRef = useRef(false);
  const savingRef = useRef(false);
  const pendingRef = useRef(false);

  useLayoutEffect(() => {
    const focusIndex = Math.min(
      Math.max(focusCellIndex, 0),
      Math.max(editCells.length - 1, 0),
    );
    const cell = cellRefs.current[focusIndex];
    if (!cell) return;
    cell.focus();
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(cell);
    range.collapse(false);
    selection?.removeAllRanges();
    selection?.addRange(range);
  }, [editCells.length, focusCellIndex]);

  useLayoutEffect(() => {
    unmountingRef.current = false;
    return () => {
      unmountingRef.current = true;
    };
  }, []);

  const save = useCallback(async () => {
    const row = rowRef.current;
    if (!row || !dirtyRef.current) return;
    if (savingRef.current || isSaving) {
      // A commit is already running. Remember that there is newer content and
      // flush it when the commit lands — dropping it here loses the user's
      // keystrokes with no error (plan §8).
      pendingRef.current = true;
      return;
    }
    savingRef.current = true;
    try {
      do {
        pendingRef.current = false;
        const nextCells = Array.from(
          row.querySelectorAll<HTMLElement>("[data-table-cell-editor]"),
        ).map((cell) => (cell.textContent ?? "").replace(/\u00a0/g, " ").trim());
        dirtyRef.current = false;
        await onSave(formatTableRow(nextCells));
        // Loop only if the user typed again during the await, so this is
        // bounded by real keystrokes rather than spinning.
      } while (pendingRef.current && dirtyRef.current);
    } finally {
      savingRef.current = false;
    }
  }, [isSaving, onSave]);

  useEffect(() => {
    if (isSaving || !pendingRef.current || !dirtyRef.current) return;
    void save();
  }, [isSaving, save]);

  function handleBlur(event: FocusEvent<HTMLTableRowElement>) {
    if (unmountingRef.current || !event.currentTarget.isConnected) return;
    const next = event.relatedTarget;
    if (next instanceof Node && rowRef.current?.contains(next)) return;
    if (!dirtyRef.current) {
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
        {editCells.map((cell, index) => (
          <td
            key={`edit-cell-${index}`}
            ref={(node) => {
              cellRefs.current[index] = node;
              // Seed the cell once and then let the DOM own it. Passing the
              // text through React (children or dangerouslySetInnerHTML) means
              // any parent re-render re-applies the *original* value and
              // silently discards what the user has typed since.
              if (node && node.dataset.seeded !== "true") {
                node.textContent = cell;
                node.dataset.seeded = "true";
              }
            }}
            role="textbox"
            aria-label={`Edit table cell ${index + 1}`}
            aria-multiline="false"
            aria-busy={isSaving}
            // Stays editable during a save (plan §7). `save()` reads the DOM
            // when it runs and `savingRef` serialises overlapping saves, so
            // continued typing is captured rather than dropped.
            contentEditable
            suppressContentEditableWarning
            spellCheck
            data-table-cell-editor
            className="border-b px-3 py-2 align-top text-foreground caret-[var(--sw-beam-hex)] outline-none"
            onInput={() => {
              dirtyRef.current = true;
            }}
            onKeyDown={handleKeyDown}
          />
        ))}
      </tr>
      {error ? (
        <tr>
          <td
            className="px-3 py-2 text-sm text-destructive"
            colSpan={Math.max(editCells.length, 1)}
            role="alert"
          >
            {error}
          </td>
        </tr>
      ) : null}
    </>
  );
}
