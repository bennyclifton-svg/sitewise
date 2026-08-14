import type { OverlayIssue } from "@/lib/types/project";

export const projectStateOptions = [
  "NSW",
  "VIC",
  "QLD",
  "SA",
  "WA",
  "TAS",
  "NT",
  "ACT",
] as const;

export function overlayIssuesFromProfile(input: {
  buildingClass?: string | null;
  workType?: string | null;
  state?: string | null;
}): OverlayIssue[] {
  const issues: OverlayIssue[] = [];
  if (!input.buildingClass?.trim()) {
    issues.push({ field: "building_class", value: null, reason: "missing" });
  }
  if (!input.workType?.trim()) {
    issues.push({ field: "work_type", value: null, reason: "missing" });
  }
  if (!input.state?.trim()) {
    issues.push({ field: "state", value: null, reason: "missing" });
  }
  return issues;
}
