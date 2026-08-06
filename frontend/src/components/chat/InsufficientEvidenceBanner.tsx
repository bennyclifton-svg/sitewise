export function InsufficientEvidenceBanner() {
  return (
    <div className="border border-[color-mix(in_oklch,var(--sw-caution)_40%,transparent)] bg-[color-mix(in_oklch,var(--sw-caution)_14%,transparent)] px-3 py-2 text-sm text-[var(--sw-caution)]">
      <p className="font-medium">Limited corpus match</p>
      <p className="mt-1 text-pretty text-[var(--sw-text-secondary)]">
        Pi could not find enough indexed evidence for a fully grounded answer. Any
        citations below are the closest matches — treat unsupported claims as
        assumptions.
      </p>
    </div>
  );
}
