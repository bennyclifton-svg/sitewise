import { cn } from "@/lib/utils";

const LOCKUP_RATIO = 584 / 129;

type SitewiseMarkProps = {
  /** Rendered mark height in CSS pixels. */
  size?: number;
  /**
   * Kept for callers. The current brand mark is a single solid S.
   */
  variant?: "auto" | "full" | "solid";
  /**
   * Brand stationery clear-space (`size / 3`). Product chrome should
   * pass `false` so the seal sits on the type column, not in a padded tile.
   */
  padded?: boolean;
  className?: string;
  title?: string;
};

/** Current solid S silhouette in the semantic information colour. */
export function SitewiseMark({
  size = 48,
  padded = true,
  className,
  title = "Sitewise",
}: SitewiseMarkProps) {
  const clear = padded ? size / 3 : 0;

  return (
    <span
      className={cn("inline-flex shrink-0 items-center justify-center", className)}
      style={clear ? { padding: clear } : undefined}
      title={title}
    >
      <span
        aria-hidden="true"
        className="block select-none bg-[var(--sw-link)]"
        style={{ width: size, height: size, mask: 'url("/brand/sitewise-mark.png") center / contain no-repeat' }}
      />
    </span>
  );
}

type SitewiseLockupProps = {
  height?: number;
  className?: string;
};

/** Preserve the current lockup silhouette while applying the theme's text colour. */
export function SitewiseLockup({
  height = 32,
  className,
}: SitewiseLockupProps) {
  const width = Math.round(height * LOCKUP_RATIO);

  return (
    <span
      className={cn("relative inline-flex shrink-0 items-center", className)}
      style={{ height, width }}
    >
      <span
        aria-hidden="true"
        className="block size-full select-none bg-[var(--sw-text-primary)]"
        style={{ mask: 'url("/brand/sitewise-lockup-dark.png") center / contain no-repeat' }}
      />
    </span>
  );
}

type SitewiseWordmarkProps = {
  markSize?: number;
  className?: string;
  markClassName?: string;
};

/** Lockup image; `markSize` maps to lockup height for existing callers. */
export function SitewiseWordmark({
  markSize = 40,
  className,
}: SitewiseWordmarkProps) {
  return (
    <SitewiseLockup
      height={Math.max(22, Math.round(markSize * 0.72))}
      className={className}
    />
  );
}
