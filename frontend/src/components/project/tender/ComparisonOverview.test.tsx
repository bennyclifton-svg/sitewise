import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ComparisonOverview } from "@/components/project/tender/ComparisonOverview";
import { api } from "@/lib/api";
import type { TenderComparison } from "@/lib/types/tender";

vi.mock("@/lib/api", () => ({
  api: {
    getTenderComparison: vi.fn(),
  },
}));

describe("ComparisonOverview", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders repository-selected comparisons with missing context", async () => {
    vi.mocked(api.getTenderComparison).mockResolvedValue(repositoryComparison);

    render(
      <MemoryRouter>
        <ComparisonOverview projectId="project-1" comparisonId="comparison-1" />
      </MemoryRouter>,
    );

    await waitFor(() => expectMetric("State", "Not stated"));
    expectMetric("Region", "Not stated");
    expectMetric("Build", "Not stated");
    expectMetric("Spec", "Not stated");
    expectMetric("Storeys", "Not stated");
  });
});

function expectMetric(label: string, value: string) {
  expect(screen.getByText(label).nextElementSibling).toHaveTextContent(value);
}

const repositoryComparison: TenderComparison = {
  id: "comparison-1",
  project_id: "project-1",
  status: "processing",
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
      builder_name: "Quote 1",
      builder_abn: null,
      quote_ref: null,
      quote_date: null,
      stated_total_cents: 120_000_00,
      gst_treatment: "unclear",
      contract_type: "unknown",
      validity_days: null,
      stage: "ingest_document",
      created_at: "2026-07-08T00:00:00Z",
      documents: [],
    },
  ],
};
