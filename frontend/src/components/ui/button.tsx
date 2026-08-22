import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { Slot } from "radix-ui"

import { cn } from "@/lib/utils"

/**
 * Hover states match the Sitewise design guide elements:
 * - Primary: #2F72C4 → #4A87D2, slight lift, blue glow intensifies
 * - Secondary (outline): bone on dark edge → beam border + text
 * - Link: beam → lighter beam
 */
const buttonVariants = cva(
  "group/button inline-flex shrink-0 items-center justify-center rounded-none border border-transparent bg-clip-padding text-sm font-medium whitespace-nowrap outline-none select-none transition-[color,background-color,border-color,box-shadow,transform] duration-[var(--sw-dur-state)] ease-[var(--sw-ease-state)] focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 active:not-aria-[haspopup]:translate-y-px disabled:pointer-events-none disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default:
          "border-t-[rgba(255,255,255,0.3)] bg-[var(--sw-facet-blue-hex)] text-white shadow-[0_12px_40px_-10px_rgba(47,114,196,0.42)] hover:-translate-y-0.5 hover:bg-[#4A87D2] hover:shadow-[0_16px_48px_-8px_rgba(74,135,210,0.62)]",
        outline:
          "border-[var(--sw-edge-side)] border-t-[var(--sw-edge-lit)] border-b-[var(--sw-edge-shade)] bg-[var(--sw-void-hex)] text-[var(--sw-text-primary)] hover:border-[var(--sw-beam-hex)] hover:bg-[color-mix(in_oklch,var(--sw-panel)_88%,white)] hover:text-[var(--sw-beam-hex)] aria-expanded:border-[var(--sw-beam-hex)] aria-expanded:text-[var(--sw-beam-hex)]",
        secondary:
          "border-[var(--sw-edge-side)] border-t-[var(--sw-edge-lit)] border-b-[var(--sw-edge-shade)] bg-[var(--sw-void-hex)] text-[var(--sw-text-primary)] hover:border-[var(--sw-beam-hex)] hover:bg-[color-mix(in_oklch,var(--sw-panel)_88%,white)] hover:text-[var(--sw-beam-hex)] aria-expanded:border-[var(--sw-beam-hex)] aria-expanded:text-[var(--sw-beam-hex)]",
        ghost:
          "border-transparent hover:bg-muted hover:text-foreground aria-expanded:bg-muted aria-expanded:text-foreground",
        destructive:
          "bg-destructive/20 text-destructive hover:bg-destructive/30 focus-visible:border-destructive/40 focus-visible:ring-destructive/40",
        link: "border-transparent text-[var(--sw-beam-hex)] underline-offset-4 hover:text-[var(--brand-hover)] hover:underline",
      },
      size: {
        default:
          "h-9 gap-1.5 px-2.5 in-data-[slot=button-group]:rounded-none has-data-[icon=inline-end]:pr-2 has-data-[icon=inline-start]:pl-2",
        xs: "h-6 gap-1 rounded-none px-2 text-xs in-data-[slot=button-group]:rounded-none has-data-[icon=inline-end]:pr-1.5 has-data-[icon=inline-start]:pl-1.5 [&_svg:not([class*='size-'])]:size-3",
        sm: "h-8 gap-1 rounded-none px-2.5 in-data-[slot=button-group]:rounded-none has-data-[icon=inline-end]:pr-1.5 has-data-[icon=inline-start]:pl-1.5",
        lg: "h-10 gap-1.5 px-2.5 has-data-[icon=inline-end]:pr-2 has-data-[icon=inline-start]:pl-2",
        icon: "size-9",
        "icon-xs":
          "size-6 rounded-none in-data-[slot=button-group]:rounded-none [&_svg:not([class*='size-'])]:size-3",
        "icon-sm":
          "size-8 rounded-none in-data-[slot=button-group]:rounded-none",
        "icon-lg": "size-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot.Root : "button"

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
