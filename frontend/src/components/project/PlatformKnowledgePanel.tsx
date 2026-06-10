import { Badge } from "@/components/ui/badge";
import type { PlatformKnowledgeStatus } from "@/lib/types/project";

const SKILLS_KINDS = new Set(["skill", "skills"]);
const KNOWLEDGE_KINDS = new Set(["doctrine", "seed", "template"]);

export function PlatformKnowledgePanel({
  platformStatus,
  mode,
}: {
  platformStatus: PlatformKnowledgeStatus | null;
  mode: "skills" | "knowledge";
}) {
  const buckets = platformStatus?.buckets ?? [];
  const allowed = mode === "skills" ? SKILLS_KINDS : KNOWLEDGE_KINDS;
  const filtered = buckets.filter((bucket) => allowed.has(bucket.kind));

  if (!filtered.length) {
    return (
      <p className="px-2 text-xs text-muted-foreground">
        {mode === "skills"
          ? "No indexed SiteWise skills yet."
          : "No indexed doctrine, seed, or template material yet."}
      </p>
    );
  }

  return (
    <ul className="space-y-2 px-1">
      {filtered.map((bucket) => (
        <li
          key={bucket.kind}
          className="flex items-center justify-between gap-2 rounded-md border bg-background px-2.5 py-2 text-xs"
        >
          <span className="font-medium capitalize">{bucket.kind}</span>
          <Badge variant="secondary">{bucket.document_count}</Badge>
        </li>
      ))}
    </ul>
  );
}

export function PlatformKnowledgeSummary({
  platformStatus,
}: {
  platformStatus: PlatformKnowledgeStatus | null;
}) {
  const available = platformStatus?.available ?? false;
  const total = platformStatus?.buckets.reduce((sum, bucket) => sum + bucket.document_count, 0) ?? 0;

  return (
    <div className="space-y-2 px-1 text-xs">
      <div className="flex items-center justify-between rounded-md border px-2.5 py-2">
        <span className="text-muted-foreground">Corpus</span>
        <span className="font-medium">{available ? "Indexed" : "Not indexed"}</span>
      </div>
      <div className="flex items-center justify-between rounded-md border px-2.5 py-2">
        <span className="text-muted-foreground">Documents</span>
        <span className="font-medium">{total}</span>
      </div>
    </div>
  );
}
