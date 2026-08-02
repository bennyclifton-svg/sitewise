import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LlmModelSelector } from "@/components/LlmModelSelector";
import { api } from "@/lib/api";
import { getSelectedAgentModel } from "@/lib/agent-model";
import { PI_RUNTIME_ID } from "@/lib/agent-runtime";

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

  it("uses Hermes model options when the agent runtime is enabled", async () => {
    vi.mocked(api.getAgentModels).mockResolvedValue({
      agent_runtime_enabled: true,
      default_model: "__hermes_config__",
      default_runtime: "hermes",
      runtimes: [
        { id: "hermes", label: "Hermes", enabled: true },
        { id: "pi", label: "Pi", enabled: false },
      ],
      models: [
        {
          id: "__hermes_config__",
          label: "Hermes default",
          is_default: true,
          provider: null,
          model: null,
        },
        {
          id: "openai:gpt-5.6-sol",
          label: "GPT-5.6 Sol (complex)",
          is_default: false,
          provider: "openai",
          model: "gpt-5.6-sol",
        },
      ],
    });

    renderSelector();

    const select = await screen.findByLabelText(/hermes model/i);
    expect(select).toHaveValue("__hermes_config__");
    expect(screen.getByRole("option", { name: "GPT-5.6 Sol (complex)" })).toBeInTheDocument();

    await userEvent.selectOptions(select, "openai:gpt-5.6-sol");

    expect(getSelectedAgentModel()).toBe("openai:gpt-5.6-sol");
    await waitFor(() => expect(api.getAgentConfiguration).toHaveBeenCalledTimes(1));
  });

  it("allows selecting a Pi model when Pi is selected", async () => {
    window.localStorage.setItem("clerk.agentRuntime", "pi");
    vi.mocked(api.getAgentModels).mockResolvedValue({
      agent_runtime_enabled: true,
      default_model: "__hermes_config__",
      default_runtime: "hermes",
      runtimes: [
        {
          id: "hermes",
          label: "Hermes",
          enabled: true,
          model: "gpt-5.6-terra",
          model_label: "gpt-5.6-terra (openai)",
        },
        {
          id: "pi",
          label: "Pi",
          enabled: true,
          model: "gpt-5.6-terra",
          model_label: "gpt-5.6-terra (openai)",
          default_model: "openai:gpt-5.6-terra",
          model_options: [
            {
              id: "openai:gpt-5.6-sol",
              label: "GPT-5.6 Sol (complex)",
              is_default: false,
              provider: "openai",
              model: "gpt-5.6-sol",
            },
            {
              id: "openai:gpt-5.6-terra",
              label: "GPT-5.6 Terra (balanced)",
              is_default: true,
              provider: "openai",
              model: "gpt-5.6-terra",
            },
            {
              id: "openai:gpt-5.6-luna",
              label: "GPT-5.6 Luna (fast)",
              is_default: false,
              provider: "openai",
              model: "gpt-5.6-luna",
            },
          ],
        },
      ],
      models: [
        {
          id: "__hermes_config__",
          label: "Hermes default",
          is_default: true,
          provider: null,
          model: null,
        },
        {
          id: "openai:gpt-5.6-sol",
          label: "GPT-5.6 Sol (complex)",
          is_default: false,
          provider: "openai",
          model: "gpt-5.6-sol",
        },
      ],
    });

    renderSelector();

    const select = await screen.findByLabelText(/pi model/i);
    expect(select).toHaveValue("openai:gpt-5.6-terra");
    expect(screen.getByRole("option", { name: "GPT-5.6 Sol (complex)" })).toBeInTheDocument();

    await userEvent.selectOptions(select, "openai:gpt-5.6-sol");

    expect(getSelectedAgentModel(PI_RUNTIME_ID)).toBe("openai:gpt-5.6-sol");
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
