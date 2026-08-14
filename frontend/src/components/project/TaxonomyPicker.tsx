import { useEffect, type ReactNode } from "react";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type {
  BuildingClass,
  ComplexityDimension,
  ProjectSubclassSelection,
  ProjectTaxonomyInput,
  ScaleField,
  TaxonomyCatalog,
  TaxonomyScalar,
} from "@/lib/types/project";
import { cn } from "@/lib/utils";

export type TaxonomyPickerValue = ProjectTaxonomyInput;

type TaxonomyPickerProps = {
  catalog: TaxonomyCatalog | null | undefined;
  value: TaxonomyPickerValue;
  onChange: (value: TaxonomyPickerValue) => void;
  disabled?: boolean;
  idPrefix?: string;
  workScopeMode?: "starter" | "fallback";
  budget?: string;
  onBudgetChange?: (value: string) => void;
  scopeNarrative?: string;
  onScopeNarrativeChange?: (value: string) => void;
};

export function TaxonomyPicker({
  catalog,
  value,
  onChange,
  disabled = false,
  idPrefix = "taxonomy",
  workScopeMode = "fallback",
  budget,
  onBudgetChange,
  scopeNarrative,
  onScopeNarrativeChange,
}: TaxonomyPickerProps) {
  const selectedClass = catalog?.building_classes.find(
    (item) => item.value === value.building_class,
  );
  const selectedClassValue = selectedClass?.value;
  const workTypes = catalog?.work_types.filter((workType) =>
    selectedClass?.work_types.includes(workType.value),
  ) ?? [];
  const selectedSubclassValues = subclassValues(value.subclasses);
  const dimensions =
    selectedClassValue && value.work_type
      ? (catalog?.complexity_dimensions[selectedClassValue] ?? [])
      : [];
  const selectedSubclasses = selectedClass?.subclasses.filter((subclass) =>
    selectedSubclassValues.includes(subclass.value),
  ) ?? [];
  const scaleFields = uniqueScaleFields(selectedSubclasses);
  const workScope = value.work_type
    ? catalog?.work_scopes[value.work_type]
    : undefined;
  const selectedWorkScope = new Set(value.work_scope ?? []);

  useEffect(() => {
    if (!catalog || !selectedClassValue || !value.work_type) return;
    const nextDimensions = catalog.complexity_dimensions[selectedClassValue] ?? [];
    if (nextDimensions.length === 0) return;
    const nextComplexity = sanitiseComplexity(value.complexity, nextDimensions);
    if (!recordsEqual(value.complexity ?? {}, nextComplexity)) {
      onChange({ ...value, complexity: nextComplexity });
    }
  }, [catalog, onChange, selectedClassValue, value]);

  if (!catalog) {
    return (
      <div className="rounded-md border border-dashed p-3 text-sm text-muted-foreground">
        Loading project profile options...
      </div>
    );
  }

  function selectBuildingClass(buildingClass: BuildingClass) {
    if (value.building_class === buildingClass.value) return;
    const workTypeStillValid = buildingClass.work_types.includes(
      value.work_type ?? "",
    );
    onChange({
      building_class: buildingClass.value,
      work_type: workTypeStillValid ? value.work_type : null,
      subclasses: [],
      scale: {},
      complexity: {},
      work_scope: [],
    });
  }

  function selectWorkType(workType: string) {
    onChange({
      ...value,
      work_type: workType,
      complexity: {},
      work_scope: [],
    });
  }

  function selectSingleSubclass(subclassValue: string) {
    onChange({
      ...value,
      subclasses: [subclassSelectionForValue(value.subclasses, subclassValue)],
      scale: {},
    });
  }

  function toggleMixedSubclass(subclassValue: string, checked: boolean) {
    const current = value.subclasses ?? [];
    const next = checked
      ? [...current, subclassSelectionForValue(current, subclassValue)]
      : current.filter((item) => subclassValueFor(item) !== subclassValue);
    onChange({
      ...value,
      subclasses: next,
      scale: {},
    });
  }

  function updateOtherLabel(label: string) {
    const otherSelection = { value: "other", label };
    if (selectedClass?.multi_subclass) {
      const current = value.subclasses ?? [];
      const withoutOther = current.filter((item) => subclassValueFor(item) !== "other");
      onChange({
        ...value,
        subclasses: [...withoutOther, otherSelection],
      });
      return;
    }
    onChange({
      ...value,
      subclasses: [otherSelection],
      scale: {},
    });
  }

  function updateScale(field: ScaleField, rawValue: string | boolean) {
    const current = value.scale ?? {};
    const next = { ...current };
    if (rawValue === "") {
      delete next[field.key];
    } else {
      next[field.key] = scaleValue(field, rawValue);
    }
    onChange({ ...value, scale: next });
  }

  function updateComplexity(key: string, optionValue: string) {
    const next = { ...(value.complexity ?? {}) };
    if (optionValue === "") {
      delete next[key];
    } else {
      next[key] = optionValue;
    }
    onChange({ ...value, complexity: next });
  }

  function toggleWorkScope(itemValue: string, checked: boolean) {
    const current = value.work_scope ?? [];
    onChange({
      ...value,
      work_scope: checked
        ? [...current, itemValue]
        : current.filter((item) => item !== itemValue),
    });
  }

  const otherSelected = selectedSubclassValues.includes("other");
  const otherLabel = selectedOtherLabel(value.subclasses);

  return (
    <div className="grid min-w-0 gap-3">
      <section className="grid gap-2" aria-label="Building class">
        <h3 className="text-sm font-medium">Class</h3>
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
          {catalog.building_classes.map((buildingClass) => (
            <button
              key={buildingClass.value}
              type="button"
              disabled={disabled}
              aria-pressed={value.building_class === buildingClass.value}
              className={cn(
                "rounded-md border px-3 py-1.5 text-left text-sm transition-colors hover:bg-muted/50",
                value.building_class === buildingClass.value &&
                  "border-primary bg-primary/5 text-primary",
              )}
              onClick={() => selectBuildingClass(buildingClass)}
            >
              {buildingClass.label}
            </button>
          ))}
        </div>
      </section>

      {selectedClass ? (
        <section className="grid gap-2" aria-label="Work type">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="grid min-w-0 flex-1 gap-2">
              <h3 className="text-sm font-medium">Work type</h3>
              <div className="flex flex-wrap gap-2">
                {workTypes.map((workType) => (
                  <button
                    key={workType.value}
                    type="button"
                    disabled={disabled}
                    aria-pressed={value.work_type === workType.value}
                    className={cn(
                      "rounded-md border px-3 py-1.5 text-sm transition-colors hover:bg-muted/50",
                      value.work_type === workType.value &&
                        "border-primary bg-primary/5 text-primary",
                    )}
                    onClick={() => selectWorkType(workType.value)}
                  >
                    {workType.label}
                  </button>
                ))}
              </div>
            </div>
            {onBudgetChange ? (
              <div className="grid w-full shrink-0 gap-2 sm:w-44">
                <Label htmlFor={`${idPrefix}-budget`}>Budget</Label>
                <Input
                  id={`${idPrefix}-budget`}
                  value={budget ?? ""}
                  disabled={disabled}
                  placeholder="$120m"
                  onChange={(event) => onBudgetChange(event.target.value)}
                />
              </div>
            ) : null}
          </div>
        </section>
      ) : null}

      {selectedClass && value.work_type ? (
        <section
          className="grid min-w-0 gap-2 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,2fr)]"
          aria-label="Project profile"
        >
          <div className="grid min-w-0 content-start gap-2 rounded-md border p-2.5">
            <h3 className="text-sm font-medium">Subclass</h3>
            <div className="grid gap-1.5">
              {selectedClass.subclasses.map((subclass) => {
                const checked = selectedSubclassValues.includes(subclass.value);
                const inputId = `${idPrefix}-subclass-${subclass.value}`;
                return (
                  <div key={subclass.value} className="grid gap-1.5">
                    <label
                      htmlFor={inputId}
                      className="flex items-center gap-2 text-sm"
                    >
                      <input
                        id={inputId}
                        type={selectedClass.multi_subclass ? "checkbox" : "radio"}
                        name={`${idPrefix}-subclass`}
                        checked={checked}
                        disabled={disabled}
                        onChange={(event) => {
                          if (selectedClass.multi_subclass) {
                            toggleMixedSubclass(subclass.value, event.target.checked);
                          } else {
                            selectSingleSubclass(subclass.value);
                          }
                        }}
                      />
                      <span>{subclass.label}</span>
                    </label>
                    {subclass.value === "other" && otherSelected ? (
                      <Input
                        value={otherLabel}
                        disabled={disabled}
                        placeholder="Describe subclass"
                        aria-label="Other subclass"
                        onChange={(event) => updateOtherLabel(event.target.value)}
                      />
                    ) : null}
                  </div>
                );
              })}
            </div>
          </div>

          <div className="grid min-w-0 content-start gap-2 rounded-md border p-2.5">
            <h3 className="text-sm font-medium">Scale</h3>
            {scaleFields.length ? (
              <div className="grid gap-2">
                {scaleFields.map((field) => {
                  const inputId = `${idPrefix}-scale-${field.key}`;
                  const fieldValue = value.scale?.[field.key];
                  if (field.type === "boolean") {
                    return (
                      <label
                        key={field.key}
                        htmlFor={inputId}
                        className="flex items-center gap-2 text-sm"
                      >
                        <input
                          id={inputId}
                          type="checkbox"
                          disabled={disabled}
                          checked={fieldValue === true}
                          onChange={(event) => updateScale(field, event.target.checked)}
                        />
                        <span>{field.label}</span>
                      </label>
                    );
                  }
                  return (
                    <div key={field.key} className="grid gap-1">
                      <Label htmlFor={inputId}>{field.label}</Label>
                      <Input
                        id={inputId}
                        type={field.type === "number" || field.type === "integer" ? "number" : "text"}
                        min={field.min}
                        max={field.max}
                        step={field.type === "integer" ? 1 : undefined}
                        disabled={disabled}
                        value={fieldValue === undefined ? "" : String(fieldValue)}
                        placeholder={field.placeholder ?? field.typical ?? ""}
                        onChange={(event) => updateScale(field, event.target.value)}
                      />
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No scale fields.</p>
            )}
          </div>

          <div className="grid min-w-0 content-start gap-2 rounded-md border p-2.5">
            <h3 className="text-sm font-medium">Complexity</h3>
            <div className="grid min-w-0 gap-2 sm:grid-cols-2">
              {dimensions.map((dimension) => {
                const selectId = `${idPrefix}-complexity-${dimension.key}`;
                const selectedValue = value.complexity?.[dimension.key] ?? "";
                return (
                  <div key={dimension.key} className="grid min-w-0 gap-1">
                    <Label htmlFor={selectId}>{dimension.label}</Label>
                    <select
                      id={selectId}
                      value={selectedValue}
                      disabled={disabled}
                      className="h-8 w-full min-w-0 max-w-full rounded-md border border-input bg-background px-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                      onChange={(event) =>
                        updateComplexity(dimension.key, event.target.value)
                      }
                    >
                      <option value="">Not stated</option>
                      {dimension.options.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </div>
                );
              })}
            </div>
          </div>
        </section>
      ) : null}

      {selectedClass && value.work_type && workScope?.categories.length ? (
        workScopeMode === "starter" ? (
          <WorkScopeFields
            title="Starter work scope"
            description="Use these selections to seed the brief when project documents are sparse."
            categories={workScope.categories}
            selected={selectedWorkScope}
            disabled={disabled}
            idPrefix={idPrefix}
            onToggle={toggleWorkScope}
            notes={
              onScopeNarrativeChange ? (
                <ScopeNotesField
                  id={`${idPrefix}-scope-notes`}
                  value={scopeNarrative ?? ""}
                  disabled={disabled}
                  onChange={onScopeNarrativeChange}
                />
              ) : null
            }
          />
        ) : (
          <details className="rounded-md border p-2.5" open>
            <summary className="cursor-pointer text-sm font-medium">
              Scope
              {selectedWorkScope.size ? ` (${selectedWorkScope.size} selected)` : ""}
            </summary>
            <div className="mt-2">
              <WorkScopeFields
                categories={workScope.categories}
                selected={selectedWorkScope}
                disabled={disabled}
                idPrefix={idPrefix}
                onToggle={toggleWorkScope}
                notes={
                  onScopeNarrativeChange ? (
                    <ScopeNotesField
                      id={`${idPrefix}-scope-notes`}
                      value={scopeNarrative ?? ""}
                      disabled={disabled}
                      onChange={onScopeNarrativeChange}
                    />
                  ) : null
                }
              />
            </div>
          </details>
        )
      ) : null}
    </div>
  );
}

function WorkScopeFields({
  title,
  description,
  categories,
  selected,
  disabled,
  idPrefix,
  onToggle,
  notes,
}: {
  title?: string;
  description?: string;
  categories: NonNullable<TaxonomyCatalog["work_scopes"][string]>["categories"];
  selected: ReadonlySet<string>;
  disabled: boolean;
  idPrefix: string;
  onToggle: (itemValue: string, checked: boolean) => void;
  notes?: ReactNode;
}) {
  return (
    <section className="grid gap-2" aria-label={title ?? "Scope"}>
      {title ? <h3 className="text-sm font-medium">{title}</h3> : null}
      {description ? (
        <p className="text-xs text-muted-foreground">{description}</p>
      ) : null}
      <div className="grid grid-cols-[repeat(auto-fit,minmax(11.5rem,1fr))] gap-2">
        {categories.map((category) => (
          <fieldset key={category.value} className="rounded-md border p-2">
            <legend className="px-1 text-xs font-medium">{category.label}</legend>
            <div className="grid gap-1">
              {category.items.map((item) => {
                const inputId = `${idPrefix}-work-scope-${item.value}`;
                return (
                  <label
                    key={item.value}
                    htmlFor={inputId}
                    className="flex items-start gap-2 text-sm leading-snug"
                  >
                    <input
                      id={inputId}
                      type="checkbox"
                      checked={selected.has(item.value)}
                      disabled={disabled}
                      onChange={(event) =>
                        onToggle(item.value, event.target.checked)
                      }
                    />
                    <span>{item.label}</span>
                  </label>
                );
              })}
            </div>
          </fieldset>
        ))}
      </div>
      {notes}
    </section>
  );
}

function ScopeNotesField({
  id,
  value,
  disabled,
  onChange,
}: {
  id: string;
  value: string;
  disabled: boolean;
  onChange: (value: string) => void;
}) {
  return (
    <div className="grid gap-2">
      <Label htmlFor={id}>Scope notes</Label>
      <textarea
        id={id}
        value={value}
        disabled={disabled}
        placeholder="One item per line"
        rows={4}
        onChange={(event) => onChange(event.target.value)}
        className="min-h-[6rem] w-full min-w-0 rounded-none border border-input bg-[var(--sw-panel)] px-2.5 py-2 text-base outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 md:text-sm"
      />
    </div>
  );
}

function subclassValues(subclasses: ProjectSubclassSelection[] | undefined): string[] {
  return (subclasses ?? [])
    .map((item) => subclassValueFor(item))
    .filter((item): item is string => Boolean(item));
}

function subclassValueFor(item: ProjectSubclassSelection): string | null {
  if (typeof item === "string") return item.trim() || null;
  return item.value.trim() || null;
}

function subclassSelectionForValue(
  current: ProjectSubclassSelection[] | undefined,
  value: string,
): ProjectSubclassSelection {
  const existing = (current ?? []).find((item) => subclassValueFor(item) === value);
  if (existing) return existing;
  return value === "other" ? { value: "other", label: "" } : value;
}

function selectedOtherLabel(
  subclasses: ProjectSubclassSelection[] | undefined,
): string {
  const other = (subclasses ?? []).find((item) => subclassValueFor(item) === "other");
  return typeof other === "object" ? (other.label ?? "") : "";
}

function uniqueScaleFields(subclasses: Array<{ scale_fields: ScaleField[] }>) {
  const fields = new Map<string, ScaleField>();
  for (const subclass of subclasses) {
    for (const field of subclass.scale_fields) {
      if (!fields.has(field.key)) {
        fields.set(field.key, field);
      }
    }
  }
  return [...fields.values()];
}

function scaleValue(field: ScaleField, rawValue: string | boolean): TaxonomyScalar {
  if (typeof rawValue === "boolean") return rawValue;
  if (field.type === "number" || field.type === "integer") {
    const parsed = Number(rawValue);
    return Number.isFinite(parsed) ? parsed : rawValue;
  }
  return rawValue;
}

/**
 * Keep the dimensions the user actually answered and drop the rest.
 *
 * This deliberately does not fall back to `options[0]`. Every dimension's first
 * option is its benign one — vacant, unrestricted, nil contamination, exempt —
 * so defaulting silently asserted that an occupied, restricted, contaminated
 * site was none of those things, before the user had typed anything. Downstream
 * that is indistinguishable from a deliberate answer: risk flags never fire,
 * and the agent cannot correct it, because a stated value is not the agent's to
 * overwrite. An absent key is honest and stays correctable.
 */
function sanitiseComplexity(
  current: Record<string, string> | undefined,
  dimensions: ComplexityDimension[],
): Record<string, string> {
  const next: Record<string, string> = {};
  for (const dimension of dimensions) {
    const currentValue = current?.[dimension.key];
    const validValues = new Set(dimension.options.map((option) => option.value));
    if (currentValue && validValues.has(currentValue)) {
      next[dimension.key] = currentValue;
    }
  }
  return next;
}

function recordsEqual(
  left: Record<string, string>,
  right: Record<string, string>,
): boolean {
  const leftKeys = Object.keys(left);
  const rightKeys = Object.keys(right);
  if (leftKeys.length !== rightKeys.length) return false;
  return leftKeys.every((key) => left[key] === right[key]);
}
