import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { MarkdownContent } from "@/components/project/MarkdownContent";
import { parsePriceMatrix, priceMatrixTsv } from "@/lib/price-matrix";

const TABLE = `| Item | Alder (AUD, excl. GST) | Banksia (AUD, excl. GST) |
| --- | --- | --- |
| Electrical | **$12,000.00** · Combined 2 quoted items; [1] (p. 2) | **$18,500.00** · [2] (p. 3) |
| Installation | **$8,000.00** · [1] (p. 2) | Included in Electrical; [2] (p. 3) |
| Credit | **$-500.00** · [1] (p. 4) | **$0.00** · [2] (p. 4) |
| **Item total** | **$19,500.00** | **$18,500.00** |
| **Quoted total** | **$20,000.00** · [1] (p. 5) | **$18,500.00** · [2] (p. 5) |
| **Difference** | **$500.00** · Unreconciled | **$0.00** · Amounts reconcile |`;
const DOCUMENT = `## Price matrix\n\n${TABLE}\n\n## Citation key\n\n- [1] Alder quote.pdf — Alder\n- [2] Banksia quote.pdf — Banksia\n`;
const writeText = vi.fn();

beforeEach(() => {
  writeText.mockReset().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
});

describe("price matrix", () => {
  it("keeps compact amounts and notes, and can show separate note columns", () => {
    render(<MarkdownContent markdown={DOCUMENT} />);
    const table = screen.getByRole("table", { name: "Price comparison matrix" });
    expect(within(table).getAllByRole("columnheader")).toHaveLength(3);
    expect(within(table).getByText("Included in Electrical; [2] (p. 3)")).toBeVisible();
    expect(within(table).getByText("$12,000.00")).toHaveClass("tabular-nums");
    fireEvent.click(screen.getByRole("button", { name: "Separate notes" }));
    expect(screen.getByRole("button", { name: "Compact view" })).toHaveAttribute("aria-pressed", "true");
    expect(within(table).getAllByRole("columnheader", { name: "Notes" })).toHaveLength(2);
  });

  it("copies numbers and blanks beside full source notes, with relative total formulas", async () => {
    render(<MarkdownContent markdown={DOCUMENT} />);
    fireEvent.click(screen.getByRole("button", { name: "Copy for Excel" }));
    await waitFor(() => expect(writeText).toHaveBeenCalledOnce());
    const text = writeText.mock.calls[0][0] as string;
    expect(text).toContain("Electrical\t12000.00\tCombined 2 quoted items; Alder quote.pdf — Alder (p. 2)\t18500.00");
    expect(text).toContain("Installation\t8000.00\tAlder quote.pdf — Alder (p. 2)\t\tIncluded in Electrical");
    expect(text).toContain("Credit\t-500.00\tAlder quote.pdf — Alder (p. 4)\t0.00");
    expect(text).toContain('=SUM(INDIRECT(""R[-3]C:R[-1]C"",FALSE))');
    expect(text).toContain('=INDIRECT(""R[-1]C"",FALSE)-INDIRECT(""R[-2]C"",FALSE)');
    expect(text).toContain("Quoted total\t20000.00");
    expect(text.split("\r\n").every((row) => row.split("\t").length === 5)).toBe(true);
    expect(screen.getByRole("status")).toHaveTextContent("Matrix copied for Excel");
  });

  it("reports clipboard failure without claiming success", async () => {
    writeText.mockRejectedValueOnce(new Error("denied"));
    render(<MarkdownContent markdown={DOCUMENT} />);
    fireEvent.click(screen.getByRole("button", { name: "Copy for Excel" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Couldn’t copy");
    expect(screen.queryByRole("button", { name: "Copied" })).not.toBeInTheDocument();
  });

  it("does not reinterpret older mixed price tables or unrelated registers", () => {
    expect(parsePriceMatrix("| Item | Firm |\n| --- | --- |\n| Work | Combined $200 [1] |", "")).toBeNull();
    expect(parsePriceMatrix(TABLE.replaceAll("Item total", "Allowance"), DOCUMENT)).toBeNull();
  });

  it("leaves an unchecked total blank and never extracts reference-only amounts", () => {
    const table = TABLE.replace("**$12,000.00** · Combined 2 quoted items", "Option $12,000.00 (reference only)")
      .replace("**$19,500.00**", "Not checked")
      .replace("**$500.00** · Unreconciled", "Not checked");
    const result = parsePriceMatrix(table, DOCUMENT)!;
    expect(result.rows[0].cells[0].amount).toBeNull();
    const text = priceMatrixTsv(result);
    expect(text).toContain("Electrical\t\tOption $12,000.00 (reference only)");
    expect(text).toContain("Item total\t\tNot checked");
    expect(text).toContain("Difference\t\tNot checked");
  });

  it("neutralises formula-like evidence and preserves escaped pipes and quotes", () => {
    const table = TABLE.replace("| Electrical |", '| =1+1 \\| scope |')
      .replace("Combined 2 quoted items; [1] (p. 2)", '=HYPERLINK("bad"); [1] (p. 2)');
    const result = parsePriceMatrix(table, DOCUMENT)!;
    const text = priceMatrixTsv(result);
    expect(text).toContain("'=1+1 | scope\t12000.00");
    expect(text).toContain("'=HYPERLINK");
    expect(text).toContain('""bad""');
  });

  it("preserves valid GFM rows without outer pipes and rejects malformed money", () => {
    const table = TABLE.replaceAll(/^\| | \|$/gm, "").replace("$12,000.00", "$9,5556.80");
    const result = parsePriceMatrix(table, DOCUMENT)!;
    expect(result.rows).toHaveLength(6);
    expect(result.rows[0].cells[0].amount).toBeNull();
    expect(result.rows[0].cells[1].amount).toBe("18500.00");
  });
});
