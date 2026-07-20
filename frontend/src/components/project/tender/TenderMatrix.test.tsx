import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TenderMatrix } from "@/components/project/tender/TenderMatrix";
import { api } from "@/lib/api";
import type {
  TenderComparison,
  TenderMatrixQuoteTotal,
  TenderMatrixResponse,
} from "@/lib/types/tender";

vi.mock("@tanstack/react-virtual", () => ({
  useVirtualizer: ({ count }: { count: number }) => ({
    getTotalSize: () => count * 64,
    getVirtualItems: () =>
      Array.from({ length: count }, (_, index) => ({
        index,
        start: index * 64,
      })),
  }),
}));

vi.mock("@/lib/api", () => ({
  api: {
    getTenderMatrix: vi.fn(),
    getTenderComparison: vi.fn(),
    getTenderQaQueue: vi.fn(),
    getTenderTaxonomy: vi.fn(),
    getTenderTrades: vi.fn(),
    searchTenderTaxonomy: vi.fn(),
    acceptAllTenderQa: vi.fn(),
    resolveTenderQaItem: vi.fn(),
  },
}));

describe("TenderMatrix", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getTenderMatrix).mockResolvedValue(matrix);
    vi.mocked(api.getTenderComparison).mockResolvedValue(comparison);
    vi.mocked(api.getTenderQaQueue).mockResolvedValue({ items: [] });
    vi.mocked(api.getTenderTaxonomy).mockResolvedValue([]);
    vi.mocked(api.getTenderTrades).mockResolvedValue({
      comparison_id: "comparison-1",
      trades: [],
    });
    vi.mocked(api.searchTenderTaxonomy).mockResolvedValue([]);
    vi.mocked(api.resolveTenderQaItem).mockResolvedValue({
      id: "mapping-1",
      entity_type: "mapping",
      action: "correct",
      qa_state: "corrected",
    });
  });

  it("posts a mapping correction when a multi-candidate choice changes", async () => {
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <TenderMatrix projectId="project-1" comparisonId="comparison-1" />
      </MemoryRouter>,
    );

    const cell = await screen.findByRole("button", {
      name: /Included .* Retaining walls, Apex Homes/,
    });
    await user.click(cell);
    const choice = await screen.findByLabelText("Mapping choice for Apex Homes Retaining walls");
    await user.selectOptions(choice, "03.01");

    await waitFor(() =>
      expect(api.resolveTenderQaItem).toHaveBeenCalledWith("mapping-1", {
        action: "correct",
        corrected_value: { cell_code: "03.01" },
        reason: "Inline matrix mapping override",
      }),
    );
    await waitFor(() => expect(api.getTenderMatrix).toHaveBeenCalledTimes(2));
    expect(api.getTenderQaQueue).toHaveBeenCalledTimes(2);
  });

  it("labels totals as ex GST and shows a reconciliation strip", async () => {
    vi.mocked(api.getTenderMatrix).mockResolvedValue({
      ...matrix,
      totals: [quoteTotal({ reconciliation: "match", residual_cents: 0 })],
    });

    render(
      <MemoryRouter>
        <TenderMatrix projectId="project-1" comparisonId="comparison-1" />
      </MemoryRouter>,
    );

    expect(await screen.findByText("Total (ex GST)")).toBeInTheDocument();
    expect(screen.getByText("Computed (ex GST)")).toBeInTheDocument();
    expect(screen.getByText(/Stated \(native\):/)).toBeInTheDocument();
    expect(screen.getByText(/Counted:/)).toBeInTheDocument();
    expect(screen.getByText(/Residual:/)).toBeInTheDocument();
  });

  it("highlights a non-zero residual and shows the cost-plus badge", async () => {
    vi.mocked(api.getTenderMatrix).mockResolvedValue({
      ...matrix,
      totals: [
        quoteTotal({
          computed_total_cents: 110_000_00,
          residual_cents: 10_000_00,
          delta_cents: -10_000_00,
          delta_ratio: 0.0833,
          reconciliation: "mismatch",
          non_comparable: true,
        }),
      ],
    });

    render(
      <MemoryRouter>
        <TenderMatrix projectId="project-1" comparisonId="comparison-1" />
      </MemoryRouter>,
    );

    expect(
      await screen.findByText(/Residual:.*10,000/),
    ).toBeInTheDocument();
    expect(
      screen.getAllByText(
        /Cost-plus — excludes builder's margin; not directly comparable/,
      ).length,
    ).toBeGreaterThan(0);
  });

  it("saves an inline cell status correction and refetches the matrix", async () => {
    const user = userEvent.setup();
    vi.mocked(api.getTenderQaQueue).mockResolvedValue({
      items: [
        {
          id: "cell-status-1",
          entity_type: "cell_status",
          report_impact_cents: 500_000,
          confidence: 0.5,
          payload: {
            quote_id: "quote-1",
            cell_code: "03.05",
            status: "included",
            amount_cents: 500_000,
            evidence: {},
          },
        },
      ],
    });

    render(
      <MemoryRouter>
        <TenderMatrix projectId="project-1" comparisonId="comparison-1" />
      </MemoryRouter>,
    );

    const cell = await screen.findByRole("button", {
      name: /Included .* Retaining walls, Apex Homes/,
    });
    await user.click(cell);
    await user.click(await screen.findByRole("button", { name: /Adjudicate/ }));
    await user.click(await screen.findByRole("button", { name: /^Edit$/ }));
    const amountInput = await screen.findByLabelText("Amount");
    await user.clear(amountInput);
    await user.type(amountInput, "6000");
    await user.click(screen.getByRole("button", { name: /Save correction/ }));

    await waitFor(() =>
      expect(api.resolveTenderQaItem).toHaveBeenCalledWith("cell-status-1", {
        action: "correct",
        corrected_value: { status: "included", amount_cents: 600_000 },
        reason: null,
      }),
    );
    await waitFor(() => expect(api.getTenderMatrix).toHaveBeenCalledTimes(2));
  });

  it("classifies documents from the review strip", async () => {
    const user = userEvent.setup();
    vi.mocked(api.getTenderQaQueue).mockResolvedValue({
      items: [
        {
          id: "doc-1",
          entity_type: "document_classification",
          report_impact_cents: 0,
          confidence: null,
          payload: {
            quote_id: "quote-1",
            filename: "quote.pdf",
            doc_type: null,
          },
        },
      ],
    });

    render(
      <MemoryRouter>
        <TenderMatrix projectId="project-1" comparisonId="comparison-1" />
      </MemoryRouter>,
    );

    expect(
      await screen.findByText(/1 document needs classification/),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Classify/ }));
    await user.click(await screen.findByRole("button", { name: /^Edit$/ }));
    const docType = await screen.findByLabelText("Document type");
    await user.selectOptions(docType, "quote_letter");
    await user.click(screen.getByRole("button", { name: /Save correction/ }));

    await waitFor(() =>
      expect(api.resolveTenderQaItem).toHaveBeenCalledWith("doc-1", {
        action: "correct",
        corrected_value: { doc_type: "quote_letter" },
        reason: null,
      }),
    );
  });

  it("suppresses a quote-level flag from the review strip", async () => {
    const user = userEvent.setup();
    vi.mocked(api.getTenderQaQueue).mockResolvedValue({
      items: [
        {
          id: "flag-1",
          entity_type: "flag",
          report_impact_cents: 0,
          confidence: null,
          payload: {
            quote_id: "quote-1",
            cell_code: null,
            flag_type: "arithmetic_inconsistency",
            severity: "warning",
            headline: "Arithmetic inconsistency",
            detail: "Line items do not reconcile to the printed total.",
          },
        },
      ],
    });

    render(
      <MemoryRouter>
        <TenderMatrix projectId="project-1" comparisonId="comparison-1" />
      </MemoryRouter>,
    );

    expect(await screen.findByText(/1 quote-level finding/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Adjudicate/ }));
    await user.click(await screen.findByRole("button", { name: /Suppress/ }));

    await waitFor(() =>
      expect(api.resolveTenderQaItem).toHaveBeenCalledWith("flag-1", {
        action: "suppress",
        corrected_value: null,
        reason: null,
      }),
    );
  });

  it("marks quotes with no stated total as not stated", async () => {
    vi.mocked(api.getTenderMatrix).mockResolvedValue({
      ...matrix,
      totals: [
        quoteTotal({
          stated_native_cents: null,
          stated_total_cents: null,
          stated_total_source: null,
          delta_cents: null,
          delta_ratio: null,
          reconciliation: "not_stated",
        }),
      ],
    });

    render(
      <MemoryRouter>
        <TenderMatrix projectId="project-1" comparisonId="comparison-1" />
      </MemoryRouter>,
    );

    expect(await screen.findByText("Not stated in quote")).toBeInTheDocument();
  });

  it("labels the header figure as stated native", async () => {
    vi.mocked(api.getTenderMatrix).mockResolvedValue({
      ...matrix,
      totals: [quoteTotal({})],
    });

    render(
      <MemoryRouter>
        <TenderMatrix projectId="project-1" comparisonId="comparison-1" />
      </MemoryRouter>,
    );

    expect(await screen.findAllByText("Stated (native)")).not.toHaveLength(0);
  });
});

function quoteTotal(
  overrides: Partial<TenderMatrixQuoteTotal>,
): TenderMatrixQuoteTotal {
  return {
    quote_id: "quote-1",
    computed_total_cents: 120_000_00,
    basis: "ex",
    residual_cents: 0,
    unallocated_cents: 0,
    not_itemised_cents: 0,
    stated_native_cents: 120_000_00,
    stated_total_cents: 120_000_00,
    stated_total_source: "extracted",
    non_comparable: false,
    delta_cents: 0,
    delta_ratio: 0,
    reconciliation: "match",
    ...overrides,
  };
}

const comparison: TenderComparison = {
  id: "comparison-1",
  project_id: "project-1",
  status: "qa",
  context: {
    context_version: 1,
    context_source: "repository_selection",
    state: null,
    region: null,
    build_type: null,
    dwelling_class: "class_1a",
    storeys: null,
    floor_area_m2: null,
    site_area_m2: null,
    soil_class: "unknown",
    slope_class: "unknown",
    bal_rating: "unknown",
    wind_rating: null,
    flood_overlay: null,
    heritage_overlay: null,
    existing_dwelling_era: null,
    demolition_required: null,
    spec_level: null,
    target_budget_cents: null,
    notes: null,
  },
  created_by: "user-1",
  created_at: "2026-07-08T00:00:00Z",
  updated_at: "2026-07-08T00:00:00Z",
  quotes: [
    {
      id: "quote-1",
      comparison_id: "comparison-1",
      builder_name: "Apex Homes",
      builder_abn: null,
      quote_ref: null,
      quote_date: null,
      stated_total_cents: 120_000_00,
      gst_treatment: "unclear",
      contract_type: "unknown",
      validity_days: null,
      stage: "complete",
      created_at: "2026-07-08T00:00:00Z",
      documents: [],
    },
  ],
};

const matrix: TenderMatrixResponse = {
  comparison_id: "comparison-1",
  totals: [],
  groups: [
    {
      name: "Site works",
      cells: [
        {
          code: "03.05",
          name: "Retaining walls",
          quotes: {
            "quote-1": {
              status: "included",
              amount_cents: 500_000,
              flags: [],
              mapping_choices: [
                {
                  mapping_id: "mapping-1",
                  selected_cell_code: "03.05",
                  locked: false,
                  candidates: [
                    {
                      cell_code: "03.05",
                      name: "Retaining walls",
                      similarity: 0.78,
                      via: "retaining",
                    },
                    {
                      cell_code: "03.01",
                      name: "Site costs",
                      similarity: 0.72,
                      via: "site costs",
                    },
                  ],
                },
              ],
            },
          },
        },
      ],
    },
  ],
};
