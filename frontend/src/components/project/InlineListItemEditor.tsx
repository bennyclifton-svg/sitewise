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

export function InlineListItemEditor({
  children,
  sourceItem,
  sourceStart,
  sourceEnd,
  isSaving,
  error,
  onCancel,
  onSave,
}: {
  children: ReactNode;
  sourceItem: string;
  sourceStart: number;
  sourceEnd: number;
  isSaving: boolean;
  error?: string | null;
  onCancel: () => void;
  onSave: (markdown: string) => Promise<void>;
}) {
  const editorRef = useRef<HTMLLIElement>(null);
  const [isDirty, setIsDirty] = useState(false);
  const savingRef = useRef(false);
  const marker =
    sourceItem.match(/^\s*(?:[-*+] |\d+[.)] )/)?.[0]?.trimStart() ?? "- ";

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
      const body = serializeInlineMarkdown(editor);
      await onSave(`${marker}${body}`);
    } finally {
      savingRef.current = false;
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLLIElement>) {
    if (event.nativeEvent.isComposing) return;
    if (event.key === "Escape") {
      event.preventDefault();
      onCancel();
    }
  }

  function handleBlur(event: FocusEvent<HTMLLIElement>) {
    const next = event.relatedTarget;
    if (next instanceof Node && editorRef.current?.contains(next)) return;
    if (!isDirty) {
      onCancel();
      return;
    }
    void save();
  }

  function handlePaste(event: ClipboardEvent<HTMLLIElement>) {
    event.preventDefault();
    insertPlainText(editorRef.current, event.clipboardData.getData("text/plain"));
    setIsDirty(true);
  }

  return (
    <>
      <li
        ref={editorRef}
        role="textbox"
        aria-label="Edit list item"
        aria-multiline="true"
        aria-busy={isSaving}
        contentEditable={!isSaving}
        suppressContentEditableWarning
        spellCheck
        data-instruction-ui
        data-block-type="list_item"
        data-md-start={sourceStart}
        data-md-end={sourceEnd}
        className="leading-relaxed caret-[var(--sw-beam-hex)] outline-none"
        onInput={() => setIsDirty(true)}
        onKeyDown={handleKeyDown}
        onBlur={handleBlur}
        onPaste={handlePaste}
      >
        {children}
      </li>
      {error ? (
        <li className="text-sm text-destructive" role="alert">
          {error}
        </li>
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
