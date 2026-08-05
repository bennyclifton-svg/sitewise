import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Check, Loader2, Table2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import type {
  WorkbookCellStyle,
  InvoiceLedger,
  InvoiceLedgerRow,
  WorkbookPreview,
  WorkbookSheetPreview,
} from "@/lib/types/project";
import { cn } from "@/lib/utils";

export function WorkbookGrid({
  projectId,
  workbookPath,
}: {
  projectId: string;
  workbookPath: string;
}) {
  const [preview, setPreview] = useState<WorkbookPreview | null>(null);
  const [ledger, setLedger] = useState<InvoiceLedger | null>(null);
  const [activeSheet, setActiveSheet] = useState<string | null>(null);
  const [workbookOverride, setWorkbookOverride] = useState<{
    projectId: string;
    path: string;
  } | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSavingInvoice, setIsSavingInvoice] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [invoiceError, setInvoiceError] = useState<string | null>(null);
  const [invoiceSaveMessage, setInvoiceSaveMessage] = useState<string | null>(null);

  const activeWorkbookPath = latestWorkbookPath(
    workbookPath,
    workbookOverride?.projectId === projectId ? workbookOverride.path : null,
  );

  useEffect(() => {
    let cancelled = false;

    async function loadWorkbookPreview() {
      setIsLoading(true);
      setError(null);
      try {
        const data = await api.getWorkbookPreview(projectId, activeWorkbookPath);
        if (cancelled) return;
        setPreview(data);
        setActiveSheet((current) =>
          current && data.sheets.some((sheet) => sheet.name === current)
            ? current
            : data.sheets[0]?.name ?? null,
        );
      } catch (loadError) {
        if (!cancelled) {
          setError(
            loadError instanceof ApiError
              ? loadError.message
              : "Could not load workbook preview.",
          );
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void loadWorkbookPreview();
    return () => {
      cancelled = true;
    };
  }, [activeWorkbookPath, projectId]);

  useEffect(() => {
    let cancelled = false;

    async function loadInvoiceLedger() {
      try {
        const data = await api.getInvoiceLedger(projectId);
        if (!cancelled) {
          setLedger(data);
          setInvoiceError(null);
        }
      } catch (loadError) {
        if (!cancelled) {
          setInvoiceError(
            loadError instanceof ApiError
              ? loadError.message
              : "Invoice controls could not be loaded. The workbook remains read-only.",
          );
        }
      }
    }

    void loadInvoiceLedger();
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  async function applyInvoiceEdit(
    request: () => Promise<InvoiceLedger>,
    previousLedger: InvoiceLedger,
  ) {
    if (isSavingInvoice) return;
    setIsSavingInvoice(true);
    setInvoiceError(null);
    setInvoiceSaveMessage(null);
    try {
      const updated = await request();
      setLedger(updated);
      setWorkbookOverride({ projectId, path: updated.workbook_path });
      setInvoiceSaveMessage(`Saved as Cost Plan v${updated.cost_plan_version}.`);
    } catch (saveError) {
      if (saveError instanceof ApiError && saveError.status === 409) {
        try {
          const latest = await api.getInvoiceLedger(projectId);
          setLedger(latest);
          setWorkbookOverride({ projectId, path: latest.workbook_path });
          setInvoiceError("The invoice changed elsewhere. Latest values are loaded; try again.");
        } catch {
          setInvoiceError("The invoice changed elsewhere. Reload the page, then try again.");
        }
      } else {
        setLedger(previousLedger);
        setInvoiceError(
          saveError instanceof ApiError
            ? saveError.message
            : "Could not save the invoice change. Try again.",
        );
      }
    } finally {
      setIsSavingInvoice(false);
    }
  }

  function updateAllocation(row: InvoiceLedgerRow, costItemKey: string) {
    if (!ledger) return;
    const previous = ledger;
    const target = ledger.cost_items.find((item) => item.item_key === costItemKey);
    if (!target) return;
    setLedger({
      ...ledger,
      rows: ledger.rows.map((item) =>
        item.allocation_id === row.allocation_id
          ? {
              ...item,
              cost_item_key: target.item_key,
              cost_item_label: target.item,
              mapping_method: "manual",
              review_status: "mapped",
            }
          : item,
      ),
    });
    void applyInvoiceEdit(
      () =>
        api.updateInvoiceAllocation(projectId, row.allocation_id, {
          expected_revision: row.invoice_revision,
          expected_cost_plan_version: previous.cost_plan_version,
          cost_item_key: costItemKey,
        }),
      previous,
    );
  }

  function updateInvoice(
    row: InvoiceLedgerRow,
    changes: { paid?: boolean; billing_month?: string },
  ) {
    if (!ledger) return;
    const previous = ledger;
    setLedger({
      ...ledger,
      rows: ledger.rows.map((item) =>
        item.invoice_id === row.invoice_id ? { ...item, ...changes } : item,
      ),
    });
    void applyInvoiceEdit(
      () =>
        api.updateInvoice(projectId, row.invoice_id, {
          expected_revision: row.invoice_revision,
          expected_cost_plan_version: previous.cost_plan_version,
          ...changes,
        }),
      previous,
    );
  }

  const sheet = useMemo(
    () => preview?.sheets.find((candidate) => candidate.name === activeSheet) ?? null,
    [activeSheet, preview],
  );
  const invoiceReadOnlyMessage =
    ledger && workbookVersion(activeWorkbookPath) !== ledger.cost_plan_version
      ? `This is an archived workbook. Open Cost Plan v${ledger.cost_plan_version} to edit invoices.`
      : null;

  if (isLoading) {
    return (
      <div className="flex min-h-48 items-center justify-center text-sm text-muted-foreground">
        Loading workbook...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-48 items-center justify-center p-4 text-sm text-destructive">
        {error}
      </div>
    );
  }

  if (!preview || !sheet) {
    return (
      <div className="flex min-h-48 items-center justify-center text-sm text-muted-foreground">
        Workbook preview is empty.
      </div>
    );
  }

  return (
    <div className="min-w-0">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b px-3 py-2">
        <div className="flex min-w-0 flex-wrap gap-1">
          {preview.sheets.map((item) => (
            <Button
              key={item.name}
              type="button"
              size="sm"
              variant={item.name === sheet.name ? "secondary" : "ghost"}
              onClick={() => setActiveSheet(item.name)}
            >
              <Table2 className="size-4" aria-hidden />
              {item.name}
            </Button>
          ))}
        </div>
        {preview.warnings.length ? (
          <span
            className="inline-flex items-center gap-1 text-xs"
            style={{ color: "var(--warn-text)" }}
          >
            <AlertTriangle className="size-3.5" aria-hidden />
            {preview.warnings.length} warning{preview.warnings.length === 1 ? "" : "s"}
          </span>
        ) : null}
      </div>
      {sheet.name === "Invoices" &&
      (isSavingInvoice || invoiceError || invoiceSaveMessage || invoiceReadOnlyMessage) ? (
        <div
          className={cn(
            "flex items-center gap-2 border-b px-3 py-2 text-xs",
            invoiceError
              ? "bg-[var(--alert-bg)] text-[var(--alert-text)]"
              : invoiceReadOnlyMessage
                ? "bg-[var(--info-bg)] text-[var(--info-text)]"
              : "bg-[var(--ok-bg)] text-[var(--ok-text)]",
          )}
          role={invoiceError ? "alert" : "status"}
        >
          {isSavingInvoice ? (
            <Loader2 className="size-3.5 animate-spin motion-reduce:animate-none" aria-hidden />
          ) : invoiceError || invoiceReadOnlyMessage ? (
            <AlertTriangle className="size-3.5" aria-hidden />
          ) : (
            <Check className="size-3.5" aria-hidden />
          )}
          <span>
            {isSavingInvoice
              ? "Saving invoice change and publishing a new Cost Plan version…"
              : invoiceError ?? invoiceSaveMessage ?? invoiceReadOnlyMessage}
          </span>
        </div>
      ) : null}
      {sheet.name === "Summary" ? (
        <SummarySheetTable sheet={sheet} />
      ) : (
        <RegisterSheetTable
          sheet={sheet}
          invoiceLedger={invoiceReadOnlyMessage ? null : ledger}
          isSavingInvoice={isSavingInvoice}
          onAllocationChange={updateAllocation}
          onInvoiceChange={updateInvoice}
        />
      )}
    </div>
  );
}

const SUMMARY_COLUMN_COUNT = 12;
const SUMMARY_MONEY_COLUMN_START = 3;
const SUMMARY_GST_LABEL_COL = 9;
const SUMMARY_GST_VALUE_COL = 10;

type WorkbookCellKind =
  | "title"
  | "subtitle"
  | "header"
  | "control"
  | "subtotal"
  | "grand"
  | "muted"
  | "data";

/** Excel workbook fills mapped to semantic preview kinds (ignore raw hex in the UI). */
const EXCEL_FILL_KIND: Record<string, WorkbookCellKind> = {
  "1F4E78": "title",
  D9EAF7: "subtitle",
  "44546A": "header",
  FFF2CC: "control",
  E2F0D9: "subtotal",
  BDD7EE: "grand",
  F2F2F2: "muted",
};

const CELL_KIND_CLASS: Record<WorkbookCellKind, string> = {
  title: "workbook-cell--title",
  subtitle: "workbook-cell--subtitle",
  header: "workbook-cell--header",
  control: "workbook-cell--control",
  subtotal: "workbook-cell--subtotal",
  grand: "workbook-cell--grand",
  muted: "workbook-cell--muted",
  data: "workbook-cell",
};

function SummarySheetTable({ sheet }: { sheet: WorkbookSheetPreview }) {
  const headerRow = headerRowIndex(sheet);
  const visibleRows = sheet.rows
    .map((row, rowIndex) => ({
      row,
      rowIndex,
      styleRow: sheet.styles[rowIndex],
    }))
    .filter(({ rowIndex }) => shouldShowPreviewRow(sheet.name, rowIndex));

  return (
    <div className="workbook-table-wrap max-h-[32rem] px-1 pb-1">
      <table
        className="workbook-table workbook-table--summary border-separate border-spacing-0 text-[10px] leading-tight lg:text-[11px]"
      >
        <colgroup>
          <col className="workbook-col-code" />
          <col className="workbook-col-category" />
          <col className="workbook-col-item" />
          {Array.from({ length: 9 }, (_, index) => (
            <col key={`money-${index}`} className="workbook-col-money" />
          ))}
        </colgroup>
        <tbody>
          {visibleRows.map(({ row, rowIndex, styleRow }, displayIndex) => {
            if (rowIndex === 0) {
              return (
                <SummaryBannerRow
                  key={`${sheet.name}-${rowIndex}`}
                  sheet={sheet}
                  row={row}
                  rowIndex={rowIndex}
                  styleRow={styleRow}
                  headerRow={headerRow}
                  displayIndex={displayIndex}
                />
              );
            }
            if (rowIndex === 1) {
              return (
                <SummaryGstRow
                  key={`${sheet.name}-${rowIndex}`}
                  sheet={sheet}
                  row={row}
                  rowIndex={rowIndex}
                  styleRow={styleRow}
                  headerRow={headerRow}
                  displayIndex={displayIndex}
                />
              );
            }
            return (
              <SummaryDataRow
                key={`${sheet.name}-${rowIndex}`}
                sheet={sheet}
                row={row}
                rowIndex={rowIndex}
                styleRow={styleRow}
                headerRow={headerRow}
                displayIndex={displayIndex}
              />
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function SummaryBannerRow({
  sheet,
  row,
  rowIndex,
  styleRow,
  headerRow,
  displayIndex,
}: SummaryRowProps) {
  const title = row.find((value) => value.trim().length > 0) ?? "";
  const cellKind = previewCellKind(
    sheet,
    rowIndex,
    0,
    row,
    headerRow,
    styleRow,
  );

  return (
    <tr>
      <td
        colSpan={SUMMARY_COLUMN_COUNT}
        className={cn(
          "border-b border-r border-l px-2 py-1.5 align-middle",
          displayIndex === 0 && "border-t",
          CELL_KIND_CLASS[cellKind],
          "workbook-cell--banner text-xs lg:text-sm",
        )}
        title={title}
      >
        {title}
      </td>
    </tr>
  );
}

function SummaryGstRow({
  sheet,
  row,
  rowIndex,
  styleRow,
  headerRow,
  displayIndex,
}: SummaryRowProps) {
  const gstText = row[0] || (row.find((value) => value.trim().length > 0) ?? "");
  const monthLabel = row[SUMMARY_GST_LABEL_COL] ?? "";
  const monthValue = row[SUMMARY_GST_VALUE_COL] ?? "";
  const trailing = row[SUMMARY_COLUMN_COUNT - 1] ?? "";

  return (
    <tr>
      <td
        colSpan={SUMMARY_GST_LABEL_COL}
        className={cn(
          "border-b border-r border-l px-2 py-1 align-middle workbook-cell--wrap",
          displayIndex === 0 && "border-t",
          CELL_KIND_CLASS.data,
          !gstText && "workbook-cell--empty",
        )}
        title={gstText}
      >
        {gstText}
      </td>
      <SummaryCell
        sheet={sheet}
        row={row}
        rowIndex={rowIndex}
        columnIndex={SUMMARY_GST_LABEL_COL}
        value={monthLabel}
        styleRow={styleRow}
        headerRow={headerRow}
        displayIndex={displayIndex}
        borderLeft
      />
      <SummaryCell
        sheet={sheet}
        row={row}
        rowIndex={rowIndex}
        columnIndex={SUMMARY_GST_VALUE_COL}
        value={monthValue}
        styleRow={styleRow}
        headerRow={headerRow}
        displayIndex={displayIndex}
      />
      <SummaryCell
        sheet={sheet}
        row={row}
        rowIndex={rowIndex}
        columnIndex={SUMMARY_COLUMN_COUNT - 1}
        value={trailing}
        styleRow={styleRow}
        headerRow={headerRow}
        displayIndex={displayIndex}
      />
    </tr>
  );
}

function SummaryDataRow({
  sheet,
  row,
  rowIndex,
  styleRow,
  headerRow,
  displayIndex,
}: SummaryRowProps) {
  return (
    <tr>
      {row.map((value, columnIndex) => (
        <SummaryCell
          key={`${sheet.name}-${rowIndex}-${columnIndex}`}
          sheet={sheet}
          row={row}
          rowIndex={rowIndex}
          columnIndex={columnIndex}
          value={value}
          styleRow={styleRow}
          headerRow={headerRow}
          displayIndex={displayIndex}
          borderLeft={columnIndex === 0}
        />
      ))}
    </tr>
  );
}

function SummaryCell({
  sheet,
  row,
  rowIndex,
  columnIndex,
  value,
  styleRow,
  headerRow,
  displayIndex,
  borderLeft = false,
}: {
  sheet: WorkbookSheetPreview;
  row: string[];
  rowIndex: number;
  columnIndex: number;
  value: string;
  styleRow: WorkbookCellStyle[] | undefined;
  headerRow: number;
  displayIndex: number;
  borderLeft?: boolean;
}) {
  const style = styleRow?.[columnIndex];
  const cellKind = previewCellKind(
    sheet,
    rowIndex,
    columnIndex,
    row,
    headerRow,
    styleRow,
  );
  const isHeader = cellKind === "header";
  const isMoneyColumn = columnIndex >= SUMMARY_MONEY_COLUMN_START;
  const isCodeColumn = columnIndex === 0;

  return (
    <td
      className={cn(
        "border-b border-r px-1 py-1 align-middle",
        borderLeft && "border-l",
        displayIndex === 0 && "border-t",
        CELL_KIND_CLASS[cellKind],
        !value && "workbook-cell--empty",
        isHeader && "workbook-cell--header-label sticky top-0 z-10",
        isHeader && isMoneyColumn && "workbook-cell--header-money",
        !isHeader && isMoneyColumn && "workbook-cell--money",
        !isHeader && isCodeColumn && "workbook-cell--code",
        (isHeader || columnIndex === 1 || columnIndex === 2) && "workbook-cell--wrap",
        !isHeader && style?.bold && "font-semibold",
      )}
      title={value}
    >
      <span className="block">{value}</span>
    </td>
  );
}

function RegisterSheetTable({
  sheet,
  invoiceLedger,
  isSavingInvoice,
  onAllocationChange,
  onInvoiceChange,
}: {
  sheet: WorkbookSheetPreview;
  invoiceLedger: InvoiceLedger | null;
  isSavingInvoice: boolean;
  onAllocationChange: (row: InvoiceLedgerRow, costItemKey: string) => void;
  onInvoiceChange: (
    row: InvoiceLedgerRow,
    changes: { paid?: boolean; billing_month?: string },
  ) => void;
}) {
  const headerRow = headerRowIndex(sheet);
  const visibleRows = sheet.rows.map((row, rowIndex) => ({
    row,
    rowIndex,
    styleRow: sheet.styles[rowIndex],
  }));
  const columnCount = sheet.column_count || (visibleRows[0]?.row.length ?? 0);
  const moneyColumns = registerMoneyColumns(sheet.name, columnCount);
  const colClasses = registerColumnClasses(sheet.name, columnCount);

  return (
    <div className="workbook-table-wrap max-h-[32rem] px-1 pb-1">
      <table
        className="workbook-table workbook-table--register border-separate border-spacing-0 text-[10px] leading-tight lg:text-[11px]"
      >
        <colgroup>
          {colClasses.map((className, index) => (
            <col key={`${sheet.name}-col-${index}`} className={className} />
          ))}
        </colgroup>
        <tbody>
          {visibleRows.map(({ row, rowIndex, styleRow }, displayIndex) => {
            const isBanner = headerRow > 0 && rowIndex < headerRow;
            const bannerText = isBanner ? row.find((cell) => cell.trim().length > 0) ?? "" : "";
            const invoiceRow =
              sheet.name === "Invoices" && rowIndex > headerRow
                ? invoiceLedger?.rows[rowIndex - headerRow - 1]
                : undefined;

            if (isBanner) {
              return (
                <tr key={`${sheet.name}-${rowIndex}`}>
                  <td
                    colSpan={columnCount}
                    className={cn(
                      "border-b border-r border-l px-2 py-1.5 align-middle",
                      displayIndex === 0 && "border-t",
                      rowIndex === 0
                        ? CELL_KIND_CLASS.subtitle
                        : CELL_KIND_CLASS.data,
                      "workbook-cell--banner text-xs lg:text-sm",
                    )}
                    title={bannerText}
                  >
                    {bannerText}
                  </td>
                </tr>
              );
            }

            return (
              <tr key={`${sheet.name}-${rowIndex}`}>
                {row.map((value, columnIndex) => {
                  const style = styleRow?.[columnIndex];
                  const cellKind = previewCellKind(
                    sheet,
                    rowIndex,
                    columnIndex,
                    row,
                    headerRow,
                    styleRow,
                  );
                  const isHeader = cellKind === "header";
                  const isMoneyCell = moneyColumns.has(columnIndex) || isMoney(value);

                  return (
                    <td
                      key={`${sheet.name}-${rowIndex}-${columnIndex}`}
                      className={cn(
                        "border-b border-r px-1 py-1 align-middle",
                        columnIndex === 0 && "border-l",
                        displayIndex === 0 && "border-t",
                        CELL_KIND_CLASS[cellKind],
                        !value && "workbook-cell--empty",
                        isHeader && "workbook-cell--header-label sticky top-0 z-10",
                        isHeader && isMoneyCell && "workbook-cell--header-money",
                        !isHeader && isMoneyCell && "workbook-cell--money",
                        !isHeader && style?.bold && "font-semibold",
                        (isHeader || !isMoneyCell) && "workbook-cell--wrap",
                      )}
                      title={value}
                    >
                      {invoiceRow && invoiceLedger && [5, 7, 8].includes(columnIndex) ? (
                        <InvoiceRegisterControl
                          columnIndex={columnIndex}
                          row={invoiceRow}
                          ledger={invoiceLedger}
                          disabled={isSavingInvoice}
                          onAllocationChange={onAllocationChange}
                          onInvoiceChange={onInvoiceChange}
                        />
                      ) : (
                        <span className="block">{value}</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function InvoiceRegisterControl({
  columnIndex,
  row,
  ledger,
  disabled,
  onAllocationChange,
  onInvoiceChange,
}: {
  columnIndex: number;
  row: InvoiceLedgerRow;
  ledger: InvoiceLedger;
  disabled: boolean;
  onAllocationChange: (row: InvoiceLedgerRow, costItemKey: string) => void;
  onInvoiceChange: (
    row: InvoiceLedgerRow,
    changes: { paid?: boolean; billing_month?: string },
  ) => void;
}) {
  if (columnIndex === 5) {
    return (
      <select
        className={cn(
          "workbook-inline-control",
          row.review_status === "needs_review" && "workbook-inline-control--review",
        )}
        value={row.cost_item_key ?? ""}
        disabled={disabled}
        aria-label={`Cost item for invoice ${row.invoice_number}: ${row.description}`}
        title={
          row.review_status === "needs_review"
            ? "Select an existing Cost Plan item to resolve this invoice line"
            : `Mapped by ${row.mapping_method.replaceAll("_", " ")}`
        }
        onChange={(event) => {
          if (event.target.value) onAllocationChange(row, event.target.value);
        }}
      >
        <option value="" disabled>
          Choose cost item
        </option>
        {costItemGroups(ledger).map(([category, items]) => (
          <optgroup key={category} label={category}>
            {items.map((item) => (
              <option key={item.item_key} value={item.item_key}>
                {item.cost_code} · {item.item}{item.budget === null ? " · TBC" : ""}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
    );
  }

  if (columnIndex === 7) {
    return (
      <input
        type="month"
        className="workbook-inline-control workbook-inline-control--month"
        value={row.billing_month.slice(0, 7)}
        disabled={disabled}
        aria-label={`Billing month for invoice ${row.invoice_number}`}
        onChange={(event) => {
          if (event.target.value) {
            onInvoiceChange(row, { billing_month: `${event.target.value}-01` });
          }
        }}
      />
    );
  }

  return (
    <button
      type="button"
      className={cn(
        "workbook-paid-toggle",
        row.paid && "workbook-paid-toggle--paid",
      )}
      disabled={disabled}
      aria-pressed={row.paid}
      aria-label={`Mark invoice ${row.invoice_number} ${
        row.paid ? "unpaid" : "paid"
      }`}
      onClick={() => onInvoiceChange(row, { paid: !row.paid })}
    >
      {row.paid ? <Check className="size-3" aria-hidden /> : null}
      {row.paid ? "Yes" : "No"}
    </button>
  );
}

function costItemGroups(
  ledger: InvoiceLedger,
): [string, InvoiceLedger["cost_items"]][] {
  const groups = new Map<string, InvoiceLedger["cost_items"]>();
  for (const item of ledger.cost_items) {
    const group = groups.get(item.category) ?? [];
    group.push(item);
    groups.set(item.category, group);
  }
  return [...groups.entries()];
}

type SummaryRowProps = {
  sheet: WorkbookSheetPreview;
  row: string[];
  rowIndex: number;
  styleRow: WorkbookCellStyle[] | undefined;
  headerRow: number;
  displayIndex: number;
};

function registerMoneyColumns(sheetName: string, columnCount: number): Set<number> {
  if (sheetName === "Invoices") return new Set([6]);
  if (sheetName === "Variations") return new Set([4, 6]);
  const money = new Set<number>();
  for (let index = 3; index < columnCount; index += 1) {
    money.add(index);
  }
  return money;
}

function registerColumnClasses(sheetName: string, columnCount: number): string[] {
  if (sheetName === "Invoices") {
    return [
      "workbook-col-date",
      "workbook-col-text",
      "workbook-col-narrow",
      "workbook-col-narrow",
      "workbook-col-text",
      "workbook-col-text",
      "workbook-col-money",
      "workbook-col-date",
      "workbook-col-narrow",
    ].slice(0, columnCount);
  }
  if (sheetName === "Variations") {
    return [
      "workbook-col-date",
      "workbook-col-text",
      "workbook-col-text",
      "workbook-col-narrow",
      "workbook-col-money",
      "workbook-col-date",
      "workbook-col-money",
    ].slice(0, columnCount);
  }
  return Array.from({ length: columnCount }, () => "workbook-col-text");
}

function shouldShowPreviewRow(sheetName: string, rowIndex: number): boolean {
  return sheetName !== "Summary" || rowIndex !== 2;
}

function previewCellKind(
  _sheet: WorkbookSheetPreview,
  rowIndex: number,
  columnIndex: number,
  row: string[],
  headerRow: number,
  styleRow: WorkbookCellStyle[] | undefined,
): WorkbookCellKind {
  const cellFillKind = fillKindFromHex(styleRow?.[columnIndex]?.fill_color);
  if (cellFillKind === "control") return "control";

  if (rowIndex === headerRow) return "header";

  if (rowIndex === 0 && headerRow > 0) return "subtitle";

  const rowText = row.join(" ").toLowerCase();
  if (rowText.includes("grand total")) return "grand";
  if (rowText.includes("subtotal")) return "subtotal";

  if (rowIndex >= headerRow || headerRow < 0) {
    const rowFillKind = fillKindFromHex(
      styleRow?.find((cell) => cell.fill_color)?.fill_color,
    );
    if (rowFillKind && rowFillKind !== "subtitle") return rowFillKind;
  }

  return "data";
}

function fillKindFromHex(fillColor: string | null | undefined): WorkbookCellKind | null {
  if (!fillColor) return null;
  const normalised = fillColor.replace("#", "").toUpperCase();
  return EXCEL_FILL_KIND[normalised] ?? null;
}

function headerRowIndex(sheet: WorkbookSheetPreview): number {
  const signatures = ["Cost Code", "Invoice Date", "Date Submitted"];
  return sheet.rows.findIndex((row) =>
    signatures.some((signature) => row.includes(signature)),
  );
}

function isMoney(value: string): boolean {
  return /^-?\$[\d,]+$/.test(value);
}

function latestWorkbookPath(basePath: string, overridePath: string | null): string {
  if (!overridePath) return basePath;
  return workbookVersion(overridePath) > workbookVersion(basePath)
    ? overridePath
    : basePath;
}

function workbookVersion(path: string): number {
  return Number(/Cost_Plan_v(\d+)/i.exec(path)?.[1] ?? 0);
}
