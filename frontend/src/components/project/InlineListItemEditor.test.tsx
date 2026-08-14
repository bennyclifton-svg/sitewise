import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { InlineListItemEditor } from "@/components/project/InlineListItemEditor";

describe("InlineListItemEditor", () => {
  it("preserves the list marker and uses the latest save callback", async () => {
    const firstSave = vi.fn().mockResolvedValue(undefined);
    const latestSave = vi.fn().mockResolvedValue(undefined);
    const onCancel = vi.fn();
    const editor = (onSave: (markdown: string) => Promise<void>) => (
      <InlineListItemEditor
        sourceItem="- Original"
        sourceStart={0}
        sourceEnd={10}
        isSaving={false}
        onCancel={onCancel}
        onSave={onSave}
      >
        Original
      </InlineListItemEditor>
    );

    const view = render(editor(firstSave));
    const textbox = screen.getByRole("textbox", { name: "Edit list item" });
    textbox.textContent = "Updated";
    fireEvent.input(textbox);

    view.rerender(editor(latestSave));
    fireEvent.blur(textbox);

    await waitFor(() => expect(latestSave).toHaveBeenCalledWith("- Updated"));
    expect(firstSave).not.toHaveBeenCalled();
  });
});
