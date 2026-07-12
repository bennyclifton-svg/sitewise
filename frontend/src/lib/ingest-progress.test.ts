import { describe, expect, it } from "vitest";

import { formatEtaSeconds, IngestBatchEstimator } from "@/lib/ingest-progress";

const MB = 1024 * 1024;

function makeEstimator(
  files: { id: string; sizeBytes: number }[],
): { estimator: IngestBatchEstimator; advance: (seconds: number) => void } {
  let nowMs = 0;
  const estimator = new IngestBatchEstimator(files, () => nowMs);
  return {
    estimator,
    advance: (seconds: number) => {
      nowMs += seconds * 1000;
    },
  };
}

describe("IngestBatchEstimator", () => {
  it("returns zero progress and no ETA for an empty batch", () => {
    const { estimator } = makeEstimator([]);
    expect(estimator.snapshot()).toEqual({ fraction: 0, etaSeconds: null });
  });

  it("starts a batch at zero progress with a positive ETA", () => {
    const { estimator } = makeEstimator([{ id: "a", sizeBytes: 2 * MB }]);
    const snapshot = estimator.snapshot();
    expect(snapshot.fraction).toBe(0);
    expect(snapshot.etaSeconds).toBeGreaterThan(0);
  });

  it("advances progress as upload bytes are reported", () => {
    const { estimator } = makeEstimator([{ id: "a", sizeBytes: 4 * MB }]);
    const before = estimator.snapshot().fraction;
    estimator.uploadProgress("a", 2 * MB);
    const during = estimator.snapshot().fraction;
    estimator.uploadProgress("a", 4 * MB);
    const after = estimator.snapshot().fraction;

    expect(during).toBeGreaterThan(before);
    expect(after).toBeGreaterThan(during);
    expect(after).toBeLessThan(1);
  });

  it("creeps forward during ingest but never reports done until the file finishes", () => {
    const { estimator, advance } = makeEstimator([{ id: "a", sizeBytes: 2 * MB }]);
    estimator.uploadProgress("a", 2 * MB);
    estimator.startIngest("a");
    const atStart = estimator.snapshot().fraction;

    advance(5);
    const midway = estimator.snapshot().fraction;
    expect(midway).toBeGreaterThan(atStart);

    // Even after far longer than any estimate, an unfinished file caps out.
    advance(3600);
    const stalled = estimator.snapshot();
    expect(stalled.fraction).toBeLessThan(1);
    expect(stalled.etaSeconds).toBeGreaterThanOrEqual(0);
  });

  it("reports completion once every file has finished", () => {
    const { estimator, advance } = makeEstimator([
      { id: "a", sizeBytes: MB },
      { id: "b", sizeBytes: MB },
    ]);
    for (const id of ["a", "b"]) {
      estimator.uploadProgress(id, MB);
      estimator.startIngest(id);
      advance(3);
      estimator.finishFile(id);
    }
    expect(estimator.snapshot()).toEqual({ fraction: 1, etaSeconds: 0 });
  });

  it("drops removed files from the batch", () => {
    const { estimator, advance } = makeEstimator([
      { id: "keep", sizeBytes: MB },
      { id: "divert", sizeBytes: 50 * MB },
    ]);
    estimator.removeFile("divert");
    estimator.uploadProgress("keep", MB);
    estimator.startIngest("keep");
    advance(2);
    estimator.finishFile("keep");
    expect(estimator.snapshot()).toEqual({ fraction: 1, etaSeconds: 0 });
  });

  it("never reports a lower fraction than it already reported", () => {
    const { estimator, advance } = makeEstimator([
      { id: "a", sizeBytes: 4 * MB },
      { id: "b", sizeBytes: 4 * MB },
    ]);
    const fractions: number[] = [];
    const record = () => fractions.push(estimator.snapshot().fraction);

    record();
    estimator.uploadProgress("a", 4 * MB);
    record();
    estimator.startIngest("a");
    advance(60); // slow ingest re-learns rates, shifting the weights
    record();
    estimator.finishFile("a");
    record();
    estimator.uploadProgress("b", MB);
    record();

    for (let i = 1; i < fractions.length; i += 1) {
      expect(fractions[i]).toBeGreaterThanOrEqual(fractions[i - 1]);
    }
  });

  it("learns from a slow first ingest when estimating the rest of the batch", () => {
    const { estimator, advance } = makeEstimator([
      { id: "a", sizeBytes: 5 * MB },
      { id: "b", sizeBytes: 5 * MB },
    ]);
    const seededEta = estimator.snapshot().etaSeconds ?? 0;

    estimator.uploadProgress("a", 5 * MB);
    estimator.startIngest("a");
    advance(60); // far slower than the seeded estimate
    estimator.finishFile("a");

    const learnedEta = estimator.snapshot().etaSeconds ?? 0;
    // Half the files are done, yet the remaining estimate should exceed what
    // the seeds predicted for the whole batch.
    expect(learnedEta).toBeGreaterThan(seededEta / 2);
    expect(learnedEta).toBeGreaterThan(20);
  });
});

describe("formatEtaSeconds", () => {
  it("returns null when there is no estimate", () => {
    expect(formatEtaSeconds(null)).toBeNull();
  });

  it("describes very short waits without a number", () => {
    expect(formatEtaSeconds(3)).toBe("a few seconds left");
  });

  it("rounds sub-90-second waits to five seconds", () => {
    expect(formatEtaSeconds(42)).toBe("~40s left");
  });

  it("switches to minutes for long waits", () => {
    expect(formatEtaSeconds(130)).toBe("~2 min left");
  });
});
