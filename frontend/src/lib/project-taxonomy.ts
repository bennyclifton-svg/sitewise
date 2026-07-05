import type {
  ProjectDetail,
  ProjectSubclassSelection,
  ProjectTaxonomyInput,
  TaxonomyScalar,
} from "@/lib/types/project";

export function taxonomyValueFromProject(project: ProjectDetail): ProjectTaxonomyInput {
  const taxonomy = project.metadata?.taxonomy ?? {};
  return {
    building_class: project.building_class,
    work_type: project.work_type,
    subclasses: taxonomy.subclasses ?? [],
    scale: taxonomy.scale ?? {},
    complexity: taxonomy.complexity ?? {},
    work_scope: taxonomy.work_scope ?? [],
  };
}

export function compactTaxonomyValue(
  value: ProjectTaxonomyInput,
): ProjectTaxonomyInput {
  const buildingClass = cleanString(value.building_class);
  const workType = cleanString(value.work_type);
  const subclasses = compactSubclasses(value.subclasses);
  const scale = compactScalarRecord(value.scale);
  const complexity = compactStringRecord(value.complexity);
  const workScope = compactStringList(value.work_scope);

  return {
    ...(buildingClass ? { building_class: buildingClass } : {}),
    ...(workType ? { work_type: workType } : {}),
    ...(subclasses.length ? { subclasses } : {}),
    ...(Object.keys(scale).length ? { scale } : {}),
    ...(Object.keys(complexity).length ? { complexity } : {}),
    ...(workScope.length ? { work_scope: workScope } : {}),
  };
}

function compactSubclasses(
  subclasses: ProjectSubclassSelection[] | undefined,
): ProjectSubclassSelection[] {
  const compact: ProjectSubclassSelection[] = [];
  for (const item of subclasses ?? []) {
    if (typeof item === "string") {
      const value = item.trim();
      if (value) compact.push(value);
      continue;
    }
    const value = item.value.trim();
    if (!value) continue;
    const label = item.label?.trim();
    compact.push(label ? { value, label } : { value });
  }
  return compact;
}

function compactScalarRecord(
  value: Record<string, TaxonomyScalar> | undefined,
): Record<string, TaxonomyScalar> {
  const compact: Record<string, TaxonomyScalar> = {};
  for (const [key, item] of Object.entries(value ?? {})) {
    if (!key.trim()) continue;
    if (typeof item === "string" && !item.trim()) continue;
    compact[key] = typeof item === "string" ? item.trim() : item;
  }
  return compact;
}

function compactStringRecord(
  value: Record<string, string> | undefined,
): Record<string, string> {
  const compact: Record<string, string> = {};
  for (const [key, item] of Object.entries(value ?? {})) {
    if (key.trim() && item.trim()) {
      compact[key] = item.trim();
    }
  }
  return compact;
}

function compactStringList(value: string[] | undefined): string[] {
  return (value ?? []).map((item) => item.trim()).filter(Boolean);
}

function cleanString(value: string | null | undefined): string | null {
  const trimmed = value?.trim();
  return trimmed || null;
}
