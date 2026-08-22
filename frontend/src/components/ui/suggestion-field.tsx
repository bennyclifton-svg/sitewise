import { Check, ChevronDown } from "lucide-react";
import { useEffect, useId, useMemo, useRef, useState } from "react";

import {
  dropdownMenuContentClassName,
  dropdownMenuItemClassName,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

type SuggestionFieldProps = {
  id?: string;
  value: string;
  suggestions: ReadonlyArray<string>;
  /** Small revision (or other) marker shown on matching suggestions. */
  badges?: Readonly<Record<string, string>>;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  "aria-label"?: string;
};

export function SuggestionField({
  id,
  value,
  suggestions,
  badges,
  onChange,
  placeholder,
  disabled = false,
  className,
  "aria-label": ariaLabel,
}: SuggestionFieldProps) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const listboxId = `${inputId}-suggestions`;
  const containerRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);

  const filtered = useMemo(() => {
    const query = value.trim().toLowerCase();
    if (!query) return [...suggestions];
    const exactMatch = suggestions.some(
      (suggestion) => suggestion.toLowerCase() === query,
    );
    if (exactMatch) return [...suggestions];
    const matched = suggestions.filter((suggestion) =>
      suggestion.toLowerCase().includes(query),
    );
    return matched.length ? matched : [...suggestions];
  }, [suggestions, value]);

  useEffect(() => {
    if (!open) return;

    function handlePointerDown(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  function selectSuggestion(suggestion: string) {
    onChange(suggestion);
    setOpen(false);
  }

  return (
    <div ref={containerRef} className={cn("relative min-w-0", className)}>
      <div className="relative flex">
        <input
          id={inputId}
          type="text"
          value={value}
          disabled={disabled}
          placeholder={placeholder}
          aria-label={ariaLabel}
          aria-autocomplete="list"
          aria-expanded={open}
          aria-controls={listboxId}
          role="combobox"
          className={cn(
            "h-9 w-full rounded-md border border-input bg-background py-0 pr-9 pl-3 text-sm outline-none",
            "focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50",
            "disabled:cursor-not-allowed disabled:opacity-50",
          )}
          onChange={(event) => {
            onChange(event.target.value);
            if (suggestions.length) setOpen(true);
          }}
          onFocus={() => {
            if (suggestions.length) setOpen(true);
          }}
          onKeyDown={(event) => {
            if (event.key === "ArrowDown" && suggestions.length) {
              event.preventDefault();
              setOpen(true);
            }
          }}
        />
        <button
          type="button"
          tabIndex={-1}
          disabled={disabled || suggestions.length === 0}
          aria-label={ariaLabel ? `${ariaLabel} suggestions` : "Suggestions"}
          aria-expanded={open}
          className={cn(
            "absolute inset-y-0 right-0 flex w-9 items-center justify-center text-muted-foreground outline-none",
            "hover:text-foreground disabled:pointer-events-none disabled:opacity-50",
          )}
          onClick={() => {
            if (!suggestions.length) return;
            setOpen((current) => !current);
          }}
        >
          <ChevronDown
            className={cn("size-4 transition-transform", open && "rotate-180")}
            aria-hidden
          />
        </button>
      </div>

      {open && filtered.length > 0 ? (
        <ul
          id={listboxId}
          role="listbox"
          aria-label={ariaLabel ? `${ariaLabel} suggestions` : "Suggestions"}
          className={cn(
            dropdownMenuContentClassName,
            "absolute top-full right-0 left-0 z-50 mt-1 max-h-64 overflow-y-auto",
          )}
        >
          {filtered.map((suggestion) => {
            const isSelected = suggestion === value;
            const badge = badges?.[suggestion];
            return (
              <li
                key={suggestion}
                role="option"
                aria-selected={isSelected}
                aria-label={badge ? `${suggestion} ${badge}` : suggestion}
                onMouseDown={(event) => {
                  event.preventDefault();
                }}
                onClick={() => selectSuggestion(suggestion)}
              >
                <button
                  type="button"
                  aria-label={badge ? `${suggestion} ${badge}` : suggestion}
                  className={cn(
                    dropdownMenuItemClassName,
                    isSelected && "bg-muted font-medium",
                  )}
                  onMouseDown={(event) => {
                    // Keep input focus; avoid blur-before-click races.
                    event.preventDefault();
                  }}
                  onClick={() => selectSuggestion(suggestion)}
                >
                  <span className="min-w-0 flex-1 truncate">{suggestion}</span>
                  {badge ? (
                    <span className="shrink-0 text-[0.6875rem] tabular-nums text-muted-foreground">
                      {badge}
                    </span>
                  ) : null}
                  {isSelected ? (
                    <Check className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />
                  ) : (
                    <span className="size-3.5 shrink-0" aria-hidden />
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}
