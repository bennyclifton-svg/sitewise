import { useState } from "react";

import { MenuSelect } from "@/components/ui/menu-select";
import { cn } from "@/lib/utils";
import {
  DOCUMENT_CATEGORIES,
  DOCUMENT_CLASSES,
  REVIEW_CONFIDENCE_MIN,
  classificationLabel,
  resolveCategorySlug,
} from "@/lib/classification";

const CANONICAL_CLASSES = new Set<string>(DOCUMENT_CLASSES);

type ClassificationChange = {
  documentClass: string;
  documentSubject: string;
};

type ClassificationChipProps = {
  documentClass: string;
  documentSubject?: string | null;
  category?: string | null;
  confidence?: number | null;
  disabled?: boolean;
  onChange: (next: ClassificationChange) => Promise<void> | void;
};

const CLASS_OPTIONS = DOCUMENT_CLASSES.map((value) => ({
  value,
  label: classificationLabel(value),
}));

const CATEGORY_OPTIONS = DOCUMENT_CATEGORIES.map((value) => ({
  value,
  label: classificationLabel(value),
}));

export function ClassificationChip({
  documentClass,
  documentSubject,
  category,
  confidence,
  disabled = false,
  onChange,
}: ClassificationChipProps) {
  const initialCategory = resolveCategorySlug({
    documentSubject,
    category,
  });
  const [classValue, setClassValue] = useState(documentClass);
  const [categoryValue, setCategoryValue] = useState(initialCategory);

  if (!CANONICAL_CLASSES.has(documentClass)) {
    return (
      <span className="rounded-md border px-2 py-0.5 text-xs text-muted-foreground">
        {documentClass}
      </span>
    );
  }

  async function commit(nextClass: string, nextCategory: string) {
    const previousClass = classValue;
    const previousCategory = categoryValue;
    setClassValue(nextClass);
    setCategoryValue(nextCategory);
    try {
      await onChange({ documentClass: nextClass, documentSubject: nextCategory });
    } catch {
      setClassValue(previousClass);
      setCategoryValue(previousCategory);
    }
  }

  const showLowConfidence =
    typeof confidence === "number" && confidence < REVIEW_CONFIDENCE_MIN;

  return (
    <div
      className="flex flex-wrap items-center gap-1.5"
      onClick={(event) => event.stopPropagation()}
      onKeyDown={(event) => event.stopPropagation()}
    >
      <MenuSelect
        aria-label="Document class"
        value={classValue}
        options={CLASS_OPTIONS}
        disabled={disabled}
        className="h-7 w-auto min-w-[7.5rem] px-2 text-xs"
        onChange={(value) => {
          void commit(value, categoryValue);
        }}
      />
      <MenuSelect
        aria-label="Category"
        value={categoryValue}
        options={CATEGORY_OPTIONS}
        disabled={disabled}
        className="h-7 w-auto min-w-[7.5rem] px-2 text-xs"
        onChange={(value) => {
          void commit(classValue, value);
        }}
      />
      {showLowConfidence ? (
        <span
          className={cn("text-xs font-medium text-[var(--warn-text)]")}
          role="status"
        >
          ⚠ Low confidence
        </span>
      ) : null}
    </div>
  );
}
