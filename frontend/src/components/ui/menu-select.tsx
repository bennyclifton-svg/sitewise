import { Check, ChevronDown } from "lucide-react";
import { useId, useMemo } from "react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

export type MenuSelectOption = {
  value: string;
  label: string;
  disabled?: boolean;
};

type MenuSelectProps = {
  id?: string;
  value: string;
  options: ReadonlyArray<MenuSelectOption>;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  contentClassName?: string;
  "aria-label"?: string;
};

export function MenuSelect({
  id,
  value,
  options,
  onChange,
  placeholder = "Select…",
  disabled = false,
  className,
  contentClassName,
  "aria-label": ariaLabel,
}: MenuSelectProps) {
  const generatedId = useId();
  const triggerId = id ?? generatedId;
  const selected = useMemo(
    () => options.find((option) => option.value === value) ?? null,
    [options, value],
  );
  const label = selected?.label ?? placeholder;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild disabled={disabled}>
        <button
          type="button"
          id={triggerId}
          disabled={disabled}
          aria-label={ariaLabel}
          className={cn(
            "flex h-9 w-full items-center justify-between gap-2 rounded-md border border-input bg-background px-3 text-left text-sm outline-none",
            "focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50",
            "disabled:cursor-not-allowed disabled:opacity-50",
            !selected && "text-muted-foreground",
            className,
          )}
        >
          <span className="min-w-0 truncate">{label}</span>
          <ChevronDown className="size-4 shrink-0 text-muted-foreground" aria-hidden />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="start"
        className={cn(
          "max-h-64 w-[var(--radix-dropdown-menu-trigger-width)] overflow-y-auto",
          contentClassName,
        )}
      >
        {options.map((option) => {
          const isSelected = option.value === value;
          return (
            <DropdownMenuItem
              key={option.value || "__empty__"}
              disabled={option.disabled}
              onSelect={() => onChange(option.value)}
              className={cn(isSelected && "bg-muted font-medium")}
            >
              <span className="min-w-0 flex-1 truncate">{option.label}</span>
              {isSelected ? (
                <Check className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />
              ) : (
                <span className="size-3.5 shrink-0" aria-hidden />
              )}
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
