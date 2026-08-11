import { describe, expect, it, vi } from "vitest";

import {
  runOptimisticMutation,
  type OptimisticConflict,
  type RebaseResult,
} from "@/lib/optimistic-mutation";

describe("runOptimisticMutation", () => {
  it("applies immediately and then confirms", async () => {
    const apply = vi.fn();
    await runOptimisticMutation({
      snapshot: { version: 1, value: "old" },
      optimistic: { version: 1, value: "new" },
      apply,
      commit: async () => ({ version: 2, value: "server" }),
      confirmed: (value) => value,
    });
    expect(apply.mock.calls).toEqual([
      [{ version: 1, value: "new" }],
      [{ version: 2, value: "server" }],
    ]);
  });

  it("reloads, rebases, and retries once on a safe conflict", async () => {
    const apply = vi.fn();
    const conflict = Object.assign(new Error("conflict"), { status: 409 });
    let attempts = 0;
    const result = await runOptimisticMutation({
      snapshot: { version: 1, value: "old" },
      optimistic: { version: 1, value: "mine" },
      apply,
      commit: async (base) => {
        attempts += 1;
        if (attempts === 1) {
          expect(base).toEqual({ version: 1, value: "old" });
          throw conflict;
        }
        expect(base).toEqual({ version: 2, value: "mine" });
        return { version: 3, value: "mine" };
      },
      confirmed: (value) => value,
      reload: async () => ({ version: 2, value: "theirs" }),
      rebase: ({ pending, latest }): RebaseResult<{ version: number; value: string }> => ({
        status: "safe",
        state: { version: latest.version, value: pending.value },
      }),
    });
    expect(result).toEqual({ version: 3, value: "mine" });
    expect(attempts).toBe(2);
    expect(apply.mock.calls).toEqual([
      [{ version: 1, value: "mine" }],
      [{ version: 2, value: "mine" }],
      [{ version: 3, value: "mine" }],
    ]);
  });

  it("preserves the pending edit and reports unresolved conflict when rebase is unsafe", async () => {
    const apply = vi.fn();
    const onUnresolvedConflict = vi.fn();
    const conflict = Object.assign(new Error("conflict"), { status: 409 });
    await expect(
      runOptimisticMutation({
        snapshot: { version: 1, value: "old" },
        optimistic: { version: 1, value: "mine" },
        apply,
        commit: async () => {
          throw conflict;
        },
        confirmed: (value) => value,
        reload: async () => ({ version: 2, value: "theirs" }),
        rebase: (): RebaseResult<{ version: number; value: string }> => ({
          status: "unsafe",
        }),
        onUnresolvedConflict,
      }),
    ).rejects.toThrow("conflict");
    expect(apply.mock.calls).toEqual([
      [{ version: 1, value: "mine" }],
      [{ version: 1, value: "mine" }],
    ]);
    expect(onUnresolvedConflict).toHaveBeenCalledWith({
      latest: { version: 2, value: "theirs" },
      pending: { version: 1, value: "mine" },
    } satisfies OptimisticConflict<{ version: number; value: string }>);
  });

  it("does not retry a second conflict after one bounded rebase attempt", async () => {
    const apply = vi.fn();
    const onUnresolvedConflict = vi.fn();
    const conflict = Object.assign(new Error("conflict"), { status: 409 });
    let attempts = 0;
    await expect(
      runOptimisticMutation({
        snapshot: { version: 1, value: "old" },
        optimistic: { version: 1, value: "mine" },
        apply,
        commit: async () => {
          attempts += 1;
          throw conflict;
        },
        confirmed: (value) => value,
        reload: async () => ({ version: attempts + 1, value: "theirs" }),
        rebase: ({ pending, latest }) => ({
          status: "safe" as const,
          state: { version: latest.version, value: pending.value },
        }),
        onUnresolvedConflict,
      }),
    ).rejects.toThrow("conflict");
    expect(attempts).toBe(2);
    expect(onUnresolvedConflict).toHaveBeenCalledTimes(1);
    expect(apply.mock.calls.at(-1)?.[0]).toEqual({ version: 2, value: "mine" });
  });

  it("rolls back to the snapshot when a non-conflict error occurs", async () => {
    const apply = vi.fn();
    await expect(
      runOptimisticMutation({
        snapshot: "old",
        optimistic: "new",
        apply,
        commit: async () => {
          throw new Error("network");
        },
        confirmed: (value) => value,
      }),
    ).rejects.toThrow("network");
    expect(apply.mock.calls).toEqual([["new"], ["old"]]);
  });
});
