import { useEffect, useState } from "react";
import { Check, Copy } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function CopyContentButton({
  content,
  loadContent,
  label = "Copy content",
  className,
  disabled = false,
  size = "icon-xs",
}: ({
  content: string;
  loadContent?: never;
} | {
  content?: never;
  loadContent: () => Promise<string>;
}) & {
  label?: string;
  className?: string;
  disabled?: boolean;
  size?: "icon-xs" | "icon-sm" | "icon";
}) {
  const [copied, setCopied] = useState(false);
  const [isCopying, setIsCopying] = useState(false);

  useEffect(() => {
    if (!copied) return;
    const timer = window.setTimeout(() => setCopied(false), 2000);
    return () => window.clearTimeout(timer);
  }, [copied]);

  async function copyContent() {
    setIsCopying(true);
    let resolvedContent: string;
    try {
      resolvedContent = loadContent ? await loadContent() : content;
    } catch {
      setIsCopying(false);
      return;
    }

    if (!resolvedContent.trim()) {
      setIsCopying(false);
      return;
    }
    try {
      await navigator.clipboard.writeText(resolvedContent);
      setCopied(true);
    } catch {
      const textarea = document.createElement("textarea");
      textarea.value = resolvedContent;
      textarea.setAttribute("readonly", "");
      textarea.style.position = "absolute";
      textarea.style.left = "-9999px";
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
    } finally {
      setIsCopying(false);
    }
  }

  return (
    <Button
      type="button"
      variant="ghost"
      size={size}
      className={cn("shrink-0 text-muted-foreground hover:text-foreground", className)}
      onClick={() => void copyContent()}
      disabled={
        disabled || isCopying || (loadContent === undefined && !content.trim())
      }
      aria-label={copied ? "Copied" : label}
      title={copied ? "Copied" : label}
    >
      {copied ? (
        <Check className="size-3.5 text-[var(--sw-positive)]" aria-hidden />
      ) : (
        <Copy className="size-3.5" aria-hidden />
      )}
    </Button>
  );
}
