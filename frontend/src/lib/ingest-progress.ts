/**
 * Time-budget model for an inbox upload batch.
 *
 * Every file costs an estimated number of seconds to upload (observable via
 * XHR byte progress) and to ingest server-side (not observable, so it creeps
 * forward against an estimate and caps out until the response lands). Rates
 * are seeded with rough defaults and re-learned from each completed file, so
 * the bar and ETA self-correct after the first document.
 */

const MB = 1024 * 1024;
const UPLOAD_BYTES_PER_SECOND_SEED = 1.5 * MB;
// Observed against the live pipeline: even tiny documents take ~20s to ingest
// (markdown conversion, classification, embedding), so the fixed overhead
// dominates. Better to over-promise and finish early than the reverse.
const INGEST_OVERHEAD_SECONDS = 12;
const INGEST_SECONDS_PER_MB_SEED = 1;
const INGEST_SECONDS_PER_MB_FLOOR = 0.05;
// An unfinished ingest never claims more than this share of its estimate…
const INGEST_CREEP_CAP = 0.95;
// …and an unfinished batch never fills the bar completely.
const ACTIVE_FRACTION_CAP = 0.98;
// Exponential moving average weight for newly observed rates.
const LEARN_WEIGHT = 0.5;
// Ignore upload timings too short to give a meaningful throughput sample.
const MIN_LEARNABLE_SECONDS = 0.2;

export type IngestBatchSnapshot = {
  /** Overall batch progress in [0, 1]; monotonic non-decreasing. */
  fraction: number;
  /** Estimated seconds of work remaining; null when the batch is empty. */
  etaSeconds: number | null;
};

type FileState = {
  sizeBytes: number;
  uploadedBytes: number;
  uploadStartMs: number | null;
  ingestStartMs: number | null;
  finished: boolean;
};

export class IngestBatchEstimator {
  private readonly files = new Map<string, FileState>();
  private readonly now: () => number;
  private uploadBytesPerSecond = UPLOAD_BYTES_PER_SECOND_SEED;
  private ingestSecondsPerMb = INGEST_SECONDS_PER_MB_SEED;
  private maxReportedFraction = 0;

  constructor(
    files: { id: string; sizeBytes: number }[],
    now: () => number = () => Date.now(),
  ) {
    this.now = now;
    for (const file of files) {
      this.files.set(file.id, {
        sizeBytes: Math.max(file.sizeBytes, 1),
        uploadedBytes: 0,
        uploadStartMs: null,
        ingestStartMs: null,
        finished: false,
      });
    }
  }

  uploadProgress(id: string, loadedBytes: number): void {
    const file = this.files.get(id);
    if (!file || file.finished) return;
    if (file.uploadStartMs === null) {
      file.uploadStartMs = this.now();
    }
    file.uploadedBytes = Math.min(Math.max(loadedBytes, file.uploadedBytes), file.sizeBytes);
  }

  startIngest(id: string): void {
    const file = this.files.get(id);
    if (!file || file.finished) return;
    if (file.uploadStartMs !== null) {
      const elapsed = (this.now() - file.uploadStartMs) / 1000;
      if (elapsed >= MIN_LEARNABLE_SECONDS) {
        this.uploadBytesPerSecond = ema(this.uploadBytesPerSecond, file.sizeBytes / elapsed);
      }
    }
    file.uploadedBytes = file.sizeBytes;
    file.ingestStartMs = this.now();
  }

  finishFile(id: string): void {
    const file = this.files.get(id);
    if (!file || file.finished) return;
    if (file.ingestStartMs !== null) {
      const duration = (this.now() - file.ingestStartMs) / 1000;
      const observedRate = Math.max(
        (duration - INGEST_OVERHEAD_SECONDS) / (file.sizeBytes / MB),
        INGEST_SECONDS_PER_MB_FLOOR,
      );
      this.ingestSecondsPerMb = ema(this.ingestSecondsPerMb, observedRate);
    }
    file.uploadedBytes = file.sizeBytes;
    file.finished = true;
  }

  /** Drop a file from the batch (e.g. diverted to a drawing-set proposal). */
  removeFile(id: string): void {
    this.files.delete(id);
  }

  snapshot(): IngestBatchSnapshot {
    if (this.files.size === 0) {
      return { fraction: 0, etaSeconds: null };
    }

    let totalSeconds = 0;
    let doneSeconds = 0;
    let allFinished = true;

    for (const file of this.files.values()) {
      const uploadCost = file.sizeBytes / this.uploadBytesPerSecond;
      const ingestCost =
        INGEST_OVERHEAD_SECONDS + (file.sizeBytes / MB) * this.ingestSecondsPerMb;
      totalSeconds += uploadCost + ingestCost;

      if (file.finished) {
        doneSeconds += uploadCost + ingestCost;
        continue;
      }

      allFinished = false;
      doneSeconds += (file.uploadedBytes / file.sizeBytes) * uploadCost;
      if (file.ingestStartMs !== null) {
        const elapsed = (this.now() - file.ingestStartMs) / 1000;
        doneSeconds += Math.min(elapsed, ingestCost * INGEST_CREEP_CAP);
      }
    }

    if (allFinished) {
      this.maxReportedFraction = 1;
      return { fraction: 1, etaSeconds: 0 };
    }

    const fraction = Math.max(
      Math.min(doneSeconds / totalSeconds, ACTIVE_FRACTION_CAP),
      this.maxReportedFraction,
    );
    this.maxReportedFraction = fraction;
    return { fraction, etaSeconds: Math.max(totalSeconds - doneSeconds, 0) };
  }
}

function ema(current: number, observed: number): number {
  return current * (1 - LEARN_WEIGHT) + observed * LEARN_WEIGHT;
}

export function formatEtaSeconds(etaSeconds: number | null): string | null {
  if (etaSeconds === null) return null;
  if (etaSeconds < 10) return "a few seconds left";
  if (etaSeconds < 90) return `~${Math.max(Math.round(etaSeconds / 5) * 5, 10)}s left`;
  return `~${Math.round(etaSeconds / 60)} min left`;
}
