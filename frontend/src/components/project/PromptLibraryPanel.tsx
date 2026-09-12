import { ChevronDown, Copy, Pencil, Plus, Trash } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import { STARTER_PROMPTS, type PromptLibrary, type SavedPrompt } from "@/lib/prompt-library";

export function PromptLibraryPanel() {
  const [library, setLibrary] = useState<PromptLibrary | null>(null);
  const [loadAttempt, setLoadAttempt] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conflict, setConflict] = useState(false);
  const [notice, setNotice] = useState("");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [editing, setEditing] = useState<(SavedPrompt & { isNew?: boolean }) | null>(null);

  useEffect(() => {
    let active = true;
    api.get<PromptLibrary>("/prompt-library").then((result) => {
      if (!active) return;
      setLibrary(result);
      setLoading(false);
    }).catch(() => {
      if (!active) return;
      setError("Could not load your prompts. Try again.");
      setLoading(false);
    });
    return () => { active = false; };
  }, [loadAttempt]);

  const prompts = library?.prompts ?? STARTER_PROMPTS;

  function reload() {
    setError(null);
    setConflict(false);
    setLoading(true);
    setLoadAttempt((attempt) => attempt + 1);
  }

  async function save(next: SavedPrompt[]) {
    if (!library || saving) return false;
    setSaving(true);
    setError(null);
    try {
      const result = await api.put<PromptLibrary>("/prompt-library", {
        expected_version: library.version,
        prompts: next,
      });
      setLibrary(result);
      setNotice("Saved to your personal library.");
      return true;
    } catch (failure) {
      const stale = failure instanceof ApiError && failure.status === 409;
      setConflict(stale);
      setError(stale
        ? "Your library changed elsewhere. Reload the latest version, then save your edit again."
        : "Could not save your prompts. Your edit is still here; try again.");
      return false;
    } finally {
      setSaving(false);
    }
  }

  async function saveEdit() {
    if (!editing || !editing.title.trim() || !editing.text.trim()) return;
    const prompt = { id: editing.id, title: editing.title.trim(), text: editing.text.trim() };
    // A prompt removed on another device must be re-added explicitly, not lost silently.
    const exists = prompts.some((item) => item.id === prompt.id);
    const next = exists ? prompts.map((item) => item.id === prompt.id ? prompt : item) : [...prompts, prompt];
    if (await save(next)) setEditing(null);
  }

  async function copy(prompt: SavedPrompt) {
    try {
      await navigator.clipboard.writeText(prompt.text);
      setNotice(`Copied ${prompt.title}.`);
    } catch {
      setError("Could not copy. Expand the prompt and select its text to copy it manually.");
    }
  }

  function newPrompt() {
    const prompt = { id: crypto.randomUUID(), title: "", text: "", isNew: true };
    setEditing(prompt);
    setExpanded((current) => new Set(current).add(prompt.id));
    setNotice("");
  }

  const rows = editing && !prompts.some((item) => item.id === editing.id)
    ? [...prompts, editing] : prompts;

  return (
    <section aria-label="Personal prompt library">
      <div className="flex items-center justify-between gap-2 border-b px-1.5 py-2">
        <h2 className="text-sm font-medium">Prompts</h2>
        <Button variant="ghost" size="sm" onClick={newPrompt} disabled={loading || !library || saving || Boolean(editing) || prompts.length >= 100}>
          <Plus className="size-3.5" aria-hidden /> New prompt
        </Button>
      </div>
      {error ? <div role="alert" className="px-2 py-3 text-sm text-destructive">
        <p>{error}</p>
        {(!library || conflict) && <Button variant="outline" size="sm" className="mt-2" onClick={reload} disabled={loading}>Reload prompts</Button>}
      </div> : null}
      <p role="status" className={notice ? "px-2 py-2 text-xs text-muted-foreground" : "sr-only"}>{notice}</p>
      {loading ? <p className="px-2 py-3 text-sm text-muted-foreground">Loading prompts…</p> : library ? <>
        {rows.length === 0 ? <p className="px-2 py-4 text-sm text-muted-foreground">No saved prompts. Create a prompt to keep it here.</p> : null}
        {rows.map((prompt) => {
          const isOpen = expanded.has(prompt.id);
          const isEditing = editing?.id === prompt.id;
          const title = prompt.title || "New prompt";
          return <div key={prompt.id} className="border-b">
            <div className="flex items-center gap-0.5 px-1">
              <button type="button" aria-expanded={isOpen} aria-controls={`prompt-${prompt.id}`} onClick={() => setExpanded((current) => {
                const next = new Set(current);
                if (next.has(prompt.id)) next.delete(prompt.id); else next.add(prompt.id);
                return next;
              })} className="flex min-w-0 flex-1 items-center gap-2 rounded-sm px-1 py-3 text-left text-sm hover:bg-[var(--cockpit-selected-surface)] focus-visible:outline-2 focus-visible:outline-[var(--cockpit-focus)]">
                <ChevronDown className={`size-3.5 shrink-0 ${isOpen ? "" : "-rotate-90"}`} aria-hidden />
                <span className="min-w-0 break-words">{title}</span>
              </button>
              <Button variant="ghost" size="icon-xs" aria-label={`Copy ${title}`} title="Copy prompt" disabled={isEditing} onClick={() => void copy(prompt)}><Copy className="size-3.5" aria-hidden /></Button>
              <Button variant="ghost" size="icon-xs" aria-label={`Edit ${title}`} title="Edit prompt" disabled={saving || Boolean(editing)} onClick={() => { setEditing({ ...prompt }); setExpanded((current) => new Set(current).add(prompt.id)); }}><Pencil className="size-3.5" aria-hidden /></Button>
              <Button variant="ghost" size="icon-xs" aria-label={`Delete ${title}`} title="Delete prompt" disabled={saving || Boolean(editing) || conflict} onClick={() => {
                if (window.confirm(`Delete "${title}" from your personal prompts?`)) void save(prompts.filter((item) => item.id !== prompt.id));
              }}><Trash className="size-3.5" aria-hidden /></Button>
            </div>
            <div id={`prompt-${prompt.id}`} hidden={!isOpen} className="px-2 pb-3">
              {isEditing ? <form className="space-y-3" onSubmit={(event) => { event.preventDefault(); void saveEdit(); }}>
                <label className="block text-xs">Topic<Input autoFocus className="mt-1" value={editing.title} maxLength={120} required disabled={saving} onChange={(event) => setEditing({ ...editing, title: event.target.value })} /></label>
                <label className="block text-xs">Prompt<textarea className="mt-1 min-h-64 w-full resize-y rounded-md border bg-transparent px-3 py-2 text-sm leading-relaxed focus-visible:outline-2 focus-visible:outline-[var(--cockpit-focus)]" value={editing.text} maxLength={12000} required disabled={saving} onChange={(event) => setEditing({ ...editing, text: event.target.value })} /></label>
                <div className="flex gap-2">
                  <Button type="submit" size="sm" disabled={saving || conflict || !editing.title.trim() || !editing.text.trim()}>{saving ? "Saving…" : "Save"}</Button>
                  <Button type="button" variant="ghost" size="sm" disabled={saving} onClick={() => setEditing(null)}>Cancel</Button>
                </div>
              </form> : <p className="whitespace-pre-wrap break-words text-sm leading-relaxed text-[var(--sw-text-secondary)]">{prompt.text}</p>}
            </div>
          </div>;
        })}
      </> : null}
    </section>
  );
}
