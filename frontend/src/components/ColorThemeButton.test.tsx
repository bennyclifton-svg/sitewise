import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { ColorThemeButton } from "@/components/ColorThemeButton";
import { THEME_STORAGE_KEY } from "@/lib/theme";

describe("ColorThemeButton", () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
    document.documentElement.style.colorScheme = "";
  });

  it("changes to light mode from its dedicated control", async () => {
    const user = userEvent.setup();
    render(<ColorThemeButton />);

    await user.click(screen.getByRole("button", { name: "Light" }));

    expect(document.documentElement.dataset.theme).toBe("light");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("light");
    expect(screen.getByRole("button", { name: "Dark" })).toBeInTheDocument();
  });
});
