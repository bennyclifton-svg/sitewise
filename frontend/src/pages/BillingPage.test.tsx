import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { BillingPage } from "@/pages/BillingPage";
import { api } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  api: {
    createBillingCheckout: vi.fn(),
    getBillingPlans: vi.fn(),
    getBillingStatus: vi.fn(),
    openBillingPortal: vi.fn(),
  },
}));

describe("BillingPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the agent quota warning", async () => {
    vi.mocked(api.getBillingPlans).mockResolvedValue({
      billing_provider: "stripe",
      billing_enabled: true,
      polar_enabled: false,
      environment: "stripe",
      plans: [
        {
          id: "starter",
          name: "Starter",
          description: "Starter plan",
          price_monthly: 49,
          configured: true,
        },
      ],
    });
    vi.mocked(api.getBillingStatus).mockResolvedValue({
      billing_provider: "stripe",
      billing_enabled: true,
      polar_enabled: false,
      environment: "stripe",
      current_plan_id: "starter",
      subscription_status: "active",
      read_only: false,
      has_customer: true,
      has_polar_customer: false,
      quota: {
        used_turns: 80,
        quota: 100,
        percent: 80,
        warning: true,
      },
    });

    render(
      <MemoryRouter>
        <BillingPage />
      </MemoryRouter>,
    );

    expect(await screen.findByText(/Agent usage/i)).toBeInTheDocument();
    expect(screen.getByText(/80 of 100 turns/i)).toBeInTheDocument();
    expect(screen.getByText(/80%/)).toBeInTheDocument();
    expect(screen.getByText(/You are near this month's agent quota/i)).toBeInTheDocument();
  });
});
