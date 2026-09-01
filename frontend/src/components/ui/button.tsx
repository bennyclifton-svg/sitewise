import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { Slot } from "radix-ui"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "group/button inline-flex shrink-0 items-center justify-center rounded-full border border-transparent bg-clip-padding text-sm font-medium whitespace-nowrap outline-none select-none transition-[color,background-color,border-color,box-shadow] duration-[var(--sw-dur-state)] ease-[var(--sw-ease-state)] focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-2 aria-invalid:ring-destructive/30 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default:
          "bg-[var(--cockpit-action-surface)] text-white hover:bg-[var(--brand-hover)]",
        outline:
          "border-[var(--cockpit-border)] bg-[var(--cockpit-control-surface)] text-foreground hover:border-[var(--cockpit-selected-border)] hover:bg-[var(--cockpit-selected-surface)] aria-expanded:border-[var(--cockpit-selected-border)] aria-expanded:bg-[var(--cockpit-selected-surface)]",
        secondary:
          "border-[var(--cockpit-border)] bg-[var(--cockpit-card-surface)] text-foreground hover:bg-[var(--cockpit-selected-surface)] aria-expanded:bg-[var(--cockpit-selected-surface)]",
        ghost:
          "border-transparent hover:bg-[var(--cockpit-selected-surface)] hover:text-foreground aria-expanded:bg-[var(--cockpit-selected-surface)] aria-expanded:text-foreground",
        destructive:
          "bg-destructive/20 text-destructive hover:bg-destructive/30 focus-visible:border-destructive/40 focus-visible:ring-destructive/40",
        link: "border-transparent text-[var(--sw-beam-hex)] underline-offset-4 hover:text-[var(--brand-hover)] hover:underline",
      },
      size: {
        default:
          "h-11 gap-2 px-5 in-data-[slot=button-group]:rounded-none has-data-[icon=inline-end]:pr-4 has-data-[icon=inline-start]:pl-4",
        xs: "h-6 gap-1 px-2 text-xs in-data-[slot=button-group]:rounded-none has-data-[icon=inline-end]:pr-1.5 has-data-[icon=inline-start]:pl-1.5 [&_svg:not([class*='size-'])]:size-3",
        sm: "h-8 gap-1 px-2.5 in-data-[slot=button-group]:rounded-none has-data-[icon=inline-end]:pr-1.5 has-data-[icon=inline-start]:pl-1.5",
        lg: "h-12 gap-2 px-6 has-data-[icon=inline-end]:pr-5 has-data-[icon=inline-start]:pl-5",
        icon: "size-11",
        "icon-xs":
          "size-6 in-data-[slot=button-group]:rounded-none [&_svg:not([class*='size-'])]:size-3",
        "icon-sm":
          "size-8 in-data-[slot=button-group]:rounded-none",
        "icon-lg": "size-11",
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
