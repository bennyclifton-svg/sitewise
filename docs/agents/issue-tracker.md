# Issue tracker: local Markdown

Issues and PRDs for this repository live as Markdown files under
`docs/issues/`.

## Conventions

- Group related work in `docs/issues/<feature-slug>/`.
- Keep a feature README or PRD beside its implementation issues when useful.
- Name implementation issues with a stable feature prefix and sequence, for
  example `TCM05-001-dependencies-and-preflight.md`.
- Record `status`, `triage_label`, and `labels` in frontmatter when the issue
  participates in triage.
- Append material implementation or review history to the issue rather than
  silently replacing its original acceptance criteria.

## Publishing and reading

When a skill says to publish to the issue tracker, create or update the relevant
file under `docs/issues/<feature-slug>/`. When it says to fetch a ticket, read
the referenced issue file directly. Do not create GitHub issues unless the user
explicitly requests a switch to GitHub tracking.
