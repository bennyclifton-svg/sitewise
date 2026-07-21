# Ingest-Time Project Identity Bootstrap

Date: 2026-07-21

Status: accepted design

Audience: implementation agents

## 1. Problem

When users ask the chat agent to fill `client` and `site_address` from ingested
documents, the flow is sticky:

1. Evidence-derived values must go through `propose_project_profile_change`.
2. The agent asks clarifying questions even when evidence is clear.
3. Direct `update_project_profile` is blocked unless the turn has an explicit
   imperative mutation scope matching a bound patch.
4. Users end up copying values into the profile UI by hand.

Identity already has extractors and a proposal/accept path. What is missing is
**ingest-time bootstrap** that fills empty profile fields without a chat loop.

## 2. Decision

**Option B:** After document ingest, extract identity with confidence. When a
field is empty and confidence is high, auto-apply via the existing proposal
accept path. When confidence is medium or values conflict, leave a pending
proposal for quiet Accept/Reject in the cockpit. Never overwrite a set field.

## 3. Scope

In scope:

- `client` and `site_address` only.
- Hosted project document ingest completion (upload / sort → ingested text).
- Deterministic extraction + confidence (no LLM on the ingest path).
- Proposal create + optional auto-accept.
- Cockpit strip for auto-applied notice and pending Accept/Reject.
- Prompt tightening so the agent does not reopen Q&A when ingest already acted.

Out of scope:

- Taxonomy / building class / scale inference.
- Overwriting user-confirmed profile values.
- Widening mutation-intent regex as the primary fix.
- Chat-only “one-shot propose” as the sole solution.

## 4. Trigger

After a project document finishes ingest successfully:

1. Read current profile for the project.
2. If both `client` and `site_address` are already set → stop.
3. Run identity extraction over the new document text (and optionally other
   already-ingested project documents when needed for stronger patterns).
4. For each still-empty field with an extract, score confidence and either
   auto-apply, propose, or no-op per the rules below.

Hook location should sit after successful hosted ingest persist (same place
document readiness becomes true), not inside chat turns.

## 5. Extraction

Reuse existing helpers:

- `app.projects.identity.identity_from_evidence_texts`
- `app.sitewise.mobilisation_evidence._extract_site_address` /
  `_extract_owners`
- grounding fallbacks already used by those helpers

Attach `ProfileEvidenceReference` entries pointing at the source document(s)
and a short excerpt where practical.

## 6. Confidence model (deterministic)

### Address

| Confidence | Rule |
| --- | --- |
| 0.9 | Street number + street + suburb + state (optional postcode) from a strong pattern (`Project:` / `Re:` / “at …” lines). |
| 0.6 | Partial locality or grounding-only fallback without a clear street line. |
| skip | Letterhead / office addresses; keep existing noise exclusions (e.g. Pacific Highway). |

### Client

| Confidence | Rule |
| --- | --- |
| 0.9 | Clear owners pattern (`To: …`, “prepared for …”, Client line that is people names only). |
| 0.55 | Phrases like `Atelier North for David & Emma Walsh`, `Client: X for Y`, or company-as-client when owners also appear → ambiguous. |
| skip | Sender firm, consultant name, advisor letterhead. |

### Thresholds (v1)

| Band | Action |
| --- | --- |
| ≥ 0.85 | Auto-apply if field empty and no conflicting pending proposal. |
| 0.5 – &lt; 0.85 | Propose only (pending Accept/Reject). |
| &lt; 0.5 | Ignore. |

### Conflicts

- Two different high-confidence values for the same empty field → do not
  auto-apply; open one pending proposal with both evidence refs.
- Matching pending proposal already exists → do not duplicate; optionally
  refresh evidence if the extract matches.
- Field already set on profile → never write.

## 7. Persistence seam

Always use the proposal module:

1. `propose_project_profile_change(..., proposer="ingest", confidence=...)`
2. If auto-apply eligible → immediately `accept_profile_proposal(..., actor_source="ingest")`

Do not call `apply_profile_patch` outside that path for ingest bootstrap.
Revision checks, events, and history stay intact.

Emitted events reuse `resource_type="project_profile_proposal"` so cockpit
query invalidation already keyed on that type continues to work.

## 8. Cockpit UI

Snapshot already exposes `open_profile_proposals`.

Add a quiet control-board strip:

- **Auto-applied:** short status listing filled fields, values, and source doc.
  No action required; profile remains editable.
- **Needs review:** one card with proposed values, confidence, evidence doc,
  Accept / Reject. Prefer one card that covers both fields when they share a
  proposal.
- Do not open a chat turn for confirmation.

API already supports accept/reject via HTTP/MCP; wire Accept/Reject buttons to
those endpoints with `expected_profile_revision`.

## 9. Agent behaviour

Keep the mutation security model unchanged (explicit imperative + bound patch
for direct updates; evidence → propose).

Tighten persona / workspace instructions:

- If profile already has `client` / `site_address` → do not re-propose or ask.
- If a pending ingest proposal exists → point the user to the cockpit card;
  do not start a second clarification loop.
- If the user asks to update identity from documents and fields are empty →
  lodge at most one proposal for clear fields (or note ingest already did),
  then stop. Ask wording questions only when evidence conflicts.
- Direct `update_project_profile` remains only for explicit user-supplied text.

## 10. Error handling

- Extraction failure or empty text → no-op; ingest success is unaffected.
- Proposal validation “no effective change” → no-op.
- Accept revision conflict → leave proposal pending; surface in cockpit.
- Partial success (address high, client medium) → auto-apply address only;
  propose client separately or in one multi-field proposal if both are propose-only.

## 11. Testing

Minimum coverage:

- Unit: confidence scoring for clear owners, ambiguous “X for Y”, strong
  address, letterhead skip, conflict between two docs.
- Unit/integration: ingest hook proposes; high-confidence empty fields
  auto-accept; set fields untouched; pending conflict not duplicated.
- Frontend: Accept/Reject card renders from `open_profile_proposals`;
  auto-applied notice appears after event invalidation.
- Regression: existing mutation-intent / proposal MCP tests still pass.

Golden fixture candidate: Walsh heritage email
(`Client: Atelier North for David & Emma Walsh` + Hargrave Street address)
should propose client (ambiguous) and auto-apply address when empty if the
street pattern scores high — or propose both if address pattern is medium.
Tune expected outcomes in tests once scoring helpers land.

## 12. Non-goals / explicit rejects

- Using chat as the primary bootstrap path.
- Auto-applying medium-confidence “for …” client strings.
- Bypassing proposals for a silent profile PATCH.
- Inferring identity with an LLM during ingest in v1.

## 13. Implementation sketch (not a full plan)

Likely modules:

1. `app/projects/identity_confidence.py` — score extracts; return field decisions.
2. `app/projects/identity_bootstrap.py` — propose / auto-accept orchestration.
3. Hosted ingest completion call site → `bootstrap_identity_from_document(...)`.
4. Frontend control-board strip bound to snapshot proposals + accept/reject API.
5. Prompt edits in `turn_context.py` / `workspace_instructions.py`.

## 14. Success criteria

For a new project with empty identity and a clear site address in ingested
docs:

- Address appears on the profile without a chat turn when confidence ≥ 0.85.
- Ambiguous client strings land as a single Accept/Reject card, not a Q&A.
- Asking chat to “update profile from documents” does not invent a second
  proposal or ask which of two clear wordings to use when ingest already
  resolved or pending the same fields.
