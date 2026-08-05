import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LlmModelSelector } from "@/components/LlmModelSelector";
import { api } from "@/lib/api";
import { getSelectedAgentModel } from "@/lib/agent-model";

vi.mock("@/lib/api", () => ({
  api: {
    getAgentModels: vi.fn(),
    getLlmModels: vi.fn(),
    getAgentConfiguration: vi.fn(),
  },
}));

describe("LlmModelSelector", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.clearAllMocks();
    vi.mocked(api.getAgentConfiguration).mockImplementation(async () => ({
      agent: await api.getAgentModels(),
      legacy: await api.getLlmModels(),
    }));
    vi.mocked(api.getLlmModels).mockResolvedValue({
      default_model: "gpt-5.6-terra",
      models: [],
    });
  });

  it("uses Pi model options when the agent runtime is enabled", async () => {
    vi.mocked(api.getAgentModels).mockResolvedValue({
      agent_runtime_enabled: true,
      default_model: "openai:gpt-5.6-terra",
      models: [
        {
          id: "openai:gpt-5.6-luna",
          label: "Fast",
          is_default: false,
          provider: "openai",
          model: "gpt-5.6-luna",
        },
        {
          id: "openai:gpt-5.6-terra",
          label: "Balanced",
          is_default: true,
          provider: "openai",
          model: "gpt-5.6-terra",
        },
        {
          id: "openai:gpt-5.6-sol",
          label: "Complex",
          is_default: false,
          provider: "openai",
          model: "gpt-5.6-sol",
        },
      ],
    });

    renderSelector();

    const select = screen.getByLabelText(/model tier/i);
    await waitFor(() => {
      expect(select).toHaveValue("openai:gpt-5.6-terra");
    });
    expect(screen.getByRole("option", { name: "Balanced" })).toHaveValue(
      "openai:gpt-5.6-terra",
    );
    expect(screen.getByRole("option", { name: "Fast" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Complex" })).toBeInTheDocument();

    await userEvent.selectOptions(select, "openai:gpt-5.6-sol");

    expect(getSelectedAgentModel()).toBe("openai:gpt-5.6-sol");
    await waitFor(() => expect(api.getAgentConfiguration).toHaveBeenCalledTimes(1));
  });

});

function renderSelector() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <LlmModelSelector />
    </QueryClientProvider>,
  );
}
