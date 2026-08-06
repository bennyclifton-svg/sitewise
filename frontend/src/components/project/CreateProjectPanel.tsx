import { FolderPlus, LoaderCircle } from "lucide-react";
import { useState } from "react";

import {
  TaxonomyPicker,
  type TaxonomyPickerValue,
} from "@/components/project/TaxonomyPicker";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import { compactTaxonomyValue } from "@/lib/project-taxonomy";
import { useTaxonomy } from "@/lib/queries/taxonomy";
import type { ProjectDetail } from "@/lib/types/project";

import { projectStateOptions } from "@/lib/project-overlays";

export function CreateProjectPanel({
  onCreated,
}: {
  onCreated: (project: ProjectDetail) => void;
}) {
  const [title, setTitle] = useState("");
  const [taxonomy, setTaxonomy] = useState<TaxonomyPickerValue>({});
  const [state, setState] = useState("NSW");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const taxonomyQuery = useTaxonomy();

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedTitle = title.trim();
    if (!trimmedTitle || submitting) return;

    setSubmitting(true);
    setError(null);
    try {
      const taxonomyInput = compactTaxonomyValue(taxonomy);
      const project = await api.createProject({
        title: trimmedTitle,
        ...taxonomyInput,
        state,
        phase: "brief-planning",
      });
      onCreated(project);
      setTitle("");
      setTaxonomy({});
    } catch (createError) {
      setError(
        createError instanceof ApiError
          ? createError.message
          : "Could not create the project.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="rounded-md border border-border bg-card">
      <header className="border-b px-4 py-3">
        <div className="flex items-center gap-2">
          <FolderPlus
            className="size-4 text-[var(--info-text)]"
            aria-hidden
          />
          <h2 className="text-base font-semibold">Create project</h2>
        </div>
      </header>

      <form className="grid min-w-0 gap-4 p-4" onSubmit={(event) => void handleSubmit(event)}>
        <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_7.5rem] sm:items-end">
          <div className="grid gap-2">
            <Label htmlFor="project-title">Project title</Label>
            <Input
              id="project-title"
              value={title}
              placeholder="Enter project name"
              onChange={(event) => setTitle(event.target.value)}
            />
          </div>
          <SelectField
            id="project-state"
            label="State"
            value={state}
            onChange={setState}
            options={projectStateOptions.map((item) => ({ value: item, label: item }))}
          />
        </div>

        <TaxonomyPicker
          catalog={taxonomyQuery.data}
          value={taxonomy}
          onChange={setTaxonomy}
          disabled={submitting}
          idPrefix="create-project-taxonomy"
          workScopeMode="starter"
        />

        {taxonomyQuery.error ? (
          <p className="text-sm text-destructive" role="alert">
            Project profile options could not load.
          </p>
        ) : null}

        {error ? (
          <p className="text-sm text-destructive" role="alert">
            {error}
          </p>
        ) : null}

        <div className="flex justify-end">
          <Button type="submit" disabled={!title.trim() || submitting}>
            {submitting ? (
              <LoaderCircle className="size-4 animate-spin" aria-hidden />
            ) : (
              <FolderPlus className="size-4" aria-hidden />
            )}
            {submitting ? "Creating" : "Create project"}
          </Button>
        </div>
      </form>
    </section>
  );
}

function SelectField({
  id,
  label,
  value,
  options,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  options: readonly { value: string; label: string }[];
  onChange: (value: string) => void;
}) {
  return (
    <div className="grid min-w-0 gap-2">
      <Label htmlFor={id}>{label}</Label>
      <select
        id={id}
        value={value}
        className="h-9 w-full min-w-0 max-w-full rounded-md border border-input bg-background px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
        onChange={(event) => onChange(event.target.value)}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}

