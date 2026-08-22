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

const OPTION_LABEL_COLLATOR = new Intl.Collator("en-AU", {
  numeric: true,
  sensitivity: "base",
});

function classificationOptions(values: ReadonlyArray<string>) {
  return values
    .map((value) => ({
      value,
      label: classificationLabel(value),
    }))
    .sort((left, right) => OPTION_LABEL_COLLATOR.compare(left.label, right.label));
}

const CLASS_OPTIONS = classificationOptions(DOCUMENT_CLASSES);
const CATEGORY_OPTIONS = classificationOptions(DOCUMENT_CATEGORIES);

const CLASSIFICATION_SELECT_CLASS_NAME =
  "h-7 w-[11.5rem] max-w-full px-2 text-xs";

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
        className={CLASSIFICATION_SELECT_CLASS_NAME}
        onChange={(value) => {
          void commit(value, categoryValue);
        }}
      />
      <MenuSelect
        aria-label="Category"
        value={categoryValue}
        options={CATEGORY_OPTIONS}
        disabled={disabled}
        className={CLASSIFICATION_SELECT_CLASS_NAME}
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
