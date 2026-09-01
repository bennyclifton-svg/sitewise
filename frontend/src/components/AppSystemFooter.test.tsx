import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AppSystemFooter } from "@/components/AppSystemFooter";

vi.mock("@/lib/supabase", () => ({
  supabase: {
    auth: {
      getUser: vi.fn().mockResolvedValue({
        data: { user: { email: "orlando@sitewise.au" } },
      }),
      onAuthStateChange: vi.fn().mockReturnValue({
        data: { subscription: { unsubscribe: vi.fn() } },
      }),
    },
  },
}));

function renderFooter() {
  return render(
    <MemoryRouter>
      <AppSystemFooter />
    </MemoryRouter>,
  );
}

describe("AppSystemFooter", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("keeps appearance controls out of the account menu", async () => {
    const user = userEvent.setup();
    renderFooter();

    await user.click(screen.getByRole("button", { name: "Account menu" }));
    expect(screen.queryByRole("menuitem", { name: /light|dark/i })).not.toBeInTheDocument();
  });
});
