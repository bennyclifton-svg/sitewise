import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
});

// jsdom implements Range but not its layout methods. Selection anchoring reads
// the selection's rect to position the instruction card; without this, jsdom
// throws where every browser returns a box.
if (!Range.prototype.getBoundingClientRect) {
  Range.prototype.getBoundingClientRect = () => new DOMRect(0, 0, 0, 0);
  Range.prototype.getClientRects = () =>
    Object.assign([], { item: () => null }) as unknown as DOMRectList;
}

const testEnv = import.meta.env as unknown as Record<string, string | undefined>;

testEnv.VITE_API_BASE_URL ??= "http://localhost:8000";
testEnv.VITE_SUPABASE_URL ??= "http://localhost:54321";
testEnv.VITE_SUPABASE_ANON_KEY ??= "test-anon-key";
