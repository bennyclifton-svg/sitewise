# Domain documentation

This is a single-context repository.

## Before exploring

- Read root `CONTEXT.md` when it exists.
- Read relevant decisions under root `docs/adr/` when that directory exists.
- Always follow root `AGENTS.md`, the stack-specific `AGENTS.md`, and the
  canonical plans named there.
- If `CONTEXT.md` or `docs/adr/` does not yet exist, proceed silently; those
  files are created only when domain language or an architectural decision
  needs to be recorded.

## Vocabulary and decisions

Use terms from `CONTEXT.md` when naming interfaces, tests, issues, and domain
concepts. If a proposed change conflicts with an ADR, identify the conflict
explicitly rather than silently overriding it.
