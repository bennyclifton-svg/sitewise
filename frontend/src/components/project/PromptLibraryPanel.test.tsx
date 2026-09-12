import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { PromptLibraryPanel } from "@/components/project/PromptLibraryPanel";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import { STARTER_PROMPTS, type PromptLibrary } from "@/lib/prompt-library";

vi.mock("@/lib/api", () => ({ api: { get: vi.fn(), put: vi.fn() } }));
const writeText = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.get).mockResolvedValue({ version: 0, prompts: null });
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
  writeText.mockResolvedValue(undefined);
});

async function load() {
  const view = render(<PromptLibraryPanel />);
  await screen.findByRole("button", { name: "Project management plan" });
  return view;
}

describe("personal prompts", () => {
  it("lists ten topics in test order, expands their text, and copies it", async () => {
    await load();
    expect(screen.getAllByRole("button", { expanded: false }).map((button) => button.textContent)).toEqual(STARTER_PROMPTS.map((prompt) => prompt.title));
    expect(screen.getByText(STARTER_PROMPTS[0].text)).not.toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Project management plan" }));
    expect(screen.getByText(STARTER_PROMPTS[0].text)).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Copy Project management plan" }));
    await waitFor(() => expect(writeText).toHaveBeenCalledWith(STARTER_PROMPTS[0].text));
    expect(await screen.findByRole("status")).toHaveTextContent("Copied Project management plan");
  });

  it("persists an edit and loads the saved library on the next mount", async () => {
    const view = await load();
    let saved: PromptLibrary | undefined;
    vi.mocked(api.put).mockImplementation(async (_path, body) => {
      saved = { version: 1, prompts: (body as { prompts: typeof STARTER_PROMPTS }).prompts };
      return saved;
    });
    fireEvent.click(screen.getByRole("button", { name: "Edit Cost plan" }));
    fireEvent.change(screen.getByLabelText("Topic"), { target: { value: "Budget review" } });
    fireEvent.change(screen.getByLabelText("Prompt"), { target: { value: "Review all allowances." } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await screen.findByText("Saved to your personal library.");
    expect(api.put).toHaveBeenCalledWith("/prompt-library", expect.objectContaining({ expected_version: 0 }));
    view.unmount();
    vi.mocked(api.get).mockResolvedValue(saved);
    render(<PromptLibraryPanel />);
    expect(await screen.findByRole("button", { name: "Budget review" })).toBeVisible();
  });

  it("creates a prompt and cancels without writing", async () => {
    await load();
    fireEvent.click(screen.getByRole("button", { name: "New prompt" }));
    fireEvent.change(screen.getByLabelText("Topic"), { target: { value: "Weekly review" } });
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(api.put).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "New prompt" }));
    fireEvent.change(screen.getByLabelText("Topic"), { target: { value: "Weekly review" } });
    fireEvent.change(screen.getByLabelText("Prompt"), { target: { value: "Review progress." } });
    vi.mocked(api.put).mockResolvedValue({ version: 1, prompts: STARTER_PROMPTS });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(api.put).toHaveBeenCalledWith("/prompt-library", expect.objectContaining({ prompts: expect.arrayContaining([expect.objectContaining({ title: "Weekly review", text: "Review progress." })]) })));
  });

  it("retains an unsaved edit after failure and merges it into a reloaded version", async () => {
    await load();
    fireEvent.click(screen.getByRole("button", { name: "Edit Cost plan" }));
    fireEvent.change(screen.getByLabelText("Prompt"), { target: { value: "My revised prompt" } });
    vi.mocked(api.put).mockRejectedValueOnce(new ApiError("Conflict", { kind: "http", status: 409 }));
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await screen.findByRole("alert");
    expect(screen.getByLabelText("Prompt")).toHaveValue("My revised prompt");
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
    vi.mocked(api.get).mockResolvedValue({ version: 4, prompts: [...STARTER_PROMPTS, { id: "other", title: "Other device", text: "Keep me" }] });
    fireEvent.click(screen.getByRole("button", { name: "Reload prompts" }));
    await screen.findByRole("button", { name: "Other device" });
    vi.mocked(api.put).mockResolvedValue({ version: 5, prompts: STARTER_PROMPTS });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(api.put).toHaveBeenLastCalledWith("/prompt-library", expect.objectContaining({ expected_version: 4, prompts: expect.arrayContaining([expect.objectContaining({ id: "other" }), expect.objectContaining({ text: "My revised prompt" })]) })));
  });

  it("does not reseed an intentionally empty library and reports copy failures", async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ version: 1, prompts: [] });
    const view = render(<PromptLibraryPanel />);
    expect(await screen.findByText(/No saved prompts/)).toBeVisible();
    view.unmount();
    await load();
    writeText.mockRejectedValueOnce(new Error("denied"));
    fireEvent.click(screen.getByRole("button", { name: "Copy Programme" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not copy");
  });

  it("requires confirmation before removing a prompt", async () => {
    await load();
    const confirm = vi.spyOn(window, "confirm").mockReturnValueOnce(false).mockReturnValueOnce(true);
    fireEvent.click(screen.getByRole("button", { name: "Delete Programme" }));
    expect(api.put).not.toHaveBeenCalled();
    vi.mocked(api.put).mockResolvedValue({ version: 1, prompts: STARTER_PROMPTS.filter((prompt) => prompt.id !== "programme") });
    fireEvent.click(screen.getByRole("button", { name: "Delete Programme" }));
    await waitFor(() => expect(screen.queryByRole("button", { name: "Programme" })).not.toBeInTheDocument());
    confirm.mockRestore();
  });
});
