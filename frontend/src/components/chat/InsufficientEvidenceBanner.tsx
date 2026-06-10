export function InsufficientEvidenceBanner() {
  return (
    <div className="rounded-md border border-amber-300/60 bg-amber-50 px-3 py-2 text-sm text-amber-950 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-100">
      <p className="font-medium">Limited corpus match</p>
      <p className="mt-1 text-pretty">
        Clerk could not find enough indexed evidence for a fully grounded answer. Any
        citations below are the closest matches — treat unsupported claims as
        assumptions.
      </p>
    </div>
  );
}
