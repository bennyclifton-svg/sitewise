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
  groups?: ReadonlyArray<SuggestionFieldGroup>;
  /** Small revision (or other) marker shown on matching suggestions. */
  badges?: Readonly<Record<string, string>>;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  "aria-label"?: string;
};

export type SuggestionFieldGroup = {
  id: string;
  label: string;
  suggestions: ReadonlyArray<string>;
  tone?: "brand" | "neutral";
};

export function SuggestionField({
  id,
  value,
  suggestions,
  groups,
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
  const [activeIndex, setActiveIndex] = useState(-1);

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
  const visibleGroups = useMemo(() => {
    if (!groups?.length) return null;
    const visible = new Set(filtered);
    return groups
      .map((group) => ({
        ...group,
        suggestions: group.suggestions.filter((suggestion) =>
          visible.has(suggestion),
        ),
      }))
      .filter((group) => group.suggestions.length > 0);
  }, [filtered, groups]);
  const visibleSuggestions = useMemo(
    () =>
      visibleGroups
        ? visibleGroups.flatMap((group) => group.suggestions)
        : filtered,
    [filtered, visibleGroups],
  );
  const groupOptionOffsets = useMemo(() => {
    return (visibleGroups ?? []).map((_, index) =>
      (visibleGroups ?? [])
        .slice(0, index)
        .reduce((offset, group) => offset + group.suggestions.length, 0),
    );
  }, [visibleGroups]);

  useEffect(() => {
    if (!open) return;

    function handlePointerDown(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false);
        setActiveIndex(-1);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        setActiveIndex(-1);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  useEffect(() => {
    if (
      !open ||
      activeIndex < 0 ||
      activeIndex >= visibleSuggestions.length
    ) {
      return;
    }
    const activeOption = document.getElementById(
      `${listboxId}-option-${activeIndex}`,
    );
    if (typeof activeOption?.scrollIntoView === "function") {
      activeOption.scrollIntoView({ block: "nearest" });
    }
  }, [activeIndex, listboxId, open, visibleSuggestions.length]);

  function selectSuggestion(suggestion: string) {
    onChange(suggestion);
    setOpen(false);
    setActiveIndex(-1);
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
          aria-activedescendant={
            open &&
            activeIndex >= 0 &&
            activeIndex < visibleSuggestions.length
              ? `${listboxId}-option-${activeIndex}`
              : undefined
          }
          role="combobox"
          className={cn(
            "h-9 w-full rounded-md border border-input bg-background py-0 pr-9 pl-3 text-sm outline-none",
            "focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50",
            "disabled:cursor-not-allowed disabled:opacity-50",
          )}
          onChange={(event) => {
            onChange(event.target.value);
            setActiveIndex(-1);
            if (suggestions.length) setOpen(true);
          }}
          onFocus={() => {
            if (suggestions.length) setOpen(true);
          }}
          onKeyDown={(event) => {
            if (event.key === "ArrowDown" && visibleSuggestions.length) {
              event.preventDefault();
              setOpen(true);
              setActiveIndex((current) =>
                current < visibleSuggestions.length - 1 ? current + 1 : 0,
              );
            } else if (event.key === "ArrowUp" && visibleSuggestions.length) {
              event.preventDefault();
              setOpen(true);
              setActiveIndex((current) =>
                current > 0 ? current - 1 : visibleSuggestions.length - 1,
              );
            } else if (event.key === "Home" && open && visibleSuggestions.length) {
              event.preventDefault();
              setActiveIndex(0);
            } else if (event.key === "End" && open && visibleSuggestions.length) {
              event.preventDefault();
              setActiveIndex(visibleSuggestions.length - 1);
            } else if (
              event.key === "Enter" &&
              open &&
              activeIndex >= 0 &&
              activeIndex < visibleSuggestions.length
            ) {
              event.preventDefault();
              selectSuggestion(visibleSuggestions[activeIndex]);
            } else if (event.key === "Escape" && open) {
              event.preventDefault();
              setOpen(false);
              setActiveIndex(-1);
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
            setOpen(!open);
            if (open) setActiveIndex(-1);
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
            "absolute top-full left-0 z-50 mt-1 max-h-[min(28rem,60vh)] w-[min(24rem,calc(100vw-2rem))] max-w-[calc(100vw-2rem)] overflow-y-auto",
          )}
        >
          {visibleGroups
            ? visibleGroups.map((group, groupIndex) => (
                <li
                  key={group.id}
                  role="group"
                  aria-labelledby={`${listboxId}-${group.id}-label`}
                >
                  <div
                    id={`${listboxId}-${group.id}-label`}
                    className={cn(
                      "sticky top-0 z-10 flex items-center gap-2 border-y border-border px-2.5 py-2 font-mono text-[0.6875rem] font-medium tracking-[0.12em] uppercase",
                      group.tone === "brand"
                        ? "bg-accent text-accent-foreground"
                        : "bg-muted text-foreground",
                    )}
                  >
                    <span
                      className={cn(
                        "h-px w-3 shrink-0",
                        group.tone === "brand"
                          ? "bg-primary"
                          : "bg-muted-foreground/60",
                      )}
                      aria-hidden
                    />
                    {group.label}
                  </div>
                  <ul role="presentation" className="py-1">
                    {group.suggestions.map((suggestion, index) => {
                      const optionIndex = groupOptionOffsets[groupIndex] + index;
                      return renderSuggestion({
                        suggestion,
                        optionIndex,
                        activeIndex,
                        listboxId,
                        value,
                        badge: badges?.[suggestion],
                        onActivate: setActiveIndex,
                        onSelect: selectSuggestion,
                      });
                    })}
                  </ul>
                </li>
              ))
            : filtered.map((suggestion, optionIndex) =>
                renderSuggestion({
                  suggestion,
                  optionIndex,
                  activeIndex,
                  listboxId,
                  value,
                  badge: badges?.[suggestion],
                  onActivate: setActiveIndex,
                  onSelect: selectSuggestion,
                }),
              )}
        </ul>
      ) : null}
    </div>
  );
}

function renderSuggestion({
  suggestion,
  optionIndex,
  activeIndex,
  listboxId,
  value,
  badge,
  onActivate,
  onSelect,
}: {
  suggestion: string;
  optionIndex: number;
  activeIndex: number;
  listboxId: string;
  value: string;
  badge?: string;
  onActivate: (index: number) => void;
  onSelect: (suggestion: string) => void;
}) {
  const isSelected = suggestion === value;
  return (
    <li
      key={`${optionIndex}-${suggestion}`}
      id={`${listboxId}-option-${optionIndex}`}
      role="option"
      aria-selected={isSelected}
      aria-label={badge ? `${suggestion} ${badge}` : suggestion}
      className={cn(
        dropdownMenuItemClassName,
        "items-start py-2",
        (isSelected || activeIndex === optionIndex) && "bg-muted",
        isSelected && "font-medium",
      )}
      onMouseDown={(event) => {
        // Keep input focus; avoid blur-before-click races.
        event.preventDefault();
      }}
      onMouseMove={() => onActivate(optionIndex)}
      onClick={() => onSelect(suggestion)}
    >
      <span className="min-w-0 flex-1 whitespace-normal break-words leading-5">
        {suggestion}
      </span>
      {badge ? (
        <span className="mt-0.5 shrink-0 text-[0.6875rem] tabular-nums text-muted-foreground">
          {badge}
        </span>
      ) : null}
      {isSelected ? (
        <Check
          className="mt-0.5 size-3.5 shrink-0 text-muted-foreground"
          aria-hidden
        />
      ) : (
        <span className="mt-0.5 size-3.5 shrink-0" aria-hidden />
      )}
    </li>
  );
}
