export const MARKDOWN_EXTENSIONS = [".md", ".markdown"] as const;

export function isMarkdownFilename(filename: string): boolean {
  const lower = filename.toLowerCase();
  return MARKDOWN_EXTENSIONS.some((extension) => lower.endsWith(extension));
}
