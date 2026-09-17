import { editableTableCells } from "@/lib/table-row-edit";

export type PriceCell = {
  amount: string | null;
  displayAmount: string | null;
  note: string;
};

export type PriceMatrix = {
  headers: string[];
  rows: { label: string; cells: PriceCell[] }[];
  sources: ReadonlyMap<string, string>;
};

function plain(value: string): string {
  return value.replace(/\\([\\`*[\]<>|])/g, "$1");
}

function priceCell(value: string): PriceCell {
  // Only the backend's leading, bold amount is counted. Figures in evidence
  // notes (rates, options, subtotals) never become spreadsheet amounts.
  const match = /^\*\*((?:\$|[A-Z]{3} )(-?(?:\d{1,3}(?:,\d{3})+|\d+)\.\d{2}))\*\*(?: · (.*))?$/.exec(value);
  return {
    amount: match ? match[2].replaceAll(",", "") : null,
    displayAmount: match?.[1] ?? null,
    note: plain(match ? match[3] ?? "" : value),
  };
}

export function parsePriceMatrix(table: string, document: string): PriceMatrix | null {
  const lines = table.trim().split(/\r?\n/).filter((line) => line.trim());
  if (lines.length < 5) return null;
  const headers = editableTableCells(lines[0]).map(plain);
  if (headers[0] !== "Item" || headers.length < 2 || headers.length > 5) return null;
  if (!headers.slice(1).every((header) => /\([A-Z]{3}, .+\)$/.test(header))) return null;
  const cells = lines.slice(2).map(editableTableCells);
  if (cells.some((row) => row.length !== headers.length)) return null;
  const rows = cells.map(([label, ...values]) => ({
    label: plain(label.replace(/^\*\*(.*)\*\*$/, "$1")),
    cells: values.map(priceCell),
  }));
  if (rows.slice(-3).map((row) => row.label).join("|") !== "Item total|Quoted total|Difference") return null;
  const sources = new Map<string, string>();
  for (const match of document.matchAll(/^(?:- )?\[(\d+)\] (.+)$/gm)) {
    sources.set(match[1], plain(match[2].trim()));
  }
  return { headers, rows, sources };
}

function textCell(value: string): string {
  const clean = Array.from(value, (char) =>
    char.charCodeAt(0) < 32 || char.charCodeAt(0) === 127 ? " " : char,
  ).join("").trim();
  // Quote evidence as text, including malicious formula-like quote labels.
  return /^[=+@-]/.test(clean) ? `'${clean}` : clean;
}

function tsvCell(value: string): string {
  return value.includes('"') ? `"${value.replaceAll('"', '""')}"` : value;
}

export function priceMatrixTsv(matrix: PriceMatrix): string {
  const itemCount = matrix.rows.length - 3;
  const output = [[textCell(matrix.headers[0]), ...matrix.headers.slice(1).flatMap((header) => [
    textCell(`${header} — Amount`), textCell(`${header} — Notes`),
  ])]];
  for (const [index, row] of matrix.rows.entries()) {
    output.push([textCell(row.label), ...row.cells.flatMap((cell) => {
      let amount = cell.amount ?? "";
      // Relative references keep the formulas valid wherever the user pastes.
      if (amount && index === itemCount && itemCount > 0) {
        amount = `=SUM(INDIRECT("R[-${itemCount}]C:R[-1]C",FALSE))`;
      } else if (amount && index === itemCount + 2) {
        amount = '=INDIRECT("R[-1]C",FALSE)-INDIRECT("R[-2]C",FALSE)';
      }
      const note = cell.note.replace(/\[(\d+)\]/g, (token, id: string) => matrix.sources.get(id) ?? token);
      return [amount, textCell(note)];
    })]);
  }
  return output.map((row) => row.map(tsvCell).join("\t")).join("\r\n");
}
