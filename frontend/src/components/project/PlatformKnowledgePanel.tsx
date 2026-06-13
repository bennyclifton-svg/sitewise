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
      <p className="px-1.5 text-xs text-muted-foreground">
        {mode === "skills"
          ? "No indexed SiteWise skills yet."
          : "No indexed doctrine, seed, or template material yet."}
      </p>
    );
  }

  return (
    <ul>
      {filtered.map((bucket) => (
        <li
          key={bucket.kind}
          className="flex h-[22px] items-center justify-between gap-2 rounded-sm px-1.5 text-xs text-muted-foreground"
        >
          <span className="truncate capitalize">{bucket.kind}</span>
          <Badge variant="secondary" className="h-4 px-1 text-[10px] font-normal">
            {bucket.document_count}
          </Badge>
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
    <div className="text-xs text-muted-foreground">
      <div className="flex h-[22px] items-center justify-between rounded-sm px-1.5">
        <span>Corpus</span>
        <span>{available ? "Indexed" : "Not indexed"}</span>
      </div>
      <div className="flex h-[22px] items-center justify-between rounded-sm px-1.5">
        <span>Documents</span>
        <span>{total}</span>
      </div>
    </div>
  );
}
