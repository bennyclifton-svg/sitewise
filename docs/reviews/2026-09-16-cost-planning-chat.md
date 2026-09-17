# Cost Planning chat recovery — 16 September 2026

Investigated the unanswered Kaposi request in Caves Beach Reno, Cost Planning
thread `8f9edc6f-75ba-47d8-a6cd-f0f12ccaaa8c`.

The original turn began at 11:43:04 UTC using Grok 4.6. It remained active with
only a saved user message beyond its 11:50:08 expiry. At 11:53:54 its partial
answer and interruption message were eventually saved, and the turn was revoked.
Production API logs had no matching execution; the local backend was running on
port 8000. Both normal and Windows selector-loop Pi diagnostics returned OK.
The precise trigger for the original interruption could not be recovered from
the local console logs.

## Reproduced reliability defect

The API emitted failure events, including `[DONE]`, before committing the
assistant error and revoking the turn. A reader stopping at `[DONE]` could
therefore observe a finished stream while the durable turn was still running.
Regression tests failed for provider errors and timeouts at this exact seam.

Failure, timeout, cancellation and queue-error branches now reach persistence
before emitting terminal error events. Added coverage checks the committed
outcome before closing the response iterator at `[DONE]`, including cancellation.
Existing local changes to admission, retries and profile handling were preserved.

Validation: 62 agent API, SSE relay, concurrency and MCP operation tests passed;
Ruff passed on the changed source and test files. This fixes the ordering defect;
it does not establish that this defect caused the original interruption or
provide recovery after an abrupt server crash.

## Request recovery

Replayed the original request through the owner-scoped application handler.
The response was saved successfully at 11:57:42 UTC. It identified Kaposi.pdf
and found no recorded award or preferred contractor in the project evidence.
The generated Cost Plan v1 was an unpriced scaffold, so a follow-up through
the same handler requests source-backed cost operations, explicitly without
awarding a contract or sending communications. The user then submitted a newer
instruction in the application at 12:02:27 UTC, stating that the Kaposi tender
was accepted and requesting approved contract amounts. The diagnostic follow-up
was revoked and stopped to avoid conflicting with that live request.

## Cost operation schema

The recovery attempt also showed the agent discovering and retrying the cost
operation shape (including the required `cost_item` target). MCP advertised
`operations` as `list[dict]`, hiding the existing validated schema. Changed the
tool annotation to `list[CostPlanOperation]` and documented item-key targeting
and decimal money strings. An MCP discovery regression failed before the change
and passed afterward; existing mutation/authorization tests also pass.

Kaposi.pdf's seven priced stage subtotals sum to $182,417.00; its stated 10%
margin gives $200,658.70 excluding GST, or $220,724.57 including GST. These were
independently checked with Python Decimal. This is the quoted construction
basis, excluding unpriced owner-supplied items and exclusions.
