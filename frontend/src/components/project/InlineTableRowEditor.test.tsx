import { render, screen } from "@testing-library/react";
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
});
