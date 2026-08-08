import { ChevronRight } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import type {
  PlatformKnowledgeBucket,
  PlatformKnowledgeDocument,
  PlatformKnowledgeStatus,
} from "@/lib/types/project";
import { cn } from "@/lib/utils";

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
  const [expandedKinds, setExpandedKinds] = useState<Set<string>>(() => new Set(["seed"]));

  if (!filtered.length) {
    return (
      <p className="px-1.5 text-xs text-muted-foreground">
        {mode === "skills"
          ? "No indexed SiteWise skills yet."
          : "No indexed doctrine, seed, or template material yet."}
      </p>
    );
  }

  function toggleKind(kind: string) {
    setExpandedKinds((current) => {
      const next = new Set(current);
      if (next.has(kind)) next.delete(kind);
      else next.add(kind);
      return next;
    });
  }

  return (
    <ul>
      {filtered.map((bucket) => (
        <KnowledgeBucketRow
          key={bucket.kind}
          bucket={bucket}
          expanded={expandedKinds.has(bucket.kind)}
          onToggle={() => toggleKind(bucket.kind)}
        />
      ))}
    </ul>
  );
}

function KnowledgeBucketRow({
  bucket,
  expanded,
  onToggle,
}: {
  bucket: PlatformKnowledgeBucket;
  expanded: boolean;
  onToggle: () => void;
}) {
  const documents = bucket.documents ?? [];
  const hasDocuments = documents.length > 0;

  return (
    <li>
      {hasDocuments ? (
        <button
          type="button"
          className="flex h-[22px] w-full items-center gap-1 rounded-sm px-1.5 text-left text-xs text-muted-foreground transition-colors hover:bg-muted/70"
          aria-label={expanded ? `Collapse ${bucket.kind}` : `Expand ${bucket.kind}`}
          aria-expanded={expanded}
          onClick={onToggle}
        >
          <ChevronRight
            className={cn("size-3 shrink-0 transition-transform", expanded && "rotate-90")}
            aria-hidden
          />
          <span className="min-w-0 flex-1 truncate capitalize">{bucket.kind}</span>
          <Badge variant="secondary" className="h-4 px-1 text-[10px] font-normal">
            {bucket.document_count}
          </Badge>
        </button>
      ) : (
        <div className="flex h-[22px] items-center gap-1 rounded-sm px-1.5 text-xs text-muted-foreground">
          <span className="size-3 shrink-0" aria-hidden />
          <span className="min-w-0 flex-1 truncate capitalize">{bucket.kind}</span>
          <Badge variant="secondary" className="h-4 px-1 text-[10px] font-normal">
            {bucket.document_count}
          </Badge>
        </div>
      )}
      {hasDocuments && expanded ? (
        <ul className="pb-0.5">
          {documents.map((document) => (
            <li
              key={document.relative_path}
              className="flex h-[22px] items-center truncate pl-7 pr-1.5 text-xs text-muted-foreground"
              title={document.relative_path}
            >
              {documentLabel(document, bucket.kind)}
            </li>
          ))}
        </ul>
      ) : null}
    </li>
  );
}

function documentLabel(document: PlatformKnowledgeDocument, kind: string): string {
  const normalized = document.relative_path.replaceAll("\\", "/");
  const prefixes = [`${kind}/`, `${kind}s/`];
  for (const prefix of prefixes) {
    if (normalized.startsWith(prefix)) {
      return normalized.slice(prefix.length);
    }
  }
  return document.filename || normalized.split("/").pop() || normalized;
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
