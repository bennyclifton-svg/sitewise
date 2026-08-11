import {
  useLayoutEffect,
  useRef,
  type ReactNode,
} from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { cn } from "@/lib/utils";
import { serializeInlineMarkdown } from "@/lib/inline-markdown";

export function InlineMarkdownEditor({
  children,
  sourceStart,
  sourceEnd,
  isChanged,
  isSaving,
  error,
  caretPoint,
  className,
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
  caretPoint?: { x: number; y: number } | null;
  className?: string;
  onCancel: () => void;
  onSave: (markdown: string) => Promise<void>;
}) {
  const hostRef = useRef<HTMLDivElement>(null);
  const editorRef = useRef<HTMLParagraphElement | null>(null);
  const dirtyRef = useRef(false);
  const savingRef = useRef(false);
  const onCancelRef = useRef(onCancel);
  const onSaveRef = useRef(onSave);
  const isSavingRef = useRef(isSaving);
  onCancelRef.current = onCancel;
  onSaveRef.current = onSave;
  isSavingRef.current = isSaving;

  // Seed HTML once from the opening children; never let React reconcile into
  // the contentEditable after that (that is what jumped the caret).
  const initialHtmlRef = useRef<string | null>(null);
  if (initialHtmlRef.current === null) {
    initialHtmlRef.current = renderToStaticMarkup(<>{children}</>);
  }
  const caretPointRef = useRef(caretPoint);

  useLayoutEffect(() => {
    const host = hostRef.current;
    if (!host || editorRef.current) return;

    const editor = document.createElement("p");
    editor.setAttribute("role", "textbox");
    editor.setAttribute("aria-label", "Edit selected text");
    editor.setAttribute("aria-multiline", "true");
    editor.setAttribute("aria-busy", isSavingRef.current ? "true" : "false");
    editor.tabIndex = 0;
    editor.contentEditable = isSavingRef.current ? "false" : "true";
    editor.spellcheck = true;
    editor.dataset.instructionUi = "";
    editor.dataset.mdStart = String(sourceStart);
    editor.dataset.mdEnd = String(sourceEnd);
    if (isChanged) editor.dataset.mdChanged = "";
    editor.className =
      "min-h-5 w-full whitespace-pre-wrap leading-relaxed caret-[var(--sw-beam-hex)] outline-none";
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
          await onSaveRef.current(serializeInlineMarkdown(editor));
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
    const onClick = (event: MouseEvent) => {
      if ((event.target as Element).closest("a")) event.preventDefault();
    };

    editor.addEventListener("input", onInput);
    editor.addEventListener("keydown", onKeyDown);
    editor.addEventListener("blur", onBlur);
    editor.addEventListener("paste", onPaste);
    editor.addEventListener("click", onClick);
    host.replaceChildren(editor);
    editorRef.current = editor;
    placeCaret(editor, caretPointRef.current);

    return () => {
      editor.removeEventListener("input", onInput);
      editor.removeEventListener("keydown", onKeyDown);
      editor.removeEventListener("blur", onBlur);
      editor.removeEventListener("paste", onPaste);
      editor.removeEventListener("click", onClick);
      editorRef.current = null;
      host.replaceChildren();
    };
    // One-time mount for this edit session.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional
  }, []);

  useLayoutEffect(() => {
    const editor = editorRef.current;
    if (!editor) return;
    editor.contentEditable = isSaving ? "false" : "true";
    editor.setAttribute("aria-busy", isSaving ? "true" : "false");
  }, [isSaving]);

  return (
    <>
      <div
        ref={hostRef}
        className={cn("min-w-0 flex-1", className)}
        data-inline-markdown-host=""
      />
      {error ? (
        <p className="my-2 text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}
    </>
  );
}

function placeCaret(
  editor: HTMLElement,
  caretPoint?: { x: number; y: number } | null,
) {
  editor.focus();
  const selection = window.getSelection();
  if (!selection) return;

  if (caretPoint) {
    const doc = document as Document & {
      caretRangeFromPoint?: (x: number, y: number) => Range | null;
      caretPositionFromPoint?: (
        x: number,
        y: number,
      ) => { offsetNode: Node; offset: number } | null;
    };
    const fromPoint = doc.caretRangeFromPoint?.(caretPoint.x, caretPoint.y);
    if (fromPoint && editor.contains(fromPoint.startContainer)) {
      fromPoint.collapse(true);
      selection.removeAllRanges();
      selection.addRange(fromPoint);
      return;
    }
    const position = doc.caretPositionFromPoint?.(caretPoint.x, caretPoint.y);
    if (position && editor.contains(position.offsetNode)) {
      const range = document.createRange();
      range.setStart(position.offsetNode, position.offset);
      range.collapse(true);
      selection.removeAllRanges();
      selection.addRange(range);
      return;
    }
  }
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
