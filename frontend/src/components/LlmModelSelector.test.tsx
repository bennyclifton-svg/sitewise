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
});
