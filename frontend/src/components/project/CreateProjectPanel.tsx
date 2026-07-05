import { FolderPlus, LoaderCircle } from "lucide-react";
import { useMemo, useState } from "react";

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

import {
  projectRoleOptions,
  projectStateOptions,
} from "@/lib/project-overlays";

export function CreateProjectPanel({
  onCreated,
}: {
  onCreated: (project: ProjectDetail) => void;
}) {
  const [title, setTitle] = useState("");
  const [slug, setSlug] = useState("");
  const [taxonomy, setTaxonomy] = useState<TaxonomyPickerValue>({});
  const [userRole, setUserRole] = useState("architect-pm");
  const [state, setState] = useState("NSW");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const taxonomyQuery = useTaxonomy();
  const generatedSlug = useMemo(() => slugFromTitle(title), [title]);
  const effectiveSlug = slug.trim() || generatedSlug;

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
        slug: slug.trim() || undefined,
        ...taxonomyInput,
        user_role: userRole,
        state,
        phase: "brief-planning",
      });
      onCreated(project);
      setTitle("");
      setSlug("");
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
    <section className="rounded-md border bg-background">
      <header className="border-b px-4 py-3">
        <div className="flex items-center gap-2">
          <FolderPlus className="size-4 text-muted-foreground" aria-hidden />
          <h2 className="text-base font-semibold">Create project</h2>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          Starts a hosted SiteWise workspace with the standard template folders.
        </p>
      </header>

      <form className="grid gap-4 p-4" onSubmit={(event) => void handleSubmit(event)}>
        <div className="grid gap-2">
          <Label htmlFor="project-title">Project title</Label>
          <Input
            id="project-title"
            value={title}
            placeholder="Petersham renovation"
            onChange={(event) => setTitle(event.target.value)}
          />
        </div>

        <div className="grid gap-2">
          <Label htmlFor="project-slug">Slug</Label>
          <Input
            id="project-slug"
            value={slug}
            placeholder={generatedSlug || "generated-from-title"}
            onChange={(event) => setSlug(event.target.value)}
          />
          <p className="text-xs text-muted-foreground">
            Workspace path: `04-projects/{effectiveSlug || "project-slug"}`
          </p>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <SelectField
            id="project-role"
            label="Role"
            value={userRole}
            onChange={setUserRole}
            options={projectRoleOptions}
          />
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
  options: Array<{ value: string; label: string }>;
  onChange: (value: string) => void;
}) {
  return (
    <div className="grid gap-2">
      <Label htmlFor={id}>{label}</Label>
      <select
        id={id}
        value={value}
        className="h-9 rounded-md border border-input bg-background px-2.5 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
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

function slugFromTitle(value: string): string {
  const slug = value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return slug || "";
}

