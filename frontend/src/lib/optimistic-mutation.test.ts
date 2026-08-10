import { describe, expect, it, vi } from "vitest";

import { runOptimisticMutation } from "@/lib/optimistic-mutation";

describe("runOptimisticMutation", () => {
  it("applies immediately and then confirms", async () => {
    const apply = vi.fn();
    await runOptimisticMutation({
      snapshot: "old",
      optimistic: "new",
      apply,
      commit: async () => "server",
      confirmed: (value) => value,
    });
    expect(apply.mock.calls).toEqual([["new"], ["server"]]);
  });

  it("reloads current state after a conflict", async () => {
    const apply = vi.fn();
    const conflict = Object.assign(new Error("conflict"), { status: 409 });
    await expect(
      runOptimisticMutation({
        snapshot: "old",
        optimistic: "new",
        apply,
        commit: async () => {
          throw conflict;
        },
        confirmed: (value) => value,
        onConflict: async () => "latest",
      }),
    ).rejects.toThrow("conflict");
    expect(apply.mock.calls).toEqual([["new"], ["latest"]]);
  });
});
