import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { Slot } from "radix-ui"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "group/button inline-flex shrink-0 items-center justify-center rounded-full border border-transparent bg-clip-padding text-sm font-medium whitespace-nowrap outline-none select-none transition-[color,background-color,border-color,box-shadow] duration-[var(--sw-dur-state)] ease-[var(--sw-ease-state)] focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:border-[var(--sw-action-disabled-border)] disabled:bg-[var(--sw-action-disabled-bg)] disabled:text-[var(--sw-action-disabled-text)] aria-invalid:border-destructive aria-invalid:ring-2 aria-invalid:ring-destructive [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default:
          "border-[var(--sw-action-primary-border)] bg-[var(--sw-action-primary)] text-[var(--sw-action-primary-text)] hover:bg-[var(--sw-action-primary-hover)] active:bg-[var(--sw-action-primary-pressed)]",
        outline:
          "border-[var(--sw-border-control)] bg-[var(--sw-input-bg)] text-foreground hover:border-[var(--sw-selection-border)] hover:bg-[var(--sw-selection-bg)] active:bg-[var(--sw-pressed-bg)] aria-expanded:border-[var(--sw-selection-border)] aria-expanded:bg-[var(--sw-selection-bg)]",
        secondary:
          "border-[var(--sw-action-secondary-border)] bg-[var(--sw-action-secondary)] text-[var(--sw-action-secondary-text)] hover:bg-[var(--sw-action-secondary-hover)] active:bg-[var(--sw-action-secondary-pressed)] aria-expanded:bg-[var(--sw-action-secondary-hover)]",
        ghost:
          "border-transparent hover:bg-[var(--cockpit-selected-surface)] hover:text-foreground aria-expanded:bg-[var(--cockpit-selected-surface)] aria-expanded:text-foreground",
        destructive:
          "border-[var(--sw-error-border)] bg-[var(--sw-error-bg)] text-[var(--sw-error-text)] hover:border-[var(--sw-error-icon)] active:border-[var(--sw-error-text)]",
        link: "border-transparent text-[var(--sw-link)] underline underline-offset-4 hover:text-[var(--sw-link-hover)]",
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
