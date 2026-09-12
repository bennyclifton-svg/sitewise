import * as React from "react"

import { cn } from "@/lib/utils"

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        "h-11 w-full min-w-0 rounded-[var(--cockpit-control-radius)] border border-input bg-[var(--sw-input-bg)] px-3.5 py-1 text-base text-[var(--sw-input-text)] transition-[color,border-color,box-shadow] outline-none file:inline-flex file:h-7 file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-[var(--sw-input-placeholder)] focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:cursor-not-allowed disabled:border-[var(--sw-action-disabled-border)] disabled:bg-[var(--sw-action-disabled-bg)] disabled:text-[var(--sw-action-disabled-text)] aria-invalid:border-destructive aria-invalid:ring-2 aria-invalid:ring-destructive md:text-base",
        className
      )}
      {...props}
    />
  )
}

export { Input }
