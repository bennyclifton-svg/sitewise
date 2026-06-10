import { Badge } from "@/components/ui/badge";
import { sourceTypeStyle } from "@/lib/citations";
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

  return (
    <aside
      className={cn("rounded-lg border p-4", style.panelClassName)}
      aria-label="Source passage details"
    >
      <div className="flex items-start justify-between gap-3">
        <h2 className="text-sm font-semibold">Source passage</h2>
        <Badge variant="outline" className="shrink-0">
          {style.label}
        </Badge>
      </div>

      <dl className="mt-4 space-y-2">
        <MetaRow label="Project" value={citation.project} />
        {citation.phase ? <MetaRow label="Phase" value={citation.phase} /> : null}
        <MetaRow label="Document" value={citation.title} />
        {citation.pageOrSection ? (
          <MetaRow label="Location" value={citation.pageOrSection} />
        ) : null}
        {citation.label ? <MetaRow label="Label" value={citation.label} /> : null}
      </dl>

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
