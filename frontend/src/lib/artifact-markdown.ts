import { splitMarkdownSections } from "@/lib/markdown-sections";

/** Any clerk:block comment, including truncated or rewritten ids. */
function artifactBlockMarkerRe(): RegExp {
  return /<!--\s*clerk:block\b[^>]*-->/gi;
}

/** Hide provenance syntax without shifting canonical Markdown offsets. */
export function maskArtifactBlockMarkers(markdown: string): string {
  return markdown.replace(artifactBlockMarkerRe(), (marker) =>
    " ".repeat(marker.length),
  );
}

/** Remove provenance syntax from copied or exported Markdown. */
export function stripArtifactBlockMarkers(markdown: string): string {
  return markdown
    .replace(/^[ \t]*<!--\s*clerk:block\b[^>]*-->[ \t]*(?:\r?\n|$)/gim, "")
    .replace(/ ?<!--\s*clerk:block\b[^>]*-->/gi, "");
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
  profileBasis: string | null;
} {
  const sections = splitMarkdownSections(markdown);
  let primary = markdown;
  const qa: string[] = [];
  const basis: string[] = [];
  for (const section of [...sections].reverse()) {
    const heading = section.heading.trim().toLowerCase();
    if (!["trace & qa", "internal audit layer", "profile basis", "profile clarifications", "actions and decisions"].includes(heading)) continue;
    const body = markdown.slice(section.start, section.end).replace(/^##[^\n]*\n?/, "").trim();
    if (heading === "trace & qa" || heading === "internal audit layer") qa.unshift(body);
    else if (heading !== "actions and decisions") basis.unshift(heading === "profile clarifications" ? `### Profile clarifications\n\n${body}` : body);
    // Preserve edit offsets when a review section occurs in the middle of a draft.
    primary = primary.slice(0, section.start) + primary.slice(section.start, section.end).replace(/[^\n]/g, " ") + primary.slice(section.end);
  }
  return { primary, qa: qa.join("\n\n") || null, profileBasis: basis.join("\n\n") || null };
}
