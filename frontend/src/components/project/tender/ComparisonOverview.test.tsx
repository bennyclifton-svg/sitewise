import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ComparisonOverview } from "@/components/project/tender/ComparisonOverview";
import { api } from "@/lib/api";
import type {
  TenderComparison,
  TenderComparisonProgress,
} from "@/lib/types/tender";

vi.mock("@/lib/api", () => ({
  api: {
    getTenderComparison: vi.fn(),
    getTenderComparisonProgress: vi.fn(),
    processTenderComparison: vi.fn(),
  },
}));

describe("ComparisonOverview", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders repository-selected comparisons with missing context", async () => {
    vi.mocked(api.getTenderComparison).mockResolvedValue(repositoryComparison);
    vi.mocked(api.getTenderComparisonProgress).mockResolvedValue(idleProgress);

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

  it("shows the progress gates and a single process button when idle", async () => {
    vi.mocked(api.getTenderComparison).mockResolvedValue(repositoryComparison);
    vi.mocked(api.getTenderComparisonProgress).mockResolvedValue(idleProgress);

    render(
      <MemoryRouter>
        <ComparisonOverview projectId="project-1" comparisonId="comparison-1" />
      </MemoryRouter>,
    );

    await waitFor(() =>
      expect(screen.getByRole("button", { name: /process quotes/i })).toBeInTheDocument(),
    );
    expect(screen.getByText("Read documents")).toBeInTheDocument();
    expect(screen.getByText("Analyse & compare")).toBeInTheDocument();
    expect(screen.getByText("Map to cost categories")).toBeInTheDocument();
  });

  it("shows QA attention state with pending count and no process button when done", async () => {
    vi.mocked(api.getTenderComparison).mockResolvedValue(repositoryComparison);
    vi.mocked(api.getTenderComparisonProgress).mockResolvedValue(qaProgress);

    render(
      <MemoryRouter>
        <ComparisonOverview projectId="project-1" comparisonId="comparison-1" />
      </MemoryRouter>,
    );

    await waitFor(() =>
      expect(
        screen.getByText(/103 findings need your review/i),
      ).toBeInTheDocument(),
    );
    expect(
      screen.queryByRole("button", { name: /process quotes/i }),
    ).not.toBeInTheDocument();
  });

  it("surfaces unreadable documents on the quote row", async () => {
    vi.mocked(api.getTenderComparison).mockResolvedValue(repositoryComparison);
    vi.mocked(api.getTenderComparisonProgress).mockResolvedValue(failedIngestProgress);

    render(
      <MemoryRouter>
        <ComparisonOverview projectId="project-1" comparisonId="comparison-1" />
      </MemoryRouter>,
    );

    await waitFor(() =>
      expect(
        screen.getByText(/quote-a\.md - Unsupported Format/i),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByRole("button", { name: /retry processing/i }),
    ).toBeInTheDocument();
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

const baseMilestones: TenderComparisonProgress["milestones"] = [
  { key: "ingest", label: "Read documents", state: "pending", detail: null },
  { key: "extract", label: "Extract line items", state: "pending", detail: null },
  { key: "map", label: "Map to cost categories", state: "pending", detail: null },
  { key: "analyse", label: "Analyse & compare", state: "pending", detail: null },
  { key: "review", label: "Review findings", state: "pending", detail: null },
  { key: "report", label: "Report", state: "pending", detail: null },
];

const idleProgress: TenderComparisonProgress = {
  comparison_id: "comparison-1",
  status: "intake",
  percent: 0,
  is_processing: false,
  qa_pending: 0,
  milestones: baseMilestones,
  quotes: [
    {
      quote_id: "quote-1",
      builder_name: "Quote 1",
      stage: "intake",
      stated_total_cents: 120_000_00,
      documents: [{ filename: "quote-a.pdf", ingest_status: "pending" }],
    },
  ],
};

const qaProgress: TenderComparisonProgress = {
  ...idleProgress,
  status: "qa",
  percent: 75,
  qa_pending: 103,
  milestones: baseMilestones.map((milestone) =>
    milestone.key === "review"
      ? { ...milestone, state: "attention", detail: "103 items need your review" }
      : milestone.key === "report"
        ? milestone
        : { ...milestone, state: "done" },
  ),
};

const failedIngestProgress: TenderComparisonProgress = {
  ...idleProgress,
  milestones: baseMilestones.map((milestone) =>
    milestone.key === "ingest"
      ? {
          ...milestone,
          state: "failed",
          detail: "Cannot read: quote-a.md. Attach PDF or DOCX versions.",
        }
      : milestone,
  ),
  quotes: [
    {
      quote_id: "quote-1",
      builder_name: "Quote 1",
      stage: "intake",
      stated_total_cents: null,
      documents: [{ filename: "quote-a.md", ingest_status: "unsupported_format" }],
    },
  ],
};
