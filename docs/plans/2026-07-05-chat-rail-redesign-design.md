# Chat Rail Redesign — Design

**Date:** 2026-07-05
**Status:** Validated with user (layout, history placement, citation target all confirmed)

## Problem

The project chat is a collapsible bar docked at the bottom of the middle panel
(`ProjectChatBar`). When expanded it competes for vertical space with the work
surface (workbench views, document viewer), the agent runtime selector is a
bare full-width `<select>` floating above the input, the model selector is
disconnected in the app footer, and chat thread history is not reachable from
the project cockpit at all.

## Guiding principles (industry patterns adopted)

1. **Copilot rail, not chat-first page.** SiteWise is a work-surface product;
   Clerk assists it. The assistant gets a persistent full-height rail so it
   never competes with the work surface (GitHub Copilot / M365 Copilot /
   Notion AI pattern). Per user direction the rail is the **left** panel.
2. **Unified composer.** One rounded container: auto-growing textarea on top,
   controls row inside below it (ChatGPT / Claude / Perplexity anatomy).
   Everything that affects the next message lives in the composer.
3. **Thread history one click away**, grouped by recency, scoped to project
   (Perplexity-style list, but in a popover to preserve conversation height).

## Panel architecture

```
┌────────────────┬──────────────────────────────┬──────────────────┐
│ LEFT: Clerk    │ MIDDLE: work surface         │ RIGHT: documents │
│ rail (chat)    │ workbench tabs, doc viewer,  │ repository,      │
│ 380px default  │ source passages, artefacts   │ always visible   │
│ 320–560px      │                              │                  │
└────────────────┴──────────────────────────────┴──────────────────┘
```

- **Left — Clerk rail.** Full-height chat. Width default 380px, clamp
  320–560px, persisted (update `cockpitShellLayout.ts` constants; keep the
  existing localStorage key mechanism, bump defaults).
  - Top strip: Home link + `ProjectSwitcher` (unchanged, compact).
  - Chat header: "Clerk" + thread title, history button, "+ New chat" button.
  - Conversation: fills remaining height. Streaming, citation chips,
    tool-call chips, scroll-to-bottom — all existing `ChatPanel` behaviour.
  - Composer docked at bottom (see anatomy below).
  - `AppSystemFooter` keeps theme toggle only; `LlmModelSelector` moves into
    the composer.
- **Middle — pure work surface.** Workbench views, document viewer, evidence.
  `ProjectChatBar` is deleted; the bottom "Source passage" box is deleted.
- **Right — documents.** Unchanged. Collapse toggle retained as an escape
  hatch for small laptops; defaults to expanded.

## Chat header: history popover

- History icon opens a popover anchored to the chat header listing threads
  for the active project, grouped Today / Yesterday / Previous 7 days /
  Older. Reuses `ChatSessionList` logic (list, create, rename, delete,
  project filter) restyled for the popover; selecting a thread swaps the
  rail conversation without navigating away from the cockpit.
- "+ New chat" creates a thread in the active project and focuses the
  composer.

## Composer anatomy

```
┌──────────────────────────────────────────┐
│ Ask about your project documents…        │  ← textarea, auto-grow 1–6 rows
│                                          │    Enter = send, Shift+Enter = newline
├──────────────────────────────────────────┤
│ [Project ⇄ Cross-project]   Pi ▾  gpt ▾ 🎤 ➤ │  ← controls row
└──────────────────────────────────────────┘
```

- **Left controls:** scope pill — compact segmented Project / Cross-project
  toggle replacing the boxed checkbox block above the history.
- **Right controls:**
  - Agent runtime selector (Pi / Hermes) — compact borderless select; reuse
    `AgentRuntimeSelector` logic, restyle. Hidden when only one runtime
    enabled (existing behaviour).
  - Model selector — `LlmModelSelector` relocated here from the footer,
    compact style.
  - Mic button — rendered now, disabled, tooltip "Voice input coming soon".
  - Send button (icon); morphs to Stop while streaming.

## Citations → middle work surface

Clicking a citation chip opens the source passage / document in the middle
panel (evidence view), side by side with the ongoing conversation. The
`SourcePassagePanel`-below-chat placement is removed. Wire the citation
selection up through the cockpit page so the middle panel can render the
evidence view; the chip keeps its selected state in the rail.

## Responsive (<1024px)

Panels stack (existing behaviour). The rail renders as a normal section;
order: main content, chat, documents. No new mobile work in this phase
beyond not regressing the current stacked layout.

## Component impact

| Component | Change |
| --- | --- |
| `ProjectShell.tsx` | Left column hosts chat rail; drop `chatBar` slot |
| `ProjectLeftNav.tsx` | Becomes the Clerk rail container (switcher + chat) |
| `ProjectChatBar.tsx` | Deleted |
| `ChatPanel.tsx` | Refactored for tall narrow column; composer extracted |
| New `ChatComposer.tsx` | Unified composer (textarea + controls row) |
| `AgentRuntimeSelector.tsx` | Restyled compact, moves into composer |
| `LlmModelSelector.tsx` | Moves from `AppSystemFooter` into composer |
| `ChatSessionList.tsx` | Reused inside new history popover |
| `SourcePassagePanel.tsx` | Rendered in middle panel via cockpit wiring |
| `cockpitShellLayout.ts` | New width constants for the rail |

## Construction-native roadmap (later phases, in priority order)

1. **@-mention documents** in the composer to pin retrieval context
   ("@geotech-report what's the bearing capacity?").
2. **Phase-aware quick-prompt chips** on the empty state (e.g. tender phase →
   "Compare tender submissions", "Summarise addenda").
3. **Message actions → registers:** "Turn this answer into an RFI draft /
   variation / site instruction" feeding the existing register workflows.
4. **Voice:** wire the mic to browser dictation (Web Speech API) first;
   long-term hands-free "site mode" (gloves, site walks).
5. Photo attachment from site → defect/QA logging.

## Out of scope

- Voice implementation (placeholder button only).
- Standalone `/chat/:id` page redesign (left as-is for now).
- Mobile-specific chat UX beyond the existing stacked fallback.
