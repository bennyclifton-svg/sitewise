/**
 * Session-scoped persistence for the anchored-instruction tray.
 *
 * A tray is keyed to one draft *version*: anchors are offsets into that
 * version's markdown, so a tray built against v3 is meaningless against v4.
 * `loadStaleTray` surfaces an older version's tray as a rebase prompt rather
 * than silently discarding it or silently sending anchors the server will
 * reject with a 409.
 */

export type InstructionKind = "revise" | "context";

export type InstructionItem = {
  id: string;
  /**
   * `context` is phase 2 (source-document passage harvesting) and is never
   * produced in v1. It ships now so persisted trays do not need migrating.
   */
  kind: InstructionKind;
  anchorStart: number;
  anchorEnd: number;
  quotedText: string;
  instruction: string;
  /** Display only — the server re-derives the section from the anchor. */
  sectionHeading: string;
  /** Set from a failed apply, so the user can see why an item did not land. */
  error?: string;
};

export type StaleTray = {
  version: number;
  items: InstructionItem[];
};

const KEY_PREFIX = "sitewise:tray:";
const QUOTE_PREVIEW_LIMIT = 180;

/** Collapse a source slice to one readable line for the card and the tray. */
export function truncateQuote(quote: string, limit = QUOTE_PREVIEW_LIMIT): string {
  const collapsed = quote.replace(/\s+/g, " ").trim();
  return collapsed.length > limit ? `${collapsed.slice(0, limit).trimEnd()}…` : collapsed;
}

/** Safari private mode throws on every sessionStorage access. */
function storage(): Storage | null {
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

function trayKey(draftId: string, version: number): string {
  return `${KEY_PREFIX}${draftId}:v${version}`;
}

function isInstructionItem(value: unknown): value is InstructionItem {
  if (typeof value !== "object" || value === null) return false;
  const item = value as Partial<InstructionItem>;
  return (
    typeof item.id === "string" &&
    (item.kind === "revise" || item.kind === "context") &&
    typeof item.anchorStart === "number" &&
    typeof item.anchorEnd === "number" &&
    typeof item.quotedText === "string" &&
    typeof item.instruction === "string" &&
    typeof item.sectionHeading === "string"
  );
}

function parseItems(raw: string | null): InstructionItem[] {
  if (!raw) return [];
  try {
    const parsed: unknown = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter(isInstructionItem) : [];
  } catch {
    return [];
  }
}

export function loadTray(draftId: string, version: number): InstructionItem[] {
  try {
    return parseItems(storage()?.getItem(trayKey(draftId, version)) ?? null);
  } catch {
    return [];
  }
}

export function saveTray(
  draftId: string,
  version: number,
  items: InstructionItem[],
): void {
  try {
    const store = storage();
    if (!store) return;
    if (items.length === 0) {
      store.removeItem(trayKey(draftId, version));
      return;
    }
    store.setItem(trayKey(draftId, version), JSON.stringify(items));
  } catch {
    // Quota or private mode — the in-memory tray remains authoritative.
  }
}

export function clearTray(draftId: string, version: number): void {
  try {
    storage()?.removeItem(trayKey(draftId, version));
  } catch {
    // Nothing to do; the caller has already dropped its in-memory copy.
  }
}

/**
 * The newest tray belonging to an *older* version of this draft, if any.
 *
 * Its anchors are stale by construction, so the UI must offer a rebase rather
 * than applying it.
 */
export function loadStaleTray(draftId: string, version: number): StaleTray | null {
  const store = storage();
  if (!store) return null;
  const prefix = `${KEY_PREFIX}${draftId}:v`;
  let newest: StaleTray | null = null;
  try {
    for (let index = 0; index < store.length; index += 1) {
      const key = store.key(index);
      if (!key?.startsWith(prefix)) continue;
      const candidate = Number(key.slice(prefix.length));
      if (!Number.isInteger(candidate) || candidate >= version) continue;
      const items = parseItems(store.getItem(key));
      if (items.length === 0) continue;
      if (!newest || candidate > newest.version) {
        newest = { version: candidate, items };
      }
    }
  } catch {
    return null;
  }
  return newest;
}

export function dropStaleTrays(draftId: string, version: number): void {
  const store = storage();
  if (!store) return;
  const prefix = `${KEY_PREFIX}${draftId}:v`;
  try {
    const doomed: string[] = [];
    for (let index = 0; index < store.length; index += 1) {
      const key = store.key(index);
      if (!key?.startsWith(prefix)) continue;
      const candidate = Number(key.slice(prefix.length));
      if (Number.isInteger(candidate) && candidate < version) doomed.push(key);
    }
    for (const key of doomed) store.removeItem(key);
  } catch {
    // Best effort only.
  }
}
