import { describe, expect, it } from "vitest";

import { splitMarkdownSections, spliceMarkdownSection } from "@/lib/markdown-sections";

const MARKDOWN = `# Title

## First

Alpha body

## Second

Beta body
`;

describe("splitMarkdownSections", () => {
  it("finds h2 section boundaries", () => {
    const sections = splitMarkdownSections(MARKDOWN);
    expect(sections).toHaveLength(2);
    expect(sections[0]?.heading).toBe("First");
    expect(sections[1]?.heading).toBe("Second");
    expect(MARKDOWN.slice(sections[0]?.start ?? 0, sections[0]?.end ?? 0)).toContain("Alpha body");
  });

  it("splices one section without changing others", () => {
    const sections = splitMarkdownSections(MARKDOWN);
    const first = sections[0];
    if (!first) throw new Error("missing section");
    const updated = spliceMarkdownSection(MARKDOWN, first, "## First\n\nGamma body\n");
    expect(updated).toContain("Gamma body");
    expect(updated).toContain("Beta body");
    expect(updated).not.toContain("Alpha body");
  });
});
