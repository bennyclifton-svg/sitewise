import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { Button } from "@/components/ui/button";
import { dropdownMenuContentClassName } from "@/components/ui/dropdown-menu";
import type { MarkdownAnchor } from "@/lib/markdown-selection";
import { cn } from "@/lib/utils";

const CARD_WIDTH = 340;
const VIEWPORT_MARGIN = 12;

/** Keep the card on screen regardless of where in the document the user selected. */
function cardPosition(rect: DOMRect): { top: number; left: number } {
  const viewportWidth = window.innerWidth || CARD_WIDTH;
  const left = Math.min(
    Math.max(rect.left, VIEWPORT_MARGIN),
    Math.max(viewportWidth - CARD_WIDTH - VIEWPORT_MARGIN, VIEWPORT_MARGIN),
  );
  return { top: Math.max(rect.bottom + 8, VIEWPORT_MARGIN), left };
}

export function SelectionInstructionCard({
  anchor,
  sectionHeading,
  onAdd,
  onDismiss,
}: {
  anchor: MarkdownAnchor;
  sectionHeading: string;
  onAdd: (instruction: string) => void;
  onDismiss: () => void;
}) {
  const [instruction, setInstruction] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    textareaRef.current?.focus();
  }, [anchor.start, anchor.end]);

  function submit() {
    const trimmed = instruction.trim();
    if (!trimmed) return;
    onAdd(trimmed);
    setInstruction("");
  }

  // Matches the ChatComposer keyboard contract: Enter sends, Shift+Enter newlines.
  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
      return;
    }
    if (event.key === "Escape") {
      event.preventDefault();
      onDismiss();
    }
  }

  const { top, left } = cardPosition(anchor.rect);

  // bg-popover, not bg-background: the dark cockpit panels set
  // `--background: transparent` so nested in-flow sections show the panel's own
  // charcoal gradient through. A floating element painted with it has no
  // background at all, so overlays use the opaque popover token — the same
  // reason ChatHistoryPopover and ChatThreadActionsMenu do.
  return createPortal(
    <div
      data-instruction-ui
      role="dialog"
      aria-label="Add an instruction for the selected text"
      className={cn(
        dropdownMenuContentClassName,
        "fixed z-[100] w-[340px] p-3 print:hidden",
      )}
      style={{ top, left }}
    >
      <p className="text-xs font-medium text-muted-foreground">{sectionHeading}</p>
      <textarea
        ref={textareaRef}
        value={instruction}
        onChange={(event) => setInstruction(event.target.value)}
        onKeyDown={handleKeyDown}
        rows={2}
        aria-label="Instruction"
        placeholder="Tighten this, cite the clause, soften the commitment…"
        className="mt-2 block w-full resize-none rounded-md border bg-transparent px-2 py-1.5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
      />
      <div className="mt-2 flex justify-end gap-2">
        <Button variant="ghost" size="sm" onClick={onDismiss}>
          Cancel
        </Button>
        <Button size="sm" onClick={submit} disabled={!instruction.trim()}>
          Add to tray
        </Button>
      </div>
    </div>,
    document.body,
  );
}
