# Edit Fix — Stage 2 survey and packet checklist

**Source plan:** [`edit=fix.md`](./edit=fix.md) §§1–4, 9, 13 · Implementation sequence "Stage 2 — Stable block architecture"
**Written:** 2026-08-20, after Stage 1 landed
**Status key:** `[ ]` not started · `[~]` in progress · `[x]` done **and verified**

> Stage 2 as written is **stale**, not vague. It was drafted without knowledge
> of the codebase and ~70% of what it asks for already ships. Implementing it
> literally would build a duplicate mutation API — it says `INSERT`, the code
> says `ADD` with `placement: before|after`. This file is the corrected,
> executable version. **Read this before `edit=fix.md` §2.**

---

## What already exists (do not rebuild)

Verified by reading the code on 2026-08-20.

| Stage 2 asks for | Reality | Where |
|---|---|---|
| Shared `INSERT/UPDATE/DELETE/MOVE` API | Ships as 9 operations: `ADD UPDATE DELETE MOVE DUPLICATE PROTECT UNPROTECT KEEP CONFIRM_DELETE` | `app/projects/artefact_blocks.py:255` `apply_block_operations` |
| `MOVE` | **Implemented.** It is the unlabelled fall-through after the `ADD` branch, which is why `grep '"MOVE"'` finds only the Literal and the validator | `artefact_blocks.py:419-440` |
| Stable block IDs | `<!-- clerk:block id=blk_… -->` markers, stamped at generation time | `materialize_block_identity`, called from `create_pmp.py:2419`, `procurement_request.py:557`, `api/projects.py:2842` |
| IDs authoritative over offsets | `_resolve_target` tries `target.id` first; range is fallback only | `artefact_blocks.py:767-782` |
| Versioned operations | `expected_base_version` → 409 → reload → rebase → single retry | `api/projects.py` + `lib/optimistic-mutation.ts` |
| One API for human **and** AI edits | Both REST (`api/projects.py:2925`) and MCP (`mcp_bridge/server.py:2231`) call the same `apply_block_operations` | — |

**Consequence:** §2 and §11 of the source plan are already satisfied. §1 is
satisfied server-side. Do not open packets for them.

---

## Real gaps

### G1 — No operation idempotency (`client_operation_id`)

`grep client_operation_id backend/app` → **no matches.** The field appears in
the source plan's §2 example and nowhere in the code.

**The failure it allows.** `runOptimisticMutation`
(`lib/optimistic-mutation.ts:26`) only retries on a 409, and a 409 means the
write did *not* apply — that path is safe. The unsafe path is a **lost
response**: the POST succeeds server-side, the reply is lost to a timeout or
dropped connection, `commit` throws a non-conflict error, the UI reverts to
`snapshot`, and the user clicks again. The operation now applies **twice** —
for `ADD`, a duplicate row.

Version checking does not prevent this: the first (successful) write bumped
the version, so the manual retry carries a stale `expected_base_version` and
409s… which triggers a rebase that re-applies the edit on top of itself.

### G2 — No temporary IDs, and it costs a full reload on every insert

`grep -rn "tmp_" frontend/src` → **no matches.** Source plan §4.

**This is worse than a missing nicety — it defeats the Stage 1 §13 fix for
inserts.** The server generates the block id and wraps the content:

```python
insertion = _marked(block_id, content, target.type)   # artefact_blocks.py:401
```

The client's optimistic markdown inserts the *bare* content with no marker.
So for `ADD` and `DUPLICATE` the two strings differ by the marker, their
SHA-256s differ, and `optimisticMatchesServer` returns false → full document
reload, every time.

| Operation | Optimistic markdown vs server | Reload after Stage 1 fix? |
|---|---|---|
| `UPDATE` | `contentWithPreservedMarker` keeps the existing marker | **No** ✅ |
| `DELETE` | range removal includes the marker | **No** ✅ |
| `ADD` | server adds a marker the client lacks | **Yes** ❌ |
| `DUPLICATE` | server adds a new marker | **Yes** ❌ |

"Add row below" is the plan's headline interaction and it is exactly the case
still doing a full reload. G2 closes it.

---

## Decisions taken

| # | Decision | Chosen | Consequence |
|---|---|---|---|
| D1 | How far does "make block IDs mandatory" go? | **Require an id only for new content.** Freshly generated artefacts already carry markers; legacy drafts keep the range fallback indefinitely. | Two addressing modes stay permanently. Accepted: no migration, nothing breaks, and `_resolve_target` already handles both. |
| D2 | Where is `client_operation_id` stored? | On the draft's provenance JSONB, as a bounded ring of recent ids — **no new table**. | Matches the existing `blocks` provenance precedent. Bounded so it cannot grow without limit. |
| D3 | What does a replayed operation return? | The **stored delta** from the original apply, with HTTP 200. | The client cannot distinguish a replay from a first apply, which is the point — a retry is safe by construction. |
| D4 | Retry carrying a stale `base_version`? | **Idempotency wins.** Check `client_operation_id` *before* the version check; a known id replays regardless of `base_version`. | Otherwise the very retry idempotency exists to protect would 409 and rebase into a double-apply. |
| D5 | Temp id format | `tmp_` + 8 hex chars, client-generated, swapped for the server `blk_` id on confirmation. | Distinguishable from `blk_` by prefix; never persisted server-side. |

---

## Packets

### [x] 2.1 — Idempotent block operations (G1)

**Owns:** `app/projects/artefact_blocks.py`, `app/api/projects.py` block route,
`app/schemas/projects.py`, `lib/api.ts`, `lib/optimistic-mutation.ts`.
**Forbidden:** a new table, a new endpoint, changing the operation vocabulary.

- Accept optional `client_operation_id` on the apply-operations request.
- Before the version check (D4), look it up in provenance; on a hit, return the
  stored delta unchanged (D3).
- On a miss, apply as today and record `{id, delta}` into a bounded ring (D2).
- Client generates one id per logical user action and **reuses it across
  retries** — including the rebase retry inside `runOptimisticMutation`.

**Failing tests first:**

```text
backend  test_replayed_client_operation_id_does_not_apply_twice
backend  test_replay_returns_the_original_delta
backend  test_replay_wins_over_a_stale_base_version
backend  test_operation_id_ring_is_bounded
frontend test_rebase_retry_reuses_the_same_client_operation_id
```

The first test must fail by producing **two** rows for one logical insert —
that is the bug, and it should be visible in the red run.

**Landed 2026-08-20.** Red run of
`test_replayed_client_operation_id_does_not_apply_twice`, before any
implementation:

```text
>       assert state["draft"].content_markdown.count("- Added item") == 1
E       AssertionError: assert 2 == 1
E        +  where 2 = ...count of str object...('- Added item')
E        +    where '## Scope | - First item <!-- clerk:block id=blk_607f... -->
E                          | - Added item <!-- clerk:block id=blk_41df... -->
E                          | - Added item <!-- clerk:block id=blk_ed2a... -->'
```

Green:

```text
backend   tests/test_project_draft_block_operations.py   7 passed
backend   tests/projects/test_artefact_blocks.py        21 passed
backend   full suite  2710 passed, 10 failed (all pre-existing), 7 skipped
backend   uv run ruff check .                           All checks passed!
frontend  86 files, 554 tests passed · typecheck clean · build clean
```

Shape of what shipped:

| Piece | Where |
|---|---|
| Bounded receipt ring + lookup | `artefact_blocks.py` `find_block_operation_receipt` / `record_block_operation_receipt`, `BLOCK_OPERATION_RECEIPT_LIMIT = 20` |
| Optional request field | `schemas/projects.py` `ApplyArtefactBlockOperationsRequest.client_operation_id` |
| Replay ahead of the version check (D4) | `api/projects.py` apply route, before the `try:` that calls `revise_workflow_artefact` |
| Receipt written on the **produced** revision | same route, after the delta is built — that is the row a rebasing client re-addresses |
| One id per logical edit, reused across the rebase retry | `DraftReviewPanel.tsx` `newClientOperationId()`, threaded through `api.applyDraftBlockOperations`'s 5th argument |

**Residual, deliberately not closed here.** The id is minted per
`saveSelectionEdit` / `mutateBlock` call, so it is reused across the internal
rebase retry — the packet's named test — but a *fresh user click* after a lost
reply mints a new id and is not deduplicated. Closing that needs either an
automatic transport retry inside `runOptimisticMutation` or an id pinned to the
composer session; neither is in this packet's bullets. The server-side
primitive is in place for whichever is chosen.

### [x] 2.2 — Temporary block ids (G2)

**Owns:** `lib/artifact-blocks.ts`, `lib/draft-block-delta.ts`,
`components/project/DraftReviewPanel.tsx`.
**Forbidden:** sending `tmp_` ids to the server; persisting them anywhere.

- Client mints `tmp_xxxxxxxx` (D5) and writes a marker into the optimistic
  markdown so an inserted block is addressable immediately.
- On confirmation, swap `tmp_` → the server `blk_` id **in place**, without
  re-rendering the document or moving focus.
- `optimisticMatchesServer` compares *after* the swap, so `ADD`/`DUPLICATE`
  stop triggering a reload.

**Failing tests first:**

```text
frontend test_insert_marks_the_new_block_with_a_temporary_id
frontend test_confirmation_swaps_tmp_id_for_the_server_block_id
frontend test_add_row_does_not_fall_back_to_a_full_reload
frontend test_focus_survives_the_id_swap
```

`test_add_row_does_not_fall_back_to_a_full_reload` is the packet's exit: it
must assert `getLatestDraft` was **not** called.

**Landed 2026-08-20.** Red run of the exit test, before any implementation —
the optimistic body is missing the marker the server wrote, so the hashes
differ and the reload path takes over:

```text
 × inserts a table row without falling back to a full reload
AssertionError: expected "vi.fn()" to be called with arguments: [ ObjectContaining{…} ]
      "content_markdown": "## Snapshot
  | Field | Status |
  | --- | --- |
  | Budget | Grounded |<!-- clerk:block id=blk_dddd… -->
- | Budget | Grounded |<!-- clerk:block id=blk_ffff… -->
+ | Budget | Grounded |
  ",
```

Green:

```text
frontend  artifact-blocks + table-row-edit + DraftReviewPanel   70 passed
frontend  full suite   86 files, 563 tests passed
frontend  pnpm typecheck clean · pnpm build clean · eslint clean on changed files
backend   untouched by this packet; 2.1's numbers stand
```

Shape of what shipped:

| Piece | Where |
|---|---|
| `tmp_` + 8 hex minting (D5) | `artifact-blocks.ts` `newTemporaryBlockId` |
| Marker placement mirroring the server's `_marked` | `artifact-blocks.ts` `markedBlock` |
| Optional `blockId` on the inserts | `insertBeforeBlock` / `insertAfterBlock` / `duplicateBlock` |
| In-place swap on confirmation (D5) | `artifact-blocks.ts` `swapTemporaryBlockIds`, keyed off `delta.changed_block_ids` |
| Id minted per insert, swapped before the hash compare | `DraftReviewPanel.tsx` `mutateBlock` — in the `confirmed` callback *and* in the `resolveConfirmedDraft` call, so the server id lands on the same render that confirms the edit |
| `tmp_` markers stripped wherever `blk_` ones were | `DraftReviewPanel.tsx` `editableBlockContent` / `contentWithPreservedMarker`, `table-row-edit.ts` `BLOCK_MARKER_RE` — a block is marked `tmp_` for the whole in-flight window, so cell editing and outbound content must see through it |

Temp ids never reach the server by construction: the panel's id-*extraction*
regexes still match `blk_` only, so a `tmp_`-marked block addresses by range,
and `ArtefactBlockTarget.id` rejects anything but `blk_` at the schema.

**Residuals, deliberately not closed here.**

1. **"Add table row above/below" and "Add list item above/below" are dead in
   the browser.** Verified 2026-08-20 in real Chrome (system Chrome via
   Playwright, React StrictMode, the real `MarkdownContent` + editors driven
   through the ⋯ menu). Result per block type:

   | Menu action | Composer opens | Composer survives | Saves |
   |---|---|---|---|
   | Add table row below | yes | **no — self-cancels** | — |
   | Add list item below | yes | **no — self-cancels** | — |
   | Add paragraph below | yes | yes | yes |

   Mechanism, from a `focusin`/`focusout` trace: the composer cell takes focus,
   then Radix's `DropdownMenuContent` — **still mounted**, its focus scope
   still trapping — pulls focus back to itself; the composer's `onBlur` sees a
   clean editor and calls `onCancel`. It is a focus *trap*, not the close-time
   restore, and not a jsdom artefact.

   Two candidate fixes were tried in the live browser and **both failed**:
   `onCloseAutoFocus={(e) => e.preventDefault()}` on the block-actions menu
   (fires later than the trap) and moving the editors' focus from
   `useLayoutEffect` to a passive `useEffect` (the trap is asynchronous, so
   effect phase does not change the ordering). Untested candidate: stash the
   selected action and run it from `onCloseAutoFocus`, so the composer mounts
   only once the scope has released.

   Consequence for this packet: the exit test drives `DUPLICATE` on a table row
   instead — same `mutateBlock` → insert → mint → swap → hash path, minus the
   composer. The G2 machinery is done; the composer is a separate defect and
   blocks the source plan's headline interaction.
2. **`ADD` with `placement: "before"` against a marker-carrying paragraph
   still reloads.** The server addresses from `_address_start`, i.e. the
   marker's own line, while the client's paragraph range starts at the content
   line — so the two insert at different offsets and the hashes diverge. Table
   rows and list items carry inline markers and are unaffected. Closing it
   means changing what `blockTargetForRange` calls a paragraph's start, which
   moves every anchor offset; out of scope for this packet.

---

## Exit gate

- [x] 2.1 and 2.2 `[x]` with pasted output
- [x] `pnpm typecheck && pnpm test && pnpm build` clean (86 files, 563 tests)
- [ ] `uv run ruff check .` clean — clean as of 2.1; backend untouched by 2.2
- [ ] Backend failures ⊆ the 10 pre-existing (5 `test_greenfield_taxonomy`,
      `test_override_rejects_cross_project_document`,
      `test_database_runner_contract`, `test_create_pmp`, `test_update_pmp`,
      `test_worker_entrypoint`) — as of 2.1; backend untouched by 2.2
- [x] `grep -rnE "tmp_[a-f0-9]{8}" backend/app backend/tests` returns nothing —
      temp ids never reach the server (bare `tmp_` matches `tmp_path` fixtures)
- [x] No new table, no new endpoint, operation vocabulary unchanged

## Baseline to measure against

Recorded at the end of Stage 1, 2026-08-20:

```text
frontend  86 files, 553 tests passed · typecheck clean · build clean
backend   2703 passed, 10 failed (all pre-existing), 7 skipped
```
