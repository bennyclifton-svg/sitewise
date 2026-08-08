import {
  useLayoutEffect,
  useRef,
  useState,
  type ClipboardEvent,
  type KeyboardEvent,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import { Check, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { serializeInlineMarkdown } from "@/lib/inline-markdown";

export function InlineMarkdownEditor({
  children,
  sectionStart,
  sourceStart,
  sourceEnd,
  isChanged,
  isSaving,
  error,
  onCancel,
  onSave,
}: {
  children: ReactNode;
  sectionStart: number;
  sourceStart: number;
  sourceEnd: number;
  isChanged: boolean;
  isSaving: boolean;
  error?: string | null;
  onCancel: () => void;
  onSave: (markdown: string) => Promise<void>;
}) {
  const editorRef = useRef<HTMLParagraphElement>(null);
  const [controlsTarget, setControlsTarget] = useState<HTMLElement | null>(null);
  const [isDirty, setIsDirty] = useState(false);

  useLayoutEffect(() => {
    const editor = editorRef.current;
    if (!editor) return;
    const documentRoot = editor.closest(".draft-markdown");
    setControlsTarget(
      documentRoot?.querySelector<HTMLElement>(
        `[data-paragraph-actions="${sectionStart}"]`,
      ) ?? null,
    );

    editor.focus();
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(editor);
    range.collapse(false);
    selection?.removeAllRanges();
    selection?.addRange(range);
  }, [sectionStart]);

  async function save() {
    const editor = editorRef.current;
    if (!editor || !isDirty || isSaving) return;
    await onSave(serializeInlineMarkdown(editor));
  }

  function handleKeyDown(event: KeyboardEvent<HTMLParagraphElement>) {
    if (event.nativeEvent.isComposing) return;
    if (event.key === "Escape") {
      event.preventDefault();
      onCancel();
      return;
    }
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      void save();
    }
  }

  function handlePaste(event: ClipboardEvent<HTMLParagraphElement>) {
    event.preventDefault();
    insertPlainText(editorRef.current, event.clipboardData.getData("text/plain"));
    setIsDirty(true);
  }

  return (
    <>
      <p
        ref={editorRef}
        role="textbox"
        aria-label="Edit selected text"
        aria-multiline="true"
        aria-busy={isSaving}
        contentEditable={!isSaving}
        suppressContentEditableWarning
        spellCheck
        data-instruction-ui
        data-md-start={sourceStart}
        data-md-end={sourceEnd}
        data-md-changed={isChanged ? "" : undefined}
        className="my-3 min-h-5 whitespace-pre-wrap leading-relaxed caret-[var(--sw-beam-hex)] outline-none"
        onInput={() => setIsDirty(true)}
        onKeyDown={handleKeyDown}
        onPaste={handlePaste}
        onClick={(event) => {
          if ((event.target as Element).closest("a")) event.preventDefault();
        }}
      >
        {children}
      </p>
      {controlsTarget
        ? createPortal(
            <>
              <Button
                type="button"
                size="icon-xs"
                variant="outline"
                aria-label="Cancel"
                title="Cancel editing"
                onClick={onCancel}
                disabled={isSaving}
              >
                <X aria-hidden />
              </Button>
              <Button
                type="button"
                size="icon-xs"
                variant="outline"
                aria-label={isSaving ? "Saving paragraph" : "Save selection"}
                title="Save paragraph"
                onClick={() => void save()}
                disabled={!isDirty || isSaving}
              >
                <Check aria-hidden />
              </Button>
            </>,
            controlsTarget,
          )
        : null}
      {error ? (
        <p className="my-2 text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}
    </>
  );
}

function insertPlainText(editor: HTMLElement | null, text: string) {
  const selection = window.getSelection();
  if (!editor || !selection || selection.rangeCount === 0) return;
  const range = selection.getRangeAt(0);
  if (!editor.contains(range.commonAncestorContainer)) return;

  range.deleteContents();
  const fragment = document.createDocumentFragment();
  text.replace(/\r\n?/g, "\n").split("\n").forEach((line, index) => {
    if (index > 0) fragment.appendChild(document.createElement("br"));
    fragment.appendChild(document.createTextNode(line));
  });
  range.insertNode(fragment);
  range.collapse(false);
  selection.removeAllRanges();
  selection.addRange(range);
}
