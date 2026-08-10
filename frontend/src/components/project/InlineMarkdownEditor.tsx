import {
  useLayoutEffect,
  useRef,
  useState,
  type ClipboardEvent,
  type FocusEvent,
  type KeyboardEvent,
  type ReactNode,
} from "react";

import { serializeInlineMarkdown } from "@/lib/inline-markdown";

export function InlineMarkdownEditor({
  children,
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
  const [isDirty, setIsDirty] = useState(false);
  const savingRef = useRef(false);

  useLayoutEffect(() => {
    const editor = editorRef.current;
    if (!editor) return;

    editor.focus();
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(editor);
    range.collapse(false);
    selection?.removeAllRanges();
    selection?.addRange(range);
  }, []);

  async function save() {
    const editor = editorRef.current;
    if (!editor || !isDirty || isSaving || savingRef.current) return;
    savingRef.current = true;
    try {
      await onSave(serializeInlineMarkdown(editor));
    } finally {
      savingRef.current = false;
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLParagraphElement>) {
    if (event.nativeEvent.isComposing) return;
    if (event.key === "Escape") {
      event.preventDefault();
      onCancel();
    }
  }

  function handleBlur(event: FocusEvent<HTMLParagraphElement>) {
    const next = event.relatedTarget;
    if (next instanceof Node && editorRef.current?.contains(next)) return;
    if (!isDirty) {
      onCancel();
      return;
    }
    void save();
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
        onBlur={handleBlur}
        onPaste={handlePaste}
        onClick={(event) => {
          if ((event.target as Element).closest("a")) event.preventDefault();
        }}
      >
        {children}
      </p>
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
