import type { SVGProps } from "react";

import { cn } from "@/lib/utils";

type IconProps = SVGProps<SVGSVGElement> & {
  className?: string;
};

/**
 * Fluent M365-style Word mark: stacked blue bands + overlapping W tile.
 */
export function WordFileIcon({ className, ...props }: IconProps) {
  return (
    <svg
      viewBox="0 0 32 32"
      role="img"
      aria-hidden
      className={cn("size-5", className)}
      {...props}
    >
      <path
        d="M10 2.5h14c2.2 0 4 1.8 4 4v5.5H10V2.5Z"
        fill="#41A5EE"
      />
      <path d="M10 12h18v8H10V12Z" fill="#2B7CD3" />
      <path
        d="M10 20h18v5.5c0 2.2-1.8 4-4 4H10V20Z"
        fill="#185ABD"
      />
      <rect x="2.5" y="9" width="16.5" height="16.5" rx="3.2" fill="#103F91" />
      <path
        d="M6.2 21.8 8.35 11.2h2.2l1.35 6.55 1.4-6.55h2.2L17.7 21.8h-2.15l-1-5.45-1.2 5.45h-1.85l-1.25-5.5-1 5.5H6.2Z"
        fill="#fff"
      />
    </svg>
  );
}

/**
 * Fluent M365-style Excel mark: stacked green bands + overlapping X tile.
 */
export function ExcelFileIcon({ className, ...props }: IconProps) {
  return (
    <svg
      viewBox="0 0 32 32"
      role="img"
      aria-hidden
      className={cn("size-5", className)}
      {...props}
    >
      <path
        d="M10 2.5h14c2.2 0 4 1.8 4 4v5.5H10V2.5Z"
        fill="#33C481"
      />
      <path d="M10 12h18v8H10V12Z" fill="#21A366" />
      <path
        d="M10 20h18v5.5c0 2.2-1.8 4-4 4H10V20Z"
        fill="#107C41"
      />
      <rect x="2.5" y="9" width="16.5" height="16.5" rx="3.2" fill="#0B5C31" />
      <path
        d="M7.1 12.1h2.45l1.7 2.95 1.7-2.95h2.45l-2.9 4.55 3.05 4.85h-2.5l-1.8-3.15-1.8 3.15H6.9l3.05-4.85-2.85-4.55Z"
        fill="#fff"
      />
    </svg>
  );
}

/**
 * Fluent-style PDF mark matching the Word tile language in Adobe red.
 */
export function PdfFileIcon({ className, ...props }: IconProps) {
  return (
    <svg
      viewBox="0 0 32 32"
      role="img"
      aria-hidden
      className={cn("size-5", className)}
      {...props}
    >
      <path
        d="M10 2.5h14c2.2 0 4 1.8 4 4v5.5H10V2.5Z"
        fill="#FF6B6B"
      />
      <path d="M10 12h18v8H10V12Z" fill="#E5252A" />
      <path
        d="M10 20h18v5.5c0 2.2-1.8 4-4 4H10V20Z"
        fill="#B30B00"
      />
      <rect x="2.5" y="9" width="16.5" height="16.5" rx="3.2" fill="#8A0A00" />
      <text
        x="10.75"
        y="20.1"
        textAnchor="middle"
        fill="#fff"
        fontSize="8"
        fontWeight="700"
        fontFamily="ui-sans-serif, system-ui, sans-serif"
      >
        PDF
      </text>
    </svg>
  );
}
