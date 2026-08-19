# X1 Programme — Working Set

> **Read this file first. It is short on purpose.**
> It tells you which *one* other file to open. Do not read the whole folder.

## What this programme does

Converge document classification, filing, invoice review, project events, Pulse
and email onto **one intake spine**, without creating a parallel `v2` system.

Authoritative doctrine: [`00-doctrine.md`](./00-doctrine.md) (~120 lines, always read it)
Verified codebase map: [`01-ground-truth.md`](./01-ground-truth.md) (read once per stage —
**stale at Gate 2; packet 9.0 rewrites it**)
Review checkpoint: [`91-review-2026-08-19.md`](./91-review-2026-08-19.md) (Stages 8B / 9–12)
Wave 3 packets: Stages 13–22 — **peer-review the stage files before implementing**
Progress ledger: [`TRACKER.md`](./TRACKER.md) (**you must update this**)
Product vision + rationale: [`../2026-08-18-pulse.md`](../2026-08-18-pulse.md) (read only if you need *why*)

## Which file do I open?

Open `TRACKER.md`, find the first packet that is not `[x]`, and open the stage
file it names. That is your entire reading list.

| Stage | File | Unblocks |
|---|---|---|
| 0 | [`stage-00-baseline.md`](./stage-00-baseline.md) | everything |
| 1 | [`stage-01-evidence-safety.md`](./stage-01-evidence-safety.md) | retrieval correctness |
| 2 | [`stage-02-audit-backfill.md`](./stage-02-audit-backfill.md) | historical repair |
| 3 | [`stage-03-classification-contract.md`](./stage-03-classification-contract.md) | **Gate 1** — all downstream |
| 4 | [`stage-04-deterministic-classifier.md`](./stage-04-deterministic-classifier.md) | accuracy |
| 5 | [`stage-05-user-override.md`](./stage-05-user-override.md) | trust + labelled data |
| 6 | [`stage-06-collapse-classifiers.md`](./stage-06-collapse-classifiers.md) | one decision engine |
| 7 | [`stage-07-auto-filing.md`](./stage-07-auto-filing.md) | Sort Files UX |
| 8 | [`stage-08-taxonomy-migration.md`](./stage-08-taxonomy-migration.md) | **Gate 2** |
| 8B | [`stage-8B-classification-remediation.md`](./stage-8B-classification-remediation.md) | **Gate 2 (Wave A blocks it)** |
| 9 | [`stage-09-consumer-behavior.md`](./stage-09-consumer-behavior.md) | retrieval / PMP / cost discovery |
| 10 | [`stage-10-invoice-foundation.md`](./stage-10-invoice-foundation.md) | D5 invoice snapshot |
| 11 | [`stage-11-invoice-validation.md`](./stage-11-invoice-validation.md) | coded invoice issues |
| 12 | [`stage-12-invoice-workflow.md`](./stage-12-invoice-workflow.md) | approval gate; unblocks 13 |
| 13 | [`stage-13-project-event-spine.md`](./stage-13-project-event-spine.md) | **shared verb vocabulary** — unblocks 14 |
| 14 | [`stage-14-pulse-mvp.md`](./stage-14-pulse-mvp.md) | **Gate 3** — Pulse MVP |
| 15 | [`stage-15-email-foundation.md`](./stage-15-email-foundation.md) | raw email store; after Gate 3 |
| 16 | [`stage-16-email-intake.md`](./stage-16-email-intake.md) | attachments = canonical intake |
| 17 | [`stage-17-email-matching.md`](./stage-17-email-matching.md) | project match + threads |
| 18 | [`stage-18-email-intelligence.md`](./stage-18-email-intelligence.md) | categories as metadata; `email.*` verbs |
| 19 | [`stage-19-email-mcp-drafts.md`](./stage-19-email-mcp-drafts.md) | MCP + user-approved send |
| 20 | [`stage-20-closed-loop-procurement.md`](./stage-20-closed-loop-procurement.md) | issue RFT via approved email |
| 21 | [`stage-21-advanced-pulse.md`](./stage-21-advanced-pulse.md) | since-window + chains |
| 22 | [`stage-22-project-email-aliases.md`](./stage-22-project-email-aliases.md) | `PROJECTCODE@in.sitewise.au` |
| E | [`90-downstream-stages.md`](./90-downstream-stages.md) § Stage E | model fallback — measurements, not a date |

## Context budget (this is a hard rule)

Each stage file declares a **Reading list**. Read those files and nothing else.
If you believe you need a file outside the list, stop and write an
**Integration note** in `TRACKER.md` instead of reading it.

Rationale: this programme is far larger than one context window. The only way it
survives is if each packet is small enough that a fresh agent can load it cold,
finish it, and hand off through `TRACKER.md`.

## The loop, every single packet

```text
1. Open TRACKER.md. Claim the packet: set [ ] → [~], write your name + branch.
2. Read the stage file's Reading list. Nothing else.
3. Write the failing test named in the packet. Run it. Confirm it FAILS.
4. Write the minimal implementation.
5. Run the packet's verification commands. Paste real output into TRACKER.md.
6. Commit with the message given in the packet.
7. Set [~] → [x] in TRACKER.md with commit SHA. Stop.
```

**One packet per commit. One packet per agent session where possible.**

## Rules that override your judgement

- If a packet's exit command fails, you are **not done**. Do not mark `[x]`.
- If you find an unrelated bug, write it under *Integration notes* in
  `TRACKER.md`. Do not fix it.
- Do not modify a file another agent owns (see *Ownership* in each stage file).
  Raise an integration note instead.
- Do not add a file without stating, in the commit body, which existing code it
  replaces.
- If you are running low on context, **stop mid-packet**, write exactly where you
  got to in `TRACKER.md` under *Handoff*, and commit nothing broken.

## Status conventions (match repo house style)

- `[ ]` not started
- `[~]` in progress (owner + branch recorded)
- `[!]` blocked (blocker recorded)
- `[x]` complete **and** verification output pasted
