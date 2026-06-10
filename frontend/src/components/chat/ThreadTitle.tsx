import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";

type ThreadTitleProps = {
  threadId: string;
  initialTitle: string | null;
  onTitleChange?: (title: string) => void;
};

export function ThreadTitle({ threadId, initialTitle, onTitleChange }: ThreadTitleProps) {
  const [savedTitle, setSavedTitle] = useState<string | null>(null);
  const title = savedTitle ?? initialTitle ?? "Untitled chat";
  const [draft, setDraft] = useState(title);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    const trimmed = draft.trim();
    if (!trimmed || trimmed === title) {
      setIsEditing(false);
      setDraft(title);
      return;
    }

    setIsSaving(true);
    setError(null);
    try {
      const updated = await api.updateThreadTitle(threadId, trimmed);
      const nextTitle = updated.title ?? trimmed;
      setSavedTitle(nextTitle);
      setDraft(nextTitle);
      setIsEditing(false);
      onTitleChange?.(nextTitle);
    } catch (saveError) {
      setError(
        saveError instanceof ApiError
          ? saveError.message
          : "Could not save the conversation title.",
      );
    } finally {
      setIsSaving(false);
    }
  }

  if (isEditing) {
    return (
      <form
        className="flex flex-wrap items-center gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          void handleSave();
        }}
      >
        <Input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          className="max-w-md"
          aria-label="Conversation title"
          disabled={isSaving}
          autoFocus
        />
        <Button type="submit" size="sm" disabled={isSaving || draft.trim() === ""}>
          {isSaving ? "Saving…" : "Save"}
        </Button>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          disabled={isSaving}
          onClick={() => {
            setDraft(title);
            setIsEditing(false);
            setError(null);
          }}
        >
          Cancel
        </Button>
        {error ? (
          <p className="w-full text-sm text-destructive" role="alert">
            {error}
          </p>
        ) : null}
      </form>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      <Button
        type="button"
        size="sm"
        variant="ghost"
        onClick={() => {
          setDraft(title);
          setIsEditing(true);
        }}
        aria-label="Edit conversation title"
      >
        Edit
      </Button>
    </div>
  );
}
