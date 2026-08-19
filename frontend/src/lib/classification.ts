export const DOCUMENT_CLASSES = [
  "drawing",
  "specification",
  "report",
  "certificate",
  "correspondence",
  "contract",
  "commercial",
  "schedule",
  "statutory_instrument",
  "photo",
  "unknown",
] as const;

/** Canonical category list. Same values as Python `DocumentSubject`. */
export const DOCUMENT_CATEGORIES = [
  "architect",
  "landscape",
  "interior_design",
  "structural",
  "civil",
  "geotechnical",
  "mechanical",
  "electrical",
  "hydraulic",
  "fire_engineer",
  "fire_services",
  "town_planner",
  "heritage",
  "archaeology",
  "surveyor",
  "quantity_surveyor",
  "certifier",
  "basix",
  "esd",
  "acoustic",
  "access",
  "roof_access",
  "facade",
  "traffic",
  "bca",
  "arborist",
  "ecology",
  "bushfire",
  "cost",
  "programme",
  "contract_admin",
  "defects",
  "none",
] as const;

/** @deprecated Use DOCUMENT_CATEGORIES. Kept so the contract test can rename in one step. */
export const DOCUMENT_SUBJECTS = DOCUMENT_CATEGORIES;

export const REVIEW_CONFIDENCE_MIN = 0.65;

const CATEGORY_LABELS: Record<string, string> = {
  architect: "Architect",
  landscape: "Landscape",
  interior_design: "Interior Design",
  structural: "Structural",
  civil: "Civil",
  geotechnical: "Geotechnical",
  mechanical: "Mechanical",
  electrical: "Electrical",
  hydraulic: "Hydraulic",
  fire_engineer: "Fire Engineer",
  fire_services: "Fire Services",
  town_planner: "Town Planner",
  heritage: "Heritage",
  archaeology: "Archaeology",
  surveyor: "Surveyor",
  quantity_surveyor: "Quantity Surveyor",
  certifier: "Certifier",
  basix: "BASIX",
  esd: "ESD",
  acoustic: "Acoustic",
  access: "Access",
  roof_access: "Roof Access",
  facade: "Facade",
  traffic: "Traffic",
  bca: "BCA",
  arborist: "Arborist",
  ecology: "Ecology",
  bushfire: "Bushfire",
  cost: "Cost",
  programme: "Programme",
  contract_admin: "Contract Admin",
  defects: "Defects",
  none: "None",
};

const CATEGORY_ALIASES: Record<string, string> = {
  architecture: "architect",
  architectural: "architect",
  "architectural services": "architect",
  "landscape architect": "landscape",
  "landscape architectural": "landscape",
  "structural engineer": "structural",
  "structural engineering": "structural",
  civil: "civil",
  "civil engineer": "civil",
  "civil stormwater": "civil",
  "civil / stormwater": "civil",
  stormwater: "civil",
  geotech: "geotechnical",
  "geotechnical engineer": "geotechnical",
  "mechanical engineer": "mechanical",
  "mechanical services": "mechanical",
  "electrical engineer": "electrical",
  "electrical services": "electrical",
  "hydraulic engineer": "hydraulic",
  services: "none",
  fire: "fire_engineer",
  "fire engineer": "fire_engineer",
  "fire engineering": "fire_engineer",
  "fire services": "fire_services",
  planning: "town_planner",
  "town planning": "town_planner",
  "town planner": "town_planner",
  "heritage consultant": "heritage",
  survey: "surveyor",
  "quantity surveyor": "quantity_surveyor",
  "building certifier": "certifier",
  certification: "certifier",
  energy: "basix",
  "energy assessor": "basix",
  "energy assessment": "basix",
  "interior designer": "interior_design",
  "interior design": "interior_design",
  archaeological: "archaeology",
  archaeologist: "archaeology",
  "esd consultant": "esd",
  sustainability: "esd",
  "sustainability consultant": "esd",
  "acoustic consultant": "acoustic",
  "access consultant": "access",
  "roof access consultant": "roof_access",
  "facade engineer": "facade",
  "traffic engineer": "traffic",
  ecologist: "ecology",
  ecological: "ecology",
  ncc: "bca",
  "building code": "bca",
  unassigned: "none",
};

export function classificationLabel(value: string): string {
  return (
    CATEGORY_LABELS[value] ??
    value
      .split("_")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ")
  );
}

function categoryKey(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

export function canonicalCategory(value: string | null | undefined): string {
  const raw = value?.trim() ?? "";
  if (!raw) return "none";
  const key = categoryKey(raw);
  const slug = key.replaceAll(" ", "_");
  if (slug in CATEGORY_LABELS) return slug;
  return CATEGORY_ALIASES[key] ?? "none";
}

export function resolveCategorySlug(input: {
  documentSubject?: string | null;
  category?: string | null;
}): string {
  const fromSubject = canonicalCategory(input.documentSubject);
  if (fromSubject !== "none") return fromSubject;
  return canonicalCategory(input.category);
}

export function documentCategoryLabel(input: {
  documentSubject?: string | null;
  category?: string | null;
}): string {
  const slug = resolveCategorySlug(input);
  if (slug === "none") return "";
  return classificationLabel(slug);
}
