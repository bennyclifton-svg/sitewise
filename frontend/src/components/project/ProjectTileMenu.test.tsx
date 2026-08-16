import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ProjectTileMenu } from "@/components/project/ProjectTileMenu";

describe("ProjectTileMenu", () => {
  it("opens actions and calls delete", async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();

    render(<ProjectTileMenu title="New Town Extension" onDelete={onDelete} />);

    await user.click(screen.getByRole("button", { name: "Actions for New Town Extension" }));
    await user.click(screen.getByRole("menuitem", { name: "Delete" }));

    expect(onDelete).toHaveBeenCalledTimes(1);
  });

  it("offers rename when a handler is provided", async () => {
    const user = userEvent.setup();
    const onRename = vi.fn();

    render(
      <ProjectTileMenu
        title="New Town Extension"
        onRename={onRename}
        onDelete={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Actions for New Town Extension" }));
    await user.click(screen.getByRole("menuitem", { name: "Rename" }));

    expect(onRename).toHaveBeenCalledTimes(1);
  });
});
