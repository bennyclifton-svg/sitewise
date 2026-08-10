import { splitMarkdownSections } from "@/lib/markdown-sections";

const ARTIFACT_BLOCK_MARKER =
  /<!--\s*clerk:block\s+id=blk_[a-f0-9]{32}\s*-->/gi;

/** Hide provenance syntax without shifting canonical Markdown offsets. */
export function maskArtifactBlockMarkers(markdown: string): string {
  return markdown.replace(ARTIFACT_BLOCK_MARKER, (marker) =>
    " ".repeat(marker.length),
  );
}

/**
 * Strip the leading `- |` generation artefact from table rows.
 *
 * Must stay byte-identical to `normalize_draft_markdown` in
 * `backend/app/sitewise/markdown_sections.py`: selection anchors use this
 * shared offset space.
 */
export function normalizeDraftMarkdown(markdown: string): string {
  return markdown
    .split("\n")
    .map((line) => {
      const trimmed = line.trimStart();
      if (trimmed.startsWith("- |")) {
        return trimmed.slice(2).trimStart();
      }
      return line;
    })
    .join("\n");
}

export function splitTraceQa(markdown: string): {
  primary: string;
  qa: string | null;
} {
  const sections = splitMarkdownSections(markdown);
  const finalSection = sections.at(-1);
  if (!finalSection || finalSection.heading.trim().toLowerCase() !== "trace & qa") {
    return { primary: markdown, qa: null };
  }
  const qaSection = markdown.slice(finalSection.start, finalSection.end);
  const qa = qaSection.replace(/^##\s+Trace\s*&\s*QA\s*\r?\n?/i, "").trim();
  return {
    primary: markdown.slice(0, finalSection.start).trimEnd(),
    qa,
  };
}
