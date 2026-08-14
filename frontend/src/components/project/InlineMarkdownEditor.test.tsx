import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { InlineMarkdownEditor } from "@/components/project/InlineMarkdownEditor";

describe("InlineMarkdownEditor", () => {
  it("keeps typed text when the parent re-renders with different children", () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const onCancel = vi.fn();

    function Host({ lead }: { lead: string }) {
      return (
        <InlineMarkdownEditor
          sectionStart={0}
          sourceStart={0}
          sourceEnd={20}
          isChanged={false}
          isSaving={false}
          onCancel={onCancel}
          onSave={onSave}
        >
          <strong>{lead}</strong> original wording
        </InlineMarkdownEditor>
      );
    }

    const view = render(<Host lead="Before" />);
    const editor = screen.getByRole("textbox", { name: "Edit selected text" });
    editor.textContent = "Stable typed sentence.";
    fireEvent.input(editor);

    view.rerender(<Host lead="After" />);

    expect(editor.textContent).toBe("Stable typed sentence.");
    expect(screen.queryByText(/original wording/)).not.toBeInTheDocument();
  });

  it("does not cancel an untouched editor as dirty on blur", () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const onCancel = vi.fn();

    render(
      <InlineMarkdownEditor
        sectionStart={0}
        sourceStart={0}
        sourceEnd={10}
        isChanged={false}
        isSaving={false}
        onCancel={onCancel}
        onSave={onSave}
      >
        Unchanged
      </InlineMarkdownEditor>,
    );

    fireEvent.blur(screen.getByRole("textbox", { name: "Edit selected text" }));
    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onSave).not.toHaveBeenCalled();
  });

  it("uses the latest save callback after its parent re-renders", async () => {
    const firstSave = vi.fn().mockResolvedValue(undefined);
    const latestSave = vi.fn().mockResolvedValue(undefined);
    const onCancel = vi.fn();
    const editor = (onSave: (markdown: string) => Promise<void>) => (
      <InlineMarkdownEditor
        sectionStart={0}
        sourceStart={0}
        sourceEnd={10}
        isChanged={false}
        isSaving={false}
        onCancel={onCancel}
        onSave={onSave}
      >
        Original
      </InlineMarkdownEditor>
    );

    const view = render(editor(firstSave));
    const textbox = screen.getByRole("textbox", { name: "Edit selected text" });
    textbox.textContent = "Updated";
    fireEvent.input(textbox);

    view.rerender(editor(latestSave));
    fireEvent.blur(textbox);

    await waitFor(() => expect(latestSave).toHaveBeenCalledWith("Updated"));
    expect(firstSave).not.toHaveBeenCalled();
  });
});
