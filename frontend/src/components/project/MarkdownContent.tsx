import type { Components } from "react-markdown";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const components: Components = {
  h1: ({ children }) => (
    <h1 className="mb-4 text-2xl font-semibold leading-tight">{children}</h1>
  ),
  h2: ({ children }) => (
    <h2 className="mt-8 border-b pb-2 text-lg font-semibold first:mt-0">
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="mt-5 text-base font-semibold">{children}</h3>
  ),
  h4: ({ children }) => (
    <h4 className="mt-4 text-sm font-semibold">{children}</h4>
  ),
  p: ({ children }) => <p className="my-3 leading-relaxed">{children}</p>,
  a: ({ children, href }) => (
    <a className="font-medium text-primary underline underline-offset-2" href={href}>
      {children}
    </a>
  ),
  blockquote: ({ children }) => (
    <blockquote className="my-4 border-l-2 pl-4 text-muted-foreground">{children}</blockquote>
  ),
  hr: () => <hr className="my-6 border-border" />,
  ul: ({ children }) => (
    <ul className="my-3 list-disc space-y-1.5 pl-5 leading-relaxed">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="my-3 list-decimal space-y-1.5 pl-5 leading-relaxed">{children}</ol>
  ),
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
  code: ({ children }) => (
    <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">{children}</code>
  ),
  table: ({ children }) => (
    <div className="my-4 overflow-x-auto rounded-md border">
      <table className="w-full min-w-[36rem] border-collapse text-left text-sm">
        {children}
      </table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-muted/50">{children}</thead>,
  th: ({ children }) => (
    <th className="border-b px-3 py-2 align-top font-medium text-foreground">{children}</th>
  ),
  td: ({ children }) => (
    <td className="border-b px-3 py-2 align-top text-foreground">{children}</td>
  ),
  tr: ({ children }) => <tr className="even:bg-muted/20">{children}</tr>,
};

function normalizeDraftMarkdown(markdown: string): string {
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

export function MarkdownContent({ markdown }: { markdown: string }) {
  const normalized = normalizeDraftMarkdown(markdown);
  return (
    <div className="draft-markdown text-sm text-foreground">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {normalized}
      </ReactMarkdown>
    </div>
  );
}
