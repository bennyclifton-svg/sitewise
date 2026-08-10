export type OptimisticMutationOptions<TState, TResult> = {
  snapshot: TState;
  optimistic: TState;
  apply: (state: TState) => void;
  commit: () => Promise<TResult>;
  confirmed: (result: TResult) => TState;
  onConflict?: () => Promise<TState>;
};

/** Shared immediate-update contract for versioned UI mutations. */
export async function runOptimisticMutation<TState, TResult>(
  options: OptimisticMutationOptions<TState, TResult>,
): Promise<TResult> {
  options.apply(options.optimistic);
  try {
    const result = await options.commit();
    options.apply(options.confirmed(result));
    return result;
  } catch (error) {
    if (isConflict(error) && options.onConflict) {
      options.apply(await options.onConflict());
    } else {
      options.apply(options.snapshot);
    }
    throw error;
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
