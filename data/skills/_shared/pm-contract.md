# SiteWise PM Contract

This is the shared execution contract for SiteWise system skills.

It is not a user-invoked skill. It is the thin reference spine that system skills inherit so each workflow does not restate the same mechanics.

## Authority

System skills obey this stack:

1. Active-project evidence only.
2. `../../AGENTS.md`.
3. `../../00-doctrine/doctrine.md`.
4. Targeted seed files in `../../01-seed/`.
5. Atomic and system skill files in `../../02-skills/`.
6. General model knowledge, labelled as assumption where evidence is absent.

If active-project evidence conflicts with doctrine, active-project evidence wins. Another project folder is never evidence for the active project.

## Mandatory Doctrine Anchors

Every system skill inherits these doctrine and workspace rules:

- `../../AGENTS.md` Sec. 1: authority stack.
- `../../AGENTS.md` Sec. 2: three-overlay declaration gate.
- `../../AGENTS.md` Sec. 5: draft-for-review output discipline.
- `../../AGENTS.md` Sec. 6: folder-driven voice register.
- `../../AGENTS.md` Sec. 9: system skills are canonical phase-gate entry points.
- `../../00-doctrine/doctrine.md` evidence discipline: Facts, Assumptions, Judgements and Recommendations.
- `../../00-doctrine/doctrine.md` register discipline: mandatory row fields and source references.
- `../../00-doctrine/doctrine.md` seed-consultation discipline.
- `../../00-doctrine/doctrine.md` escalation triggers.
- `../../00-doctrine/doctrine.md` decision discipline.

## System-Skill Skeleton

Every system skill follows this sequence unless its file states a justified exception:

0. Pre-flight: read the active project `README.md` and enforce the Sec. 2 declaration gate at the system-skill boundary.
1. Invoke `../atomic/seed-targeted-read.md` with the task subject where seed consultation is required.
2. Invoke `../atomic/evidence-sweep.md` with the task subject.
3. Run the workflow-specific assessment or drafting sequence.
4. Use `../atomic/register-row-draft.md` for structured register rows.
5. Use `../atomic/markdown-draft-for-review.md` for narrative outputs.
6. Route Excel work through `../atomic/excel-safe-edit.md` and `../atomic/excel-verify.md`.
7. Surface gaps and escalation triggers explicitly.
8. Return a short summary: drafts produced, register rows proposed, gaps open, escalations surfaced and next action.

## Atomic Mechanics

The six atomic skills are the mechanical layer:

| Atomic | Role |
| --- | --- |
| `../atomic/evidence-sweep.md` | Active-project evidence inventory and gap report |
| `../atomic/seed-targeted-read.md` | Declaration gate and targeted seed loading |
| `../atomic/register-row-draft.md` | Register row drafting with mandatory fields |
| `../atomic/markdown-draft-for-review.md` | Draft markdown output with provenance |
| `../atomic/excel-safe-edit.md` | Controlled Excel edits |
| `../atomic/excel-verify.md` | Post-edit Excel checks |

## Substrate Boundary

Markdown and Excel are the active SiteWise register substrates in v1.

`project.db` is a future migration target only. No current skill or Clerk local-v1 workflow writes to `project.db` unless a later explicit PRD, issue and user approval changes that boundary.

## Clerk Relationship

`../../02-skills/` is canonical for workflow contracts. Clerk workflow buttons and runtime paths implement these contracts; they do not become parallel sources of truth.
