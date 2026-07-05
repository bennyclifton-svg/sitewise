export type MarkdownSectionSlice = {
  heading: string;
  start: number;
  end: number;
};

const HEADING_RE = /^##\s+(.+?)\s*$/;

export function splitMarkdownSections(markdown: string): MarkdownSectionSlice[] {
  const lines = markdown.split("\n");
  const sections: MarkdownSectionSlice[] = [];
  let offset = 0;
  let current: MarkdownSectionSlice | null = null;

  for (const line of lines) {
    const match = HEADING_RE.exec(line);
    if (match) {
      if (current) {
        current.end = offset;
        sections.push(current);
      }
      current = {
        heading: match[1].trim(),
        start: offset,
        end: markdown.length,
      };
    }
    offset += line.length + 1;
  }

  if (current) {
    current.end = markdown.length;
    sections.push(current);
  }

  return sections;
}

export function spliceMarkdownSection(
  markdown: string,
  section: MarkdownSectionSlice,
  replacement: string,
): string {
  const normalized = replacement.endsWith("\n") ? replacement : `${replacement}\n`;
  return markdown.slice(0, section.start) + normalized + markdown.slice(section.end);
}
