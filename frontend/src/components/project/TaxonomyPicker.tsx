import { useEffect } from "react";

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
};

export function TaxonomyPicker({
  catalog,
  value,
  onChange,
  disabled = false,
  idPrefix = "taxonomy",
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

  useEffect(() => {
    if (!catalog || !selectedClassValue || !value.work_type) return;
    const nextDimensions = catalog.complexity_dimensions[selectedClassValue] ?? [];
    if (nextDimensions.length === 0) return;
    const nextComplexity = defaultComplexity(value.complexity, nextDimensions);
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
    onChange({
      building_class: buildingClass.value,
      work_type: null,
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
      complexity: defaultComplexity({}, catalog?.complexity_dimensions[value.building_class ?? ""] ?? []),
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
    onChange({
      ...value,
      complexity: {
        ...(value.complexity ?? {}),
        [key]: optionValue,
      },
    });
  }

  const otherSelected = selectedSubclassValues.includes("other");
  const otherLabel = selectedOtherLabel(value.subclasses);

  return (
    <div className="grid gap-4">
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
                "rounded-md border px-3 py-2 text-left text-sm transition-colors hover:bg-muted/50",
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
          <h3 className="text-sm font-medium">Work type</h3>
          <div className="flex flex-wrap gap-2">
            {workTypes.map((workType) => (
              <button
                key={workType.value}
                type="button"
                disabled={disabled}
                aria-pressed={value.work_type === workType.value}
                className={cn(
                  "rounded-md border px-3 py-2 text-sm transition-colors hover:bg-muted/50",
                  value.work_type === workType.value &&
                    "border-primary bg-primary/5 text-primary",
                )}
                onClick={() => selectWorkType(workType.value)}
              >
                {workType.label}
              </button>
            ))}
          </div>
        </section>
      ) : null}

      {selectedClass && value.work_type ? (
        <section className="grid gap-3 lg:grid-cols-3" aria-label="Project profile">
          <div className="grid content-start gap-3 rounded-md border p-3">
            <h3 className="text-sm font-medium">Subclass</h3>
            <div className="grid gap-2">
              {selectedClass.subclasses.map((subclass) => {
                const checked = selectedSubclassValues.includes(subclass.value);
                const inputId = `${idPrefix}-subclass-${subclass.value}`;
                return (
                  <div key={subclass.value} className="grid gap-2">
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

          <div className="grid content-start gap-3 rounded-md border p-3">
            <h3 className="text-sm font-medium">Scale</h3>
            {scaleFields.length ? (
              <div className="grid gap-3">
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
                    <div key={field.key} className="grid gap-1.5">
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

          <div className="grid content-start gap-3 rounded-md border p-3">
            <h3 className="text-sm font-medium">Complexity</h3>
            <div className="grid gap-3">
              {dimensions.map((dimension) => {
                const selectId = `${idPrefix}-complexity-${dimension.key}`;
                const selectedValue =
                  value.complexity?.[dimension.key] ??
                  dimension.options[0]?.value ??
                  "";
                return (
                  <div key={dimension.key} className="grid gap-1.5">
                    <Label htmlFor={selectId}>{dimension.label}</Label>
                    <select
                      id={selectId}
                      value={selectedValue}
                      disabled={disabled}
                      className="h-9 rounded-md border border-input bg-background px-2.5 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                      onChange={(event) =>
                        updateComplexity(dimension.key, event.target.value)
                      }
                    >
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

function defaultComplexity(
  current: Record<string, string> | undefined,
  dimensions: ComplexityDimension[],
): Record<string, string> {
  const next: Record<string, string> = {};
  for (const dimension of dimensions) {
    const currentValue = current?.[dimension.key];
    const validValues = new Set(dimension.options.map((option) => option.value));
    next[dimension.key] =
      currentValue && validValues.has(currentValue)
        ? currentValue
        : (dimension.options[0]?.value ?? "");
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
