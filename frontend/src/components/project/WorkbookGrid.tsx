import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Table2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import type { WorkbookPreview, WorkbookSheetPreview } from "@/lib/types/project";
import { cn } from "@/lib/utils";

export function WorkbookGrid({
  projectId,
  workbookPath,
}: {
  projectId: string;
  workbookPath: string;
}) {
  const [preview, setPreview] = useState<WorkbookPreview | null>(null);
  const [activeSheet, setActiveSheet] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadWorkbookPreview() {
      setIsLoading(true);
      setError(null);
      try {
        const data = await api.getWorkbookPreview(projectId, workbookPath);
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
  }, [projectId, workbookPath]);

  const sheet = useMemo(
    () => preview?.sheets.find((candidate) => candidate.name === activeSheet) ?? null,
    [activeSheet, preview],
  );

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
          <span className="inline-flex items-center gap-1 text-xs text-amber-700">
            <AlertTriangle className="size-3.5" aria-hidden />
            {preview.warnings.length} warning{preview.warnings.length === 1 ? "" : "s"}
          </span>
        ) : null}
      </div>
      <SheetTable sheet={sheet} />
    </div>
  );
}

function SheetTable({ sheet }: { sheet: WorkbookSheetPreview }) {
  const headerRow = headerRowIndex(sheet);
  return (
    <div className="max-h-[32rem] overflow-auto">
      <table className="min-w-max border-separate border-spacing-0 text-xs">
        <tbody>
          {sheet.rows.map((row, rowIndex) => (
            <tr key={`${sheet.name}-${rowIndex}`}>
              {row.map((value, columnIndex) => {
                const style = sheet.styles[rowIndex]?.[columnIndex];
                const isHeader = rowIndex === headerRow;
                const isTitle = headerRow >= 0 && rowIndex < headerRow;
                return (
                  <td
                    key={`${sheet.name}-${rowIndex}-${columnIndex}`}
                    className={cn(
                      "h-8 max-w-72 border-b border-r px-2 py-1 align-middle",
                      columnIndex === 0 && "border-l",
                      rowIndex === 0 && "border-t",
                      isHeader && "sticky top-0 z-10 font-semibold text-background",
                      !isHeader && style?.bold && "font-semibold",
                      isTitle && "text-sm",
                      isMoney(value) && "text-right tabular-nums",
                      value ? "text-foreground" : "text-muted-foreground",
                    )}
                    style={{
                      backgroundColor: isHeader
                        ? "#44546A"
                        : style?.fill_color ?? undefined,
                    }}
                    title={value}
                  >
                    <span className="block truncate">{value}</span>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function headerRowIndex(sheet: WorkbookSheetPreview): number {
  const signatures = [
    "Cost Code",
    "Invoice Date",
    "Date Submitted",
  ];
  return sheet.rows.findIndex((row) =>
    signatures.some((signature) => row.includes(signature)),
  );
}

function isMoney(value: string): boolean {
  return /^-?\$[\d,]+$/.test(value);
}
