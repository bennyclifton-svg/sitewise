import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { afterEach, describe, expect, it } from "vitest";

import { normalizeDraftMarkdown } from "@/lib/artifact-markdown";
import { isAnchorError, resolveSelectionAnchor } from "@/lib/markdown-selection";

const SOURCE = `# Plan

## Procurement posture

The head builder is procured through a single-stage invited tender.

| Section | Evidence status |
| --- | --- |
| Appointment & fee | Grounded |

## Programme

Slab, frame, lockup and fixing are the tracked milestones.
`;

function offsetsOf(needle: string): { start: number; end: number } {
  const start = SOURCE.indexOf(needle);
  if (start < 0) throw new Error(`fixture is missing ${needle!}`);
  return { start, end: start + needle.length };
}

const PARAGRAPH_ONE = offsetsOf(
  "The head builder is procured through a single-stage invited tender.",
);
const TABLE_ROW = offsetsOf("| Appointment & fee | Grounded |");
const HEADING_TWO = offsetsOf("## Programme");
const PARAGRAPH_TWO = offsetsOf(
  "Slab, frame, lockup and fixing are the tracked milestones.",
);

/**
 * Mirrors what MarkdownContent renders: block elements carrying source offsets,
 * with a table cell whose *rendered* text (a badge) differs from its source.
 */
function renderFixture(): HTMLElement {
  const container = document.createElement("div");
  container.innerHTML = `
    <p data-md-start="${PARAGRAPH_ONE.start}" data-md-end="${PARAGRAPH_ONE.end}"
      >The head builder is procured through a single-stage invited tender.</p>
    <table><tbody>
      <tr data-md-start="${TABLE_ROW.start}" data-md-end="${TABLE_ROW.end}">
        <td>Appointment &amp; fee</td><td><span class="badge">Grounded</span></td>
      </tr>
    </tbody></table>
    <div data-decision-id="procurement-route"><button>Traditional</button></div>
    <h2 data-md-start="${HEADING_TWO.start}" data-md-end="${HEADING_TWO.end}">Programme</h2>
    <p data-md-start="${PARAGRAPH_TWO.start}" data-md-end="${PARAGRAPH_TWO.end}"
      >Slab, frame, lockup and fixing are the tracked milestones.</p>
    <div data-instruction-ui><textarea>tighten this</textarea></div>
  `;
  document.body.appendChild(container);
  return container;
}

function selectAcross(from: Node, to: Node): Selection {
  const range = document.createRange();
  range.setStart(from, 0);
  range.setEnd(to, to.textContent?.length ?? 0);
  const selection = window.getSelection();
  if (!selection) throw new Error("jsdom did not provide a Selection");
  selection.removeAllRanges();
  selection.addRange(range);
  return selection;
}

function textNodeIn(element: Element): Node {
  const node = document.createTreeWalker(element, NodeFilter.SHOW_TEXT).nextNode();
  if (!node) throw new Error("no text node found");
  return node;
}

afterEach(() => {
  window.getSelection()?.removeAllRanges();
  document.body.innerHTML = "";
});

describe("resolveSelectionAnchor", () => {
  it("resolves a selection inside one paragraph to that paragraph's source range", () => {
    const container = renderFixture();
    const paragraph = container.querySelector("p")!;
    const selection = selectAcross(textNodeIn(paragraph), textNodeIn(paragraph));

    const result = resolveSelectionAnchor(selection, container, SOURCE);

    expect(result).not.toBeNull();
    expect(isAnchorError(result)).toBe(false);
    expect(result).toMatchObject({
      start: PARAGRAPH_ONE.start,
      end: PARAGRAPH_ONE.end,
      quotedText:
        "The head builder is procured through a single-stage invited tender.",
    });
  });

  it("resolves a table cell to the row's SOURCE text, not the rendered badge", () => {
    const container = renderFixture();
    const badge = container.querySelector(".badge")!;
    const selection = selectAcross(textNodeIn(badge), textNodeIn(badge));

    const result = resolveSelectionAnchor(selection, container, SOURCE);

    expect(isAnchorError(result)).toBe(false);
    // The user selected the word "Grounded" inside a Badge; the anchor is the
    // whole source row, pipes and all. This is D1 — never reverse-map the DOM.
    expect(result).toMatchObject({
      quotedText: "| Appointment & fee | Grounded |",
    });
  });

  it("suppresses itself inside a decision block", () => {
    const container = renderFixture();
    const decision = container.querySelector("[data-decision-id] button")!;
    const selection = selectAcross(textNodeIn(decision), textNodeIn(decision));

    expect(resolveSelectionAnchor(selection, container, SOURCE)).toBeNull();
  });

  it("suppresses itself inside the instruction UI", () => {
    const container = renderFixture();
    const tray = container.querySelector("[data-instruction-ui] textarea")!;
    const selection = selectAcross(textNodeIn(tray), textNodeIn(tray));

    expect(resolveSelectionAnchor(selection, container, SOURCE)).toBeNull();
  });

  it("rejects a selection spanning two sections", () => {
    const container = renderFixture();
    const first = container.querySelector("p")!;
    const last = container.querySelectorAll("p")[1]!;
    const selection = selectAcross(textNodeIn(first), textNodeIn(last));

    const result = resolveSelectionAnchor(selection, container, SOURCE);

    expect(isAnchorError(result)).toBe(true);
    expect(result).toEqual({ error: "Select text within a single section." });
  });

  it("returns the union range for two blocks in one section", () => {
    const container = renderFixture();
    const paragraph = container.querySelector("p")!;
    const row = container.querySelector("tr")!;
    const selection = selectAcross(textNodeIn(paragraph), textNodeIn(row));

    const result = resolveSelectionAnchor(selection, container, SOURCE);

    expect(isAnchorError(result)).toBe(false);
    expect(result).toMatchObject({
      start: PARAGRAPH_ONE.start,
      end: TABLE_ROW.end,
    });
  });

  it("returns null for a collapsed selection", () => {
    const container = renderFixture();
    const paragraph = container.querySelector("p")!;
    const range = document.createRange();
    range.setStart(textNodeIn(paragraph), 3);
    range.collapse(true);
    const selection = window.getSelection()!;
    selection.removeAllRanges();
    selection.addRange(range);

    expect(resolveSelectionAnchor(selection, container, SOURCE)).toBeNull();
  });

  it("returns null when the selection is outside the container", () => {
    const container = renderFixture();
    const outside = document.createElement("p");
    outside.setAttribute("data-md-start", "0");
    outside.setAttribute("data-md-end", "6");
    outside.textContent = "# Plan";
    document.body.appendChild(outside);
    const selection = selectAcross(textNodeIn(outside), textNodeIn(outside));

    expect(resolveSelectionAnchor(selection, container, SOURCE)).toBeNull();
  });

  it("returns null when the touched block carries no offsets", () => {
    const container = document.createElement("div");
    container.innerHTML = "<p>Unstamped prose.</p>";
    document.body.appendChild(container);
    const paragraph = container.querySelector("p")!;
    const selection = selectAcross(textNodeIn(paragraph), textNodeIn(paragraph));

    expect(resolveSelectionAnchor(selection, container, SOURCE)).toBeNull();
  });

  it("returns null when offsets fall outside the source (a stale render)", () => {
    const container = document.createElement("div");
    container.innerHTML =
      '<p data-md-start="9000" data-md-end="9100">Stale block.</p>';
    document.body.appendChild(container);
    const paragraph = container.querySelector("p")!;
    const selection = selectAcross(textNodeIn(paragraph), textNodeIn(paragraph));

    expect(resolveSelectionAnchor(selection, container, SOURCE)).toBeNull();
  });

  it("returns null when there is no selection at all", () => {
    const container = renderFixture();
    expect(resolveSelectionAnchor(null, container, SOURCE)).toBeNull();
  });
});

const VECTORS_PATH = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../../backend/tests/sitewise/fixtures/normalize_vectors.json",
);

type NormalizeVector = { name: string; input: string; expected: string };

const vectors: NormalizeVector[] = JSON.parse(readFileSync(VECTORS_PATH, "utf-8"));

describe("normalizeDraftMarkdown parity with the backend", () => {
  it("loads the shared vectors", () => {
    expect(vectors.length).toBeGreaterThan(0);
  });

  it.each(vectors)("$name", ({ input, expected }) => {
    expect(normalizeDraftMarkdown(input)).toBe(expected);
  });
});
