import { FileText, Globe2 } from "lucide-react";

import { isWebSourceType, sourceTypeStyle } from "@/lib/citations";
import type { Citation } from "@/lib/types/citation";
import { cn } from "@/lib/utils";

type CitationChipProps = {
  citation: Citation;
  index: number;
  selected?: boolean;
  onSelect: (citation: Citation) => void;
};

export function CitationChip({
  citation,
  index,
  selected = false,
  onSelect,
}: CitationChipProps) {
  const style = sourceTypeStyle(citation.sourceType);
  const SourceIcon = isWebSourceType(citation.sourceType) ? Globe2 : FileText;

  return (
    <button
      type="button"
      onClick={() => onSelect(citation)}
      className={cn(
        "inline-flex max-w-full items-center gap-1.5 rounded-full border px-2.5 py-1 text-left text-xs font-medium transition-colors",
        style.chipClassName,
        selected && "ring-2 ring-ring ring-offset-2 ring-offset-background",
      )}
      aria-pressed={selected}
      aria-label={`Citation ${index + 1}: ${citation.title}`}
    >
      <SourceIcon className="size-3 shrink-0 opacity-70" aria-hidden />
      <span className="truncate">
        [{index + 1}] {citation.title}
      </span>
    </button>
  );
}
