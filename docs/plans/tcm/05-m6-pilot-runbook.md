# M6 — Pilot runbook (human-led)

**Goal (PRD §19):** 3 friendly-customer reports delivered; ≤ 2h operator QA each; go/no-go on the payment link. This is an operations stage — code sessions are small punch-list fixes only.

## Blocking gates before the first report goes out

| Gate | PRD | Owner |
| --- | --- | --- |
| QS red-pen day done; corrections committed to seed files with QS named in `provenance` | §11.3 | Ben (paid QS) |
| Benchmark confidence discipline verified: no `low`-confidence row reachable in customer-facing text (run the M4b grep/claim tests + manual spot check of one rendered report) | §11.2, §9.7 | Ben |
| Engagement-terms wording for data rights | §17, §21.3 | Ben (legal review; blocking before first **paid** report) |
| Disclaimer block present in §8 of the rendered report | §18 | check in M5a output |
| Delivery decision: manual from operator inbox (v1 default) | §21.2 | Ben |

## Per-pilot checklist (repeat ×3)

1. Intake: create project + comparison; fill ProjectContext completely (it drives everything).
2. Upload documents per quote; watch pipeline stages; record wall-clock (target ≤ 30 min processing, §17).
3. Work the QA queue to zero `needs_review`. **Time it.** Record minutes by category (extraction / mapping / silence / flags) — this is the dataset for the go/no-go and for graduation thresholds later.
4. Build report draft; edit narrative; review every flag against §18 guardrails (no intent imputation; Appendix C phrases only).
5. Approve; deliver PDF manually; record `delivered` + delivery note.
6. Debrief: ask the customer the three questions that matter — Was anything confusing? Did you use the builder questions? Would you have paid $X?

## Metrics to record (in this file, per pilot)

- processing wall-clock; QA minutes total + by category; corrections count by entity type
- LLM spend for the comparison (target ≤ A$15, §17)
- T0/T1/T2/T3 mapping share (the cost-flywheel health check, §9.3)
- silence outcomes distribution + how many the operator overturned (reputational-risk signal)
- report-impacting errors found after approval (target: zero)

## Go/no-go (end of M6)

GO on the payment link iff: 3 reports delivered; QA ≤ 2h each (or a credible trend toward it); zero customer-visible factual errors; engagement terms signed off. Otherwise: scope cut per PRD §19's standing rule — M6 may ship with silence inference fully manual (operator sets statuses in the QA console) rather than slip.

## Punch-list session template (for the cheap model)

```
Read AGENTS.md (TCM section) and docs/plans/tcm/05-m6-pilot-runbook.md.
Fix exactly the following pilot finding on feature/tcm-main: <paste finding,
with the failing behavior, the PRD section that defines correct behavior, and
the file(s) involved if known>. Write a regression test first, then the fix.
Touch nothing else. Finish with full pytest output.
```
