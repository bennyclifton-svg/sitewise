export type TenderBbox = {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
};

export type TenderPageEvidence = {
  imagePath: string | null;
  pageNumber: number | null;
  bbox: TenderBbox | null;
  label: string | null;
};

export function pageEvidenceFromPayload(
  payload: Record<string, unknown>,
): TenderPageEvidence {
  const evidence = readRecord(payload.evidence) ?? payload;
  return {
    imagePath:
      findStringByKey(evidence, "image_path") ??
      findStringByKey(evidence, "imagePath"),
    pageNumber:
      findNumberByKey(evidence, "page_no") ??
      findNumberByKey(evidence, "page"),
    bbox: findBbox(evidence),
    label:
      findStringByKey(evidence, "doc") ??
      findStringByKey(evidence, "document") ??
      findStringByKey(evidence, "document_id"),
  };
}

function findBbox(value: unknown): TenderBbox | null {
  const record = readRecord(value);
  if (record) {
    const direct = bboxFromRecord(record);
    if (direct) return direct;
    for (const child of Object.values(record)) {
      const match = findBbox(child);
      if (match) return match;
    }
  }
  if (Array.isArray(value)) {
    for (const child of value) {
      const match = findBbox(child);
      if (match) return match;
    }
  }
  return null;
}

function bboxFromRecord(record: Record<string, unknown>): TenderBbox | null {
  const maybeBox = readRecord(record.bbox) ?? record;
  const x0 = readNumber(maybeBox.x0);
  const y0 = readNumber(maybeBox.y0);
  const x1 = readNumber(maybeBox.x1);
  const y1 = readNumber(maybeBox.y1);
  if (x0 === null || y0 === null || x1 === null || y1 === null) return null;
  return { x0, y0, x1, y1 };
}

function findStringByKey(value: unknown, key: string): string | null {
  const record = readRecord(value);
  if (record) {
    const direct = record[key];
    if (typeof direct === "string" && direct.trim()) return direct;
    for (const child of Object.values(record)) {
      const match = findStringByKey(child, key);
      if (match) return match;
    }
  }
  if (Array.isArray(value)) {
    for (const child of value) {
      const match = findStringByKey(child, key);
      if (match) return match;
    }
  }
  return null;
}

function findNumberByKey(value: unknown, key: string): number | null {
  const record = readRecord(value);
  if (record) {
    const direct = readNumber(record[key]);
    if (direct !== null) return direct;
    for (const child of Object.values(record)) {
      const match = findNumberByKey(child, key);
      if (match !== null) return match;
    }
  }
  if (Array.isArray(value)) {
    for (const child of value) {
      const match = findNumberByKey(child, key);
      if (match !== null) return match;
    }
  }
  return null;
}

function readRecord(value: unknown): Record<string, unknown> | null {
  if (typeof value !== "object" || value === null || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function readNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}
