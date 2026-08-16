import { cn } from "@/lib/utils";

type SitewiseMarkProps = {
  /** Rendered mark height in CSS pixels. */
  size?: number;
  /**
   * `auto` uses mark.svg at ≥96px and mark-solid below that.
   * Pass `full` to force mark.svg at any size.
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

/**
 * Flat Sitewise mark. Uses the solid variant below 96px so the open
 * corner does not collapse visually, unless `variant` overrides that.
 */
export function SitewiseMark({
  size = 48,
  variant = "auto",
  padded = true,
  className,
  title = "SiteWise",
}: SitewiseMarkProps) {
  const useFull =
    variant === "full" || (variant === "auto" && size >= 96);
  const src = useFull
    ? "/style-guide/logo/mark.svg"
    : "/style-guide/logo/mark-solid.svg";
  const clear = padded ? size / 3 : 0;

  return (
    <span
      className={cn("inline-flex shrink-0 items-center justify-center", className)}
      style={clear ? { padding: clear } : undefined}
      title={title}
    >
      <img
        src={src}
        alt=""
        width={size}
        height={size}
        draggable={false}
        className="block select-none"
      />
    </span>
  );
}

type SitewiseWordmarkProps = {
  markSize?: number;
  className?: string;
  markClassName?: string;
};

/** Mark + plain-text wordmark until licensed Söhne lockup exists. */
export function SitewiseWordmark({
  markSize = 40,
  className,
  markClassName,
}: SitewiseWordmarkProps) {
  return (
    <span className={cn("inline-flex items-center gap-2", className)}>
      <SitewiseMark size={markSize} className={markClassName} />
      <span className="font-display text-[1.05rem] font-light tracking-[-0.02em] text-[var(--sw-text-primary)]">
        SiteWise
      </span>
    </span>
  );
}
