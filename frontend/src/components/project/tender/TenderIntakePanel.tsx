import { FilePlus2, LoaderCircle, Plus, Trash2 } from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import type { EvidencePreview } from "@/lib/types/project";
import type { TenderProjectContext, TenderQuoteCreate } from "@/lib/types/tender";
import { cn } from "@/lib/utils";

type QuoteDraft = {
  id: string;
  builderName: string;
  builderAbn: string;
  quoteRef: string;
  quoteDate: string;
  statedTotal: string;
  gstTreatment: NonNullable<TenderQuoteCreate["gst_treatment"]>;
  contractType: NonNullable<TenderQuoteCreate["contract_type"]>;
  validityDays: string;
  projectDocumentPaths: string[];
  files: File[];
};

type BoolSelect = "unknown" | "yes" | "no";

let quoteDraftId = 0;

const fieldClass =
  "h-9 w-full rounded-md border border-input bg-background px-2.5 py-1 text-sm shadow-xs outline-none transition-[color,box-shadow] focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";
const multiSelectClass =
  "min-h-24 w-full rounded-md border border-input bg-background px-2.5 py-2 text-sm shadow-xs outline-none transition-[color,box-shadow] focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";

const states: NonNullable<TenderProjectContext["state"]>[] = ["NSW", "VIC", "QLD"];
const regions: NonNullable<TenderProjectContext["region"]>[] = ["metro", "regional"];
const buildTypes: NonNullable<TenderProjectContext["build_type"]>[] = [
  "new_build",
  "renovation",
  "addition",
];
const soilClasses: NonNullable<TenderProjectContext["soil_class"]>[] = [
  "unknown",
  "A",
  "S",
  "M",
  "H1",
  "H2",
  "E",
  "P",
];
const slopeClasses: NonNullable<TenderProjectContext["slope_class"]>[] = [
  "unknown",
  "flat",
  "moderate",
  "steep",
];
const balRatings: NonNullable<TenderProjectContext["bal_rating"]>[] = [
  "unknown",
  "none",
  "12.5",
  "19",
  "29",
  "40",
  "FZ",
];
const specLevels: NonNullable<TenderProjectContext["spec_level"]>[] = [
  "builder_base",
  "mid",
  "high",
  "architectural",
];
const gstTreatments: NonNullable<TenderQuoteCreate["gst_treatment"]>[] = [
  "unclear",
  "inclusive",
  "exclusive",
];
const contractTypes: NonNullable<TenderQuoteCreate["contract_type"]>[] = [
  "unknown",
  "hia",
  "mba",
  "custom",
  "cost_plus",
];

export function TenderIntakePanel({
  projectId,
  onCancel,
}: {
  projectId: string;
  onCancel?: () => void;
}) {
  const navigate = useNavigate();
  const [state, setState] = useState<NonNullable<TenderProjectContext["state"]>>("NSW");
  const [region, setRegion] =
    useState<NonNullable<TenderProjectContext["region"]>>("metro");
  const [buildType, setBuildType] =
    useState<NonNullable<TenderProjectContext["build_type"]>>("new_build");
  const [storeys, setStoreys] = useState("1");
  const [floorArea, setFloorArea] = useState("");
  const [siteArea, setSiteArea] = useState("");
  const [soilClass, setSoilClass] =
    useState<NonNullable<TenderProjectContext["soil_class"]>>("unknown");
  const [slopeClass, setSlopeClass] =
    useState<NonNullable<TenderProjectContext["slope_class"]>>("unknown");
  const [balRating, setBalRating] =
    useState<NonNullable<TenderProjectContext["bal_rating"]>>("unknown");
  const [windRating, setWindRating] = useState("");
  const [floodOverlay, setFloodOverlay] = useState<BoolSelect>("unknown");
  const [heritageOverlay, setHeritageOverlay] = useState<BoolSelect>("unknown");
  const [existingDwellingEra, setExistingDwellingEra] = useState("");
  const [demolitionRequired, setDemolitionRequired] =
    useState<BoolSelect>("unknown");
  const [specLevel, setSpecLevel] =
    useState<NonNullable<TenderProjectContext["spec_level"]>>("mid");
  const [targetBudget, setTargetBudget] = useState("");
  const [notes, setNotes] = useState("");
  const [quotes, setQuotes] = useState<QuoteDraft[]>(() => [
    newQuoteDraft(),
    newQuoteDraft(),
    newQuoteDraft(),
  ]);
  const [projectDocuments, setProjectDocuments] = useState<EvidencePreview[]>([]);
  const [documentsError, setDocumentsError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadDocuments() {
      setDocumentsError(null);
      try {
        const evidence = await api.getProjectEvidence(projectId);
        if (!cancelled) {
          setProjectDocuments(evidence.filter(isTenderDocumentCandidate));
        }
      } catch (error) {
        if (!cancelled) {
          setDocumentsError(
            error instanceof ApiError
              ? error.message
              : "Could not load project documents.",
          );
        }
      }
    }

    void loadDocuments();
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitError(null);

    const activeQuotes = quotes.filter((quote) => quote.builderName.trim());
    if (activeQuotes.length < 2) {
      setSubmitError("Add at least two builders.");
      return;
    }

    const quoteWithoutDocument = activeQuotes.find(
      (quote) => quote.projectDocumentPaths.length === 0 && quote.files.length === 0,
    );
    if (quoteWithoutDocument) {
      setSubmitError(`Attach at least one document for ${quoteWithoutDocument.builderName}.`);
      return;
    }

    setIsSubmitting(true);
    try {
      const comparison = await api.createTenderComparison({
        project_id: projectId,
        context: buildContext(),
      });

      for (const quoteDraft of activeQuotes) {
        const quote = await api.createTenderQuote(comparison.id, buildQuote(quoteDraft));
        for (const workspacePath of quoteDraft.projectDocumentPaths) {
          await api.attachTenderProjectDocument(quote.id, workspacePath);
        }
        for (const file of quoteDraft.files) {
          await api.uploadTenderQuoteDocument(quote.id, file);
        }
      }

      navigate(`/projects/${projectId}/tender/${comparison.id}`);
    } catch (error) {
      setSubmitError(
        error instanceof ApiError
          ? error.message
          : "Could not create the tender comparison.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  function buildContext(): TenderProjectContext {
    return {
      context_version: 1,
      context_source: "manual",
      state,
      region,
      build_type: buildType,
      dwelling_class: "class_1a",
      storeys: integerOrFallback(storeys, 1),
      floor_area_m2: numberOrNull(floorArea),
      site_area_m2: numberOrNull(siteArea),
      soil_class: soilClass,
      slope_class: slopeClass,
      bal_rating: balRating,
      wind_rating: textOrNull(windRating),
      flood_overlay: boolOrNull(floodOverlay),
      heritage_overlay: boolOrNull(heritageOverlay),
      existing_dwelling_era: textOrNull(existingDwellingEra),
      demolition_required: boolOrNull(demolitionRequired),
      spec_level: specLevel,
      target_budget_cents: moneyToCents(targetBudget),
      notes: textOrNull(notes),
    };
  }

  function updateQuote(id: string, patch: Partial<QuoteDraft>) {
    setQuotes((current) =>
      current.map((quote) => (quote.id === id ? { ...quote, ...patch } : quote)),
    );
  }

  function addQuote() {
    setQuotes((current) => (current.length >= 5 ? current : [...current, newQuoteDraft()]));
  }

  function removeQuote(id: string) {
    setQuotes((current) =>
      current.length <= 2 ? current : current.filter((quote) => quote.id !== id),
    );
  }

  return (
    <section className="rounded-md border bg-card shadow-sm">
      <form onSubmit={(event) => void handleSubmit(event)}>
        <header className="flex flex-wrap items-start justify-between gap-3 border-b px-4 py-3">
          <div className="min-w-0">
            <p className="cockpit-zone-title">Tender intake</p>
            <h2 className="mt-1 text-lg font-semibold tracking-tight">
              New tender comparison
            </h2>
          </div>
          <div className="flex gap-2">
            {onCancel ? (
              <Button type="button" variant="outline" onClick={onCancel}>
                Cancel
              </Button>
            ) : null}
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? (
                <LoaderCircle className="size-4 animate-spin" aria-hidden />
              ) : (
                <FilePlus2 className="size-4" aria-hidden />
              )}
              {isSubmitting ? "Creating" : "Create comparison"}
            </Button>
          </div>
        </header>

        {submitError ? (
          <p className="mx-4 mt-4 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
            {submitError}
          </p>
        ) : null}

        <div className="grid gap-5 p-4 xl:grid-cols-[minmax(0,22rem)_minmax(0,1fr)]">
          <section className="space-y-4">
            <div>
              <p className="text-sm font-medium">Project context</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Class 1 residential comparison settings.
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <SelectField
                id="tender-state"
                label="State"
                value={state}
                options={states}
                onChange={setState}
              />
              <SelectField
                id="tender-region"
                label="Region"
                value={region}
                options={regions}
                onChange={setRegion}
              />
              <SelectField
                id="tender-build-type"
                label="Build"
                value={buildType}
                options={buildTypes}
                onChange={setBuildType}
              />
              <SelectField
                id="tender-spec"
                label="Spec"
                value={specLevel}
                options={specLevels}
                onChange={setSpecLevel}
              />
              <InputField
                id="tender-storeys"
                label="Storeys"
                type="number"
                min="1"
                value={storeys}
                onChange={setStoreys}
              />
              <InputField
                id="tender-floor-area"
                label="Floor area m2"
                type="number"
                min="0"
                value={floorArea}
                onChange={setFloorArea}
              />
              <InputField
                id="tender-site-area"
                label="Site area m2"
                type="number"
                min="0"
                value={siteArea}
                onChange={setSiteArea}
              />
              <InputField
                id="tender-budget"
                label="Target budget"
                inputMode="decimal"
                value={targetBudget}
                onChange={setTargetBudget}
              />
              <SelectField
                id="tender-soil"
                label="Soil"
                value={soilClass}
                options={soilClasses}
                onChange={setSoilClass}
              />
              <SelectField
                id="tender-slope"
                label="Slope"
                value={slopeClass}
                options={slopeClasses}
                onChange={setSlopeClass}
              />
              <SelectField
                id="tender-bal"
                label="BAL"
                value={balRating}
                options={balRatings}
                onChange={setBalRating}
              />
              <InputField
                id="tender-wind"
                label="Wind"
                value={windRating}
                onChange={setWindRating}
              />
              <BoolField
                id="tender-flood"
                label="Flood"
                value={floodOverlay}
                onChange={setFloodOverlay}
              />
              <BoolField
                id="tender-heritage"
                label="Heritage"
                value={heritageOverlay}
                onChange={setHeritageOverlay}
              />
              <BoolField
                id="tender-demolition"
                label="Demolition"
                value={demolitionRequired}
                onChange={setDemolitionRequired}
              />
              <InputField
                id="tender-era"
                label="Existing era"
                value={existingDwellingEra}
                onChange={setExistingDwellingEra}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="tender-notes">Notes</Label>
              <textarea
                id="tender-notes"
                className={cn(fieldClass, "min-h-20 resize-y py-2")}
                value={notes}
                onChange={(event) => setNotes(event.currentTarget.value)}
              />
            </div>
          </section>

          <section className="space-y-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-sm font-medium">Builder quotes</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Attach sorted project documents or upload quote files.
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={addQuote}
                disabled={quotes.length >= 5}
              >
                <Plus className="size-4" aria-hidden />
                Add builder
              </Button>
            </div>

            {documentsError ? (
              <p className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
                {documentsError}
              </p>
            ) : null}

            <div className="space-y-3">
              {quotes.map((quote, index) => (
                <QuoteDraftPanel
                  key={quote.id}
                  index={index}
                  quote={quote}
                  projectDocuments={projectDocuments}
                  canRemove={quotes.length > 2}
                  onChange={(patch) => updateQuote(quote.id, patch)}
                  onRemove={() => removeQuote(quote.id)}
                />
              ))}
            </div>
          </section>
        </div>
      </form>
    </section>
  );
}

function QuoteDraftPanel({
  index,
  quote,
  projectDocuments,
  canRemove,
  onChange,
  onRemove,
}: {
  index: number;
  quote: QuoteDraft;
  projectDocuments: EvidencePreview[];
  canRemove: boolean;
  onChange: (patch: Partial<QuoteDraft>) => void;
  onRemove: () => void;
}) {
  const documentSelectId = `${quote.id}-project-documents`;

  return (
    <section className="rounded-md border bg-background p-3">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-medium">Builder {index + 1}</p>
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          onClick={onRemove}
          disabled={!canRemove}
          title="Remove builder"
        >
          <Trash2 className="size-4" aria-hidden />
        </Button>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <InputField
          id={`${quote.id}-builder`}
          label="Builder"
          value={quote.builderName}
          onChange={(builderName) => onChange({ builderName })}
        />
        <InputField
          id={`${quote.id}-abn`}
          label="ABN"
          value={quote.builderAbn}
          onChange={(builderAbn) => onChange({ builderAbn })}
        />
        <InputField
          id={`${quote.id}-ref`}
          label="Quote ref"
          value={quote.quoteRef}
          onChange={(quoteRef) => onChange({ quoteRef })}
        />
        <InputField
          id={`${quote.id}-date`}
          label="Quote date"
          type="date"
          value={quote.quoteDate}
          onChange={(quoteDate) => onChange({ quoteDate })}
        />
        <InputField
          id={`${quote.id}-total`}
          label="Stated total"
          inputMode="decimal"
          value={quote.statedTotal}
          onChange={(statedTotal) => onChange({ statedTotal })}
        />
        <InputField
          id={`${quote.id}-validity`}
          label="Validity days"
          type="number"
          min="0"
          value={quote.validityDays}
          onChange={(validityDays) => onChange({ validityDays })}
        />
        <SelectField
          id={`${quote.id}-gst`}
          label="GST"
          value={quote.gstTreatment}
          options={gstTreatments}
          onChange={(gstTreatment) => onChange({ gstTreatment })}
        />
        <SelectField
          id={`${quote.id}-contract`}
          label="Contract"
          value={quote.contractType}
          options={contractTypes}
          onChange={(contractType) => onChange({ contractType })}
        />
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor={documentSelectId}>Project documents</Label>
          <select
            id={documentSelectId}
            multiple
            className={multiSelectClass}
            value={quote.projectDocumentPaths}
            onChange={(event) =>
              onChange({
                projectDocumentPaths: Array.from(
                  event.currentTarget.selectedOptions,
                ).map((option) => option.value),
              })
            }
          >
            {projectDocuments.map((document) => (
              <option key={document.relative_path} value={document.relative_path}>
                {document.filename}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor={`${quote.id}-files`}>Upload files</Label>
          <Input
            id={`${quote.id}-files`}
            type="file"
            multiple
            accept=".pdf,.doc,.docx,.xls,.xlsx,application/pdf"
            onChange={(event) =>
              onChange({ files: Array.from(event.currentTarget.files ?? []) })
            }
          />
          <p className="min-h-4 text-xs text-muted-foreground">
            {quote.files.length
              ? `${quote.files.length} selected`
              : projectDocuments.length
                ? ""
                : "No project documents found"}
          </p>
        </div>
      </div>
    </section>
  );
}

function InputField({
  id,
  label,
  value,
  onChange,
  type = "text",
  min,
  inputMode,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  min?: string;
  inputMode?: "decimal" | "numeric";
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        type={type}
        min={min}
        inputMode={inputMode}
        value={value}
        onChange={(event) => onChange(event.currentTarget.value)}
      />
    </div>
  );
}

function SelectField<T extends string>({
  id,
  label,
  value,
  options,
  onChange,
}: {
  id: string;
  label: string;
  value: T;
  options: readonly T[];
  onChange: (value: T) => void;
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <select
        id={id}
        className={fieldClass}
        value={value}
        onChange={(event) => onChange(event.currentTarget.value as T)}
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {formatOption(option)}
          </option>
        ))}
      </select>
    </div>
  );
}

function BoolField({
  id,
  label,
  value,
  onChange,
}: {
  id: string;
  label: string;
  value: BoolSelect;
  onChange: (value: BoolSelect) => void;
}) {
  return (
    <SelectField
      id={id}
      label={label}
      value={value}
      options={["unknown", "yes", "no"] as const}
      onChange={onChange}
    />
  );
}

function newQuoteDraft(): QuoteDraft {
  quoteDraftId += 1;
  return {
    id: `quote-draft-${quoteDraftId}`,
    builderName: "",
    builderAbn: "",
    quoteRef: "",
    quoteDate: "",
    statedTotal: "",
    gstTreatment: "unclear",
    contractType: "unknown",
    validityDays: "",
    projectDocumentPaths: [],
    files: [],
  };
}

function buildQuote(quote: QuoteDraft): TenderQuoteCreate {
  return {
    builder_name: quote.builderName.trim(),
    builder_abn: textOrNull(quote.builderAbn),
    quote_ref: textOrNull(quote.quoteRef),
    quote_date: textOrNull(quote.quoteDate),
    stated_total_cents: moneyToCents(quote.statedTotal),
    gst_treatment: quote.gstTreatment,
    contract_type: quote.contractType,
    validity_days: integerOrNull(quote.validityDays),
  };
}

function isTenderDocumentCandidate(document: EvidencePreview): boolean {
  const name = `${document.filename} ${document.relative_path}`.toLowerCase();
  return [".pdf", ".doc", ".docx", ".xls", ".xlsx"].some((extension) =>
    name.includes(extension),
  );
}

function textOrNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function numberOrNull(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

function integerOrNull(value: string): number | null {
  const parsed = numberOrNull(value);
  return parsed === null ? null : Math.trunc(parsed);
}

function integerOrFallback(value: string, fallback: number): number {
  return integerOrNull(value) ?? fallback;
}

function moneyToCents(value: string): number | null {
  const trimmed = value.replaceAll("$", "").replaceAll(",", "").trim();
  if (!trimmed) return null;
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? Math.round(parsed * 100) : null;
}

function boolOrNull(value: BoolSelect): boolean | null {
  if (value === "yes") return true;
  if (value === "no") return false;
  return null;
}

function formatOption(value: string): string {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
