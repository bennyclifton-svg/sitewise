export type RegisterCitationLayout = {
  dropColumnIndexes: number[];
  citationColumnIndex: number | null;
  appendCitation: boolean;
  blankCitationHeader: boolean;
};

const CITATION_TOKEN_RE = /\[(\d+)\]/g;

export function extractCitationTokens(text: string): string {
  const seen = new Set<string>();
  const tokens: string[] = [];
  for (const match of text.matchAll(CITATION_TOKEN_RE)) {
    const token = `[${match[1]}]`;
    if (seen.has(token)) continue;
    seen.add(token);
    tokens.push(token);
  }
  return tokens.join(" ");
}

export function stripCitationTokens(text: string): string {
  return text.replace(CITATION_TOKEN_RE, " ").replace(/\s+/g, " ").trim();
}

export function isCitationCellValue(text: string): boolean {
  const value = text.trim();
  return (
    value === "" ||
    value === "—" ||
    value === "-" ||
    value === "–" ||
    /^(?:\[\d+\](?:\s+\[\d+\])*)$/.test(value)
  );
}

function normalizeHeaders(headers: readonly string[]): string[] {
  return headers.map((header) => header.trim().toLowerCase().replace(/\s+/g, " "));
}

export function citationColumnIndexFromHeaders(
  headers: readonly string[],
): number | null {
  const normalized = normalizeHeaders(headers);
  const named = normalized.findIndex(
    (header) => header === "citation" || header === "ref",
  );
  if (named >= 0) return named;
  const last = normalized.at(-1);
  if (last === "") return headers.length - 1;
  return null;
}

export function briefTableLayoutFromHeaders(
  headers: readonly string[],
): RegisterCitationLayout | null {
  const normalized = normalizeHeaders(headers);
  if (!normalized.includes("item") || !normalized.includes("position")) {
    return null;
  }
  if (normalized.includes("location") && normalized.includes("finish")) {
    return null;
  }
  const dropColumnIndexes: number[] = [];
  const basisIndex = normalized.findIndex(
    (header) =>
      header === "basis / source" ||
      header === "basis/source" ||
      header === "source",
  );
  const hasOwner = normalized.includes("owner");
  const hasAction = normalized.some(
    (header) => header.includes("verification") || header === "next action",
  );
  if (basisIndex >= 0 && hasOwner && hasAction && normalized.length >= 5) {
    dropColumnIndexes.push(basisIndex);
  }
  const citationColumnIndex = citationColumnIndexFromHeaders(headers);
  return {
    dropColumnIndexes,
    citationColumnIndex,
    appendCitation: citationColumnIndex === null,
    blankCitationHeader: true,
  };
}

function trailingCitationLayout(
  headers: readonly string[],
): RegisterCitationLayout {
  const citationColumnIndex = citationColumnIndexFromHeaders(headers);
  return {
    dropColumnIndexes: [],
    citationColumnIndex,
    appendCitation: citationColumnIndex === null,
    blankCitationHeader: true,
  };
}

export function planningTableLayoutFromHeaders(
  headers: readonly string[],
): RegisterCitationLayout | null {
  const normalized = normalizeHeaders(headers);
  if (normalized.includes("discipline") && normalized.includes("firm")) {
    return null;
  }
  if (normalized.includes("item") && normalized.includes("position")) {
    return null;
  }
  if (
    normalized.includes("item") &&
    normalized.includes("location") &&
    normalized.includes("finish")
  ) {
    return null;
  }
  const looksNamedPlanning = normalized.some(
    (header) =>
      header.includes("compliance") ||
      header.includes("approval") ||
      header.includes("authority"),
  );
  const looksDueDiligence =
    normalized.includes("item") &&
    normalized.includes("status") &&
    normalized.some(
      (header) => header.includes("next") || header.includes("verification"),
    );
  if (
    !(
      (looksNamedPlanning && normalized.includes("status")) ||
      looksDueDiligence
    )
  ) {
    return null;
  }
  return trailingCitationLayout(headers);
}

export function pmpRegisterTableLayoutFromHeaders(
  headers: readonly string[],
): RegisterCitationLayout | null {
  const planning = planningTableLayoutFromHeaders(headers);
  if (planning) return planning;
  const normalized = normalizeHeaders(headers);
  if (normalized.includes("item") && normalized.includes("position")) {
    return null;
  }
  if (
    normalized.includes("item") &&
    normalized.includes("location") &&
    normalized.includes("finish")
  ) {
    return null;
  }
  if (normalized.includes("discipline") && normalized.includes("firm")) {
    return null;
  }
  if (
    normalized.some((header) => header.includes("milestone")) ||
    normalized.includes("risk")
  ) {
    return trailingCitationLayout(headers);
  }
  const looksActionRegister =
    normalized.includes("item") &&
    (normalized.includes("owner") || normalized.includes("status")) &&
    normalized.some(
      (header) =>
        header.includes("next") || header === "due" || header === "due basis",
    );
  if (looksActionRegister) return trailingCitationLayout(headers);
  return null;
}
