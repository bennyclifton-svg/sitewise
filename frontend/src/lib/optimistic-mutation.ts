export type RebaseResult<TState> =
  | { status: "safe"; state: TState }
  | { status: "unsafe" };

export type OptimisticConflict<TState> = {
  latest: TState;
  pending: TState;
};

export type OptimisticMutationOptions<TState, TResult> = {
  snapshot: TState;
  optimistic: TState;
  apply: (state: TState) => void;
  /** Receives the revision base for the attempt; first call uses `snapshot`. */
  commit: (base: TState) => Promise<TResult>;
  confirmed: (result: TResult) => TState;
  reload?: () => Promise<TState>;
  rebase?: (args: {
    snapshot: TState;
    pending: TState;
    latest: TState;
  }) => RebaseResult<TState>;
  onUnresolvedConflict?: (conflict: OptimisticConflict<TState>) => void;
};

/** Shared immediate-update contract for versioned UI mutations. */
export async function runOptimisticMutation<TState, TResult>(
  options: OptimisticMutationOptions<TState, TResult>,
): Promise<TResult> {
  options.apply(options.optimistic);

  let base = options.snapshot;
  let pending = options.optimistic;
  let retried = false;

  while (true) {
    try {
      const result = await options.commit(base);
      options.apply(options.confirmed(result));
      return result;
    } catch (error) {
      if (!isConflict(error)) {
        options.apply(options.snapshot);
        throw error;
      }

      if (!options.reload) {
        options.apply(options.snapshot);
        throw error;
      }

      const latest = await options.reload();
      if (!retried && options.rebase) {
        const rebased = options.rebase({
          snapshot: options.snapshot,
          pending,
          latest,
        });
        if (rebased.status === "safe") {
          options.apply(rebased.state);
          base = rebased.state;
          pending = rebased.state;
          retried = true;
          continue;
        }
      }

      // Unsafe rebase, missing rebase, or second conflict: keep the user's edit.
      options.apply(pending);
      options.onUnresolvedConflict?.({ latest, pending });
      throw error;
    }
  }
}

function isConflict(error: unknown): boolean {
  return (
    typeof error === "object" &&
    error !== null &&
    "status" in error &&
    error.status === 409
  );
}
