import { useLayoutEffect, useRef, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";

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
  const hostRef = useRef<HTMLLIElement>(null);
  const editorRef = useRef<HTMLElement | null>(null);
  const dirtyRef = useRef(false);
  const savingRef = useRef(false);
  const onCancelRef = useRef(onCancel);
  const onSaveRef = useRef(onSave);
  const isSavingRef = useRef(isSaving);
  onCancelRef.current = onCancel;
  onSaveRef.current = onSave;
  isSavingRef.current = isSaving;

  const marker =
    sourceItem.match(/^\s*(?:[-*+] |\d+[.)] )/)?.[0]?.trimStart() ?? "- ";
  const initialHtmlRef = useRef<string | null>(null);
  if (initialHtmlRef.current === null) {
    initialHtmlRef.current = renderToStaticMarkup(<>{children}</>);
  }

  useLayoutEffect(() => {
    const host = hostRef.current;
    if (!host || editorRef.current) return;

    // Keep the outer <li> for list semantics; edit a nested span so React can
    // own the list item chrome without touching the typed DOM.
    const editor = document.createElement("span");
    editor.role = "textbox";
    editor.setAttribute("aria-label", "Edit list item");
    editor.setAttribute("aria-multiline", "true");
    editor.setAttribute("aria-busy", isSavingRef.current ? "true" : "false");
    editor.contentEditable = isSavingRef.current ? "false" : "true";
    editor.spellcheck = true;
    editor.dataset.instructionUi = "";
    editor.className =
      "leading-relaxed caret-[var(--sw-beam-hex)] outline-none";
    editor.innerHTML = initialHtmlRef.current ?? "";

    const onInput = () => {
      dirtyRef.current = true;
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.isComposing) return;
      if (event.key === "Escape") {
        event.preventDefault();
        onCancelRef.current();
      }
    };
    const onBlur = (event: FocusEvent) => {
      const next = event.relatedTarget;
      if (next instanceof Node && editor.contains(next)) return;
      if (!dirtyRef.current) {
        onCancelRef.current();
        return;
      }
      void (async () => {
        if (!dirtyRef.current || isSavingRef.current || savingRef.current) return;
        savingRef.current = true;
        try {
          const body = serializeInlineMarkdown(editor);
          await onSaveRef.current(`${marker}${body}`);
        } finally {
          savingRef.current = false;
        }
      })();
    };
    const onPaste = (event: ClipboardEvent) => {
      event.preventDefault();
      insertPlainText(editor, event.clipboardData?.getData("text/plain") ?? "");
      dirtyRef.current = true;
    };

    editor.addEventListener("input", onInput);
    editor.addEventListener("keydown", onKeyDown);
    editor.addEventListener("blur", onBlur);
    editor.addEventListener("paste", onPaste);
    host.replaceChildren(editor);
    editorRef.current = editor;

    editor.focus();
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(editor);
    range.collapse(false);
    selection?.removeAllRanges();
    selection?.addRange(range);

    return () => {
      editor.removeEventListener("input", onInput);
      editor.removeEventListener("keydown", onKeyDown);
      editor.removeEventListener("blur", onBlur);
      editor.removeEventListener("paste", onPaste);
      editorRef.current = null;
      host.replaceChildren();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- mount once per edit
  }, []);

  useLayoutEffect(() => {
    const editor = editorRef.current;
    if (!editor) return;
    editor.contentEditable = isSaving ? "false" : "true";
    editor.setAttribute("aria-busy", isSaving ? "true" : "false");
  }, [isSaving]);

  return (
    <>
      <li
        ref={hostRef}
        data-block-type="list_item"
        data-md-start={sourceStart}
        data-md-end={sourceEnd}
        className="leading-relaxed"
      />
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
