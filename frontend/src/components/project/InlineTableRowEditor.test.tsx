import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { InlineTableRowEditor } from "@/components/project/InlineTableRowEditor";

describe("InlineTableRowEditor", () => {
  it("keeps the opening row cells when its parent re-renders", () => {
    const editor = (sourceRow: string) => (
      <table>
        <tbody>
          <InlineTableRowEditor
            sourceRow={sourceRow}
            sourceStart={0}
            sourceEnd={sourceRow.length}
            isSaving={false}
            focusCellIndex={1}
            onCancel={vi.fn()}
            onSave={vi.fn().mockResolvedValue(undefined)}
          />
        </tbody>
      </table>
    );

    const view = render(editor("| Alpha | Beta |"));
    expect(screen.getAllByRole("textbox").map((cell) => cell.textContent)).toEqual([
      "Alpha",
      "Beta",
    ]);
    expect(document.activeElement).toBe(screen.getAllByRole("textbox")[1]);

    view.rerender(editor("| Changed | Values |"));

    expect(screen.getAllByRole("textbox").map((cell) => cell.textContent)).toEqual([
      "Alpha",
      "Beta",
    ]);
  });

  it("keeps what the user typed when the parent re-renders", () => {
    const editor = (isSaving: boolean) => (
      <table>
        <tbody>
          <InlineTableRowEditor
            sourceRow="| Alpha | Beta |"
            sourceStart={0}
            sourceEnd={16}
            isSaving={isSaving}
            onCancel={vi.fn()}
            onSave={vi.fn().mockResolvedValue(undefined)}
          />
        </tbody>
      </table>
    );

    const view = render(editor(false));
    const cell = screen.getAllByRole("textbox")[1];
    cell.textContent = "Gamma";
    fireEvent.input(cell);

    // Any parent re-render used to re-apply the row's *original* text through
    // dangerouslySetInnerHTML, silently discarding in-flight keystrokes.
    view.rerender(editor(true));

    expect(screen.getAllByRole("textbox").map((c) => c.textContent)).toEqual([
      "Alpha",
      "Gamma",
    ]);
  });

  it("stays editable while a save is in flight", () => {
    render(
      <table>
        <tbody>
          <InlineTableRowEditor
            sourceRow="| Alpha | Beta |"
            sourceStart={0}
            sourceEnd={16}
            isSaving
            onCancel={vi.fn()}
            onSave={vi.fn().mockResolvedValue(undefined)}
          />
        </tbody>
      </table>,
    );

    const cells = screen.getAllByRole("textbox");
    expect(cells).toHaveLength(2);
    for (const cell of cells) {
      // Plan §7: one in-flight save must not stop the user typing in another
      // cell. contentEditable="false" here silently swallowed keystrokes.
      expect(cell).toHaveAttribute("contenteditable", "true");
      expect(cell).toHaveAttribute("aria-busy", "true");
    }
  });

  it("flushes an edit made during a save instead of dropping it", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const editor = (isSaving: boolean) => (
      <table>
        <tbody>
          <InlineTableRowEditor
            sourceRow="| Alpha | Beta |"
            sourceStart={0}
            sourceEnd={16}
            isSaving={isSaving}
            onCancel={vi.fn()}
            onSave={onSave}
          />
        </tbody>
      </table>
    );

    const view = render(editor(true));
    const cell = screen.getAllByRole("textbox")[1];

    // The user keeps typing while the parent commit is still in flight.
    cell.textContent = "Gamma";
    fireEvent.input(cell);
    fireEvent.keyDown(cell, { key: "Enter" });

    // Plan §8: the edit must not vanish just because a save was running.
    expect(onSave).not.toHaveBeenCalled();

    view.rerender(editor(false));

    await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
    expect(onSave).toHaveBeenCalledWith("| Alpha | Gamma |");
  });

  it("does not save or cancel when the editor unmounts mid-keystroke", () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const onCancel = vi.fn();
    const { unmount } = render(
      <table>
        <tbody>
          <InlineTableRowEditor
            sourceRow="| Surveyor | $4,200 |"
            sourceStart={0}
            sourceEnd={22}
            isSaving={false}
            focusCellIndex={1}
            onCancel={onCancel}
            onSave={onSave}
          />
        </tbody>
      </table>,
    );

    const feeCell = screen.getAllByRole("textbox")[1];
    feeCell.textContent = "8500";
    fireEvent.input(feeCell);

    // A remount used to fire blur on the dying row, which saved empty/partial
    // cells and made the fee jump to blank or zero.
    unmount();

    expect(onSave).not.toHaveBeenCalled();
    expect(onCancel).not.toHaveBeenCalled();
  });
});
