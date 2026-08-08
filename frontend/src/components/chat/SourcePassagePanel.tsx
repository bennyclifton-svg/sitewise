import { ExternalLink } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { isWebSourceType, sourceTypeStyle } from "@/lib/citations";
import type { Citation } from "@/lib/types/citation";
import { cn } from "@/lib/utils";

type SourcePassagePanelProps = {
  citation: Citation | null;
};

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[5.5rem_1fr] gap-2 text-sm">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-medium break-words">{value}</dd>
    </div>
  );
}

export function SourcePassagePanel({ citation }: SourcePassagePanelProps) {
  if (!citation) {
    return (
      <aside className="rounded-lg border border-dashed p-4">
        <h2 className="text-sm font-semibold">Source passage</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Click a citation chip on an assistant answer to verify the excerpt here.
        </p>
      </aside>
    );
  }

  const style = sourceTypeStyle(citation.sourceType);
  const isWeb = isWebSourceType(citation.sourceType);

  return (
    <aside
      className={cn("rounded-lg border p-4", style.panelClassName)}
      aria-label="Source passage details"
    >
      <div className="flex items-start justify-between gap-3">
        <h2 className="text-sm font-semibold">
          {isWeb ? "Web source details" : "Source passage"}
        </h2>
        <Badge variant="outline" className="shrink-0">
          {style.label}
        </Badge>
      </div>

      <dl className="mt-4 space-y-2">
        {isWeb ? (
          <>
            {citation.publisher ? (
              <MetaRow label="Publisher" value={citation.publisher} />
            ) : null}
            {citation.jurisdiction ? (
              <MetaRow label="Jurisdiction" value={citation.jurisdiction} />
            ) : null}
            {citation.versionStatus ? (
              <MetaRow label="Version" value={citation.versionStatus} />
            ) : null}
            {citation.effectiveDate ? (
              <MetaRow label="Effective" value={citation.effectiveDate} />
            ) : null}
            {citation.retrievedAt ? (
              <MetaRow label="Retrieved" value={citation.retrievedAt} />
            ) : null}
            <MetaRow label="Source" value={citation.title} />
          </>
        ) : (
          <>
            <MetaRow label="Project" value={citation.project} />
            {citation.phase ? <MetaRow label="Phase" value={citation.phase} /> : null}
            <MetaRow label="Document" value={citation.title} />
          </>
        )}
        {citation.pageOrSection ? (
          <MetaRow label="Location" value={citation.pageOrSection} />
        ) : null}
        {!isWeb && citation.label ? (
          <MetaRow label="Label" value={citation.label} />
        ) : null}
      </dl>

      {isWeb && citation.url ? (
        <a
          href={citation.url}
          target="_blank"
          rel="noreferrer noopener"
          className="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-[var(--sw-beam)] underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          Open official source
          <ExternalLink className="size-3.5" aria-hidden />
        </a>
      ) : null}

      <div className="mt-4">
        <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
          Excerpt
        </p>
        <blockquote className="mt-2 rounded-md border bg-background/80 px-3 py-2 text-sm leading-relaxed whitespace-pre-wrap">
          {citation.excerpt}
        </blockquote>
      </div>
    </aside>
  );
}
