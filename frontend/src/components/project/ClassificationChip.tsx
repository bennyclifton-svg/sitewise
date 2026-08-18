import { useState } from "react";

import { MenuSelect } from "@/components/ui/menu-select";
import { cn } from "@/lib/utils";

const DOCUMENT_CLASSES = [
  "drawing",
  "specification",
  "report",
  "certificate",
  "correspondence",
  "contract",
  "commercial",
  "schedule",
  "statutory_instrument",
  "photo",
  "unknown",
] as const;

const DOCUMENT_SUBJECTS = [
  "planning",
  "heritage",
  "structural",
  "services",
  "hydraulic",
  "fire",
  "geotechnical",
  "survey",
  "cost",
  "programme",
  "contract_admin",
  "defects",
  "sustainability",
  "access",
  "acoustic",
  "none",
] as const;

const LOW_CONFIDENCE = 0.65;
const CANONICAL_CLASSES = new Set<string>(DOCUMENT_CLASSES);

type ClassificationChange = {
  documentClass: string;
  documentSubject: string;
};

type ClassificationChipProps = {
  documentClass: string;
  documentSubject?: string | null;
  confidence?: number | null;
  disabled?: boolean;
  onChange: (next: ClassificationChange) => Promise<void> | void;
};

function labelFor(value: string): string {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

const CLASS_OPTIONS = DOCUMENT_CLASSES.map((value) => ({
  value,
  label: labelFor(value),
}));

const SUBJECT_OPTIONS = DOCUMENT_SUBJECTS.map((value) => ({
  value,
  label: labelFor(value),
}));

export function ClassificationChip({
  documentClass,
  documentSubject,
  confidence,
  disabled = false,
  onChange,
}: ClassificationChipProps) {
  const [classValue, setClassValue] = useState(documentClass);
  const [subjectValue, setSubjectValue] = useState(documentSubject || "none");

  if (!CANONICAL_CLASSES.has(documentClass)) {
    return (
      <span className="rounded-md border px-2 py-0.5 text-xs text-muted-foreground">
        {documentClass}
      </span>
    );
  }

  async function commit(nextClass: string, nextSubject: string) {
    const previousClass = classValue;
    const previousSubject = subjectValue;
    setClassValue(nextClass);
    setSubjectValue(nextSubject);
    try {
      await onChange({ documentClass: nextClass, documentSubject: nextSubject });
    } catch {
      setClassValue(previousClass);
      setSubjectValue(previousSubject);
    }
  }

  const showLowConfidence =
    typeof confidence === "number" && confidence < LOW_CONFIDENCE;

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
          void commit(value, subjectValue);
        }}
      />
      <MenuSelect
        aria-label="Document subject"
        value={subjectValue}
        options={SUBJECT_OPTIONS}
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
