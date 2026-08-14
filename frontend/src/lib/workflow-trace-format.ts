/** Compact inline summary — arrays become counts so chunk refs never blow the row. */
export function formatMetadataSummary(metadata: Record<string, unknown>): string {
  const entries = Object.entries(metadata);
  const scalars = entries.filter(([, value]) => isScalarMetadata(value));
  const rest = entries.filter(([, value]) => !isScalarMetadata(value));
  return [...scalars, ...rest]
    .slice(0, 2)
    .map(([key, value]) => `${key}: ${formatValue(value)}`)
    .join(" · ");
}

function isScalarMetadata(value: unknown): boolean {
  return (
    value === null ||
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean"
  );
}

function formatValue(value: unknown): string {
  if (Array.isArray(value)) return String(value.length);
  if (value === null) return "null";
  if (typeof value === "object") return "object";
  const text = String(value);
  if (text.length > 48) return `${text.slice(0, 45)}…`;
  return text;
}
