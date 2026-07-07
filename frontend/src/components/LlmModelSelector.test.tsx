import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LlmModelSelector } from "@/components/LlmModelSelector";
import { api } from "@/lib/api";
import { getSelectedAgentModel } from "@/lib/agent-model";

vi.mock("@/lib/api", () => ({
  api: {
    getAgentModels: vi.fn(),
    getLlmModels: vi.fn(),
  },
}));

describe("LlmModelSelector", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.clearAllMocks();
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
          id: "openai-codex:gpt-5.5",
          label: "gpt-5.5 (Codex)",
          is_default: false,
          provider: "openai-codex",
          model: "gpt-5.5",
        },
      ],
    });

    render(<LlmModelSelector />);

    const select = await screen.findByLabelText(/hermes model/i);
    expect(select).toHaveValue("__hermes_config__");
    expect(screen.getByRole("option", { name: "gpt-5.5 (Codex)" })).toBeInTheDocument();

    await userEvent.selectOptions(select, "openai-codex:gpt-5.5");

    expect(getSelectedAgentModel()).toBe("openai-codex:gpt-5.5");
    await waitFor(() => expect(api.getLlmModels).not.toHaveBeenCalled());
  });

  it("shows Pi's configured model instead of Hermes options when Pi is selected", async () => {
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
          model: "gpt-5.1",
          model_label: "gpt-5.1 (openai-api)",
        },
        {
          id: "pi",
          label: "Pi",
          enabled: true,
          model: "gpt-5.1",
          model_label: "gpt-5.1 (openai)",
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
          id: "openai-codex:gpt-5.5",
          label: "gpt-5.5 (Codex)",
          is_default: false,
          provider: "openai-codex",
          model: "gpt-5.5",
        },
      ],
    });

    render(<LlmModelSelector />);

    const select = await screen.findByLabelText(/pi model/i);
    expect(select).toBeDisabled();
    expect(screen.getByRole("option", { name: "gpt-5.1 (openai)" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "gpt-5.5 (Codex)" })).not.toBeInTheDocument();
  });
});
