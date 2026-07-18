import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TenderMatrix } from "@/components/project/tender/TenderMatrix";
import { api } from "@/lib/api";
import type { TenderComparison, TenderMatrixResponse } from "@/lib/types/tender";

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
    resolveTenderQaItem: vi.fn(),
  },
}));

describe("TenderMatrix", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getTenderMatrix).mockResolvedValue(matrix);
    vi.mocked(api.getTenderComparison).mockResolvedValue(comparison);
    vi.mocked(api.getTenderQaQueue).mockResolvedValue({ items: [] });
    vi.mocked(api.resolveTenderQaItem).mockResolvedValue({
      id: "mapping-1",
      entity_type: "mapping",
      action: "correct",
      qa_state: "corrected",
    });
  });

  it("posts a mapping correction when a multi-candidate choice changes", async () => {
    const user = userEvent.setup();

    render(<TenderMatrix projectId="project-1" comparisonId="comparison-1" />);

    const choice = await screen.findByLabelText("Mapping choice for Apex Homes Retaining walls");
    await user.selectOptions(choice, "03.01");

    await waitFor(() =>
      expect(api.resolveTenderQaItem).toHaveBeenCalledWith("mapping-1", {
        action: "correct",
        corrected_value: { cell_code: "03.01" },
        reason: "Inline matrix mapping override",
      }),
    );
  });
});

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
