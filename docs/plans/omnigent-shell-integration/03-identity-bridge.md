# Phase 3 — Identity bridge (Supabase → Omnigent), per-project

> Part of [Omnigent Shell Integration](./README.md) — **read the README first**.
> **Depends on:** [Phase 2](./02-domain-agent-tool-bridge.md) (tool-layer authorization exists to enforce identity against).
> **Resume context:** The Clerk tools authorize by `project_id` but nothing yet establishes *who the caller is* when a request comes through the Omnigent shell. This phase makes one Supabase sign-in flow through Omnigent and carry into per-project tool authorization.

**Goal:** One sign-in (Supabase) grants access to the Omnigent shell, and the same identity gates project access at the tool boundary — no gap where a user reaches another project. Decisions #5 (Supabase primary) + #6 (per-project).

---

### Task 3.1: Choose header-injection over full OIDC (documented)

**Files:**
- Create: `docs/plans/omnigent/auth-bridge-decision.md`

**Rationale to record:** Omnigent supports a `header` auth mode (`OMNIGENT_AUTH_PROVIDER=header`, reads `X-Forwarded-Email` or a configured header) for "behind an existing SSO proxy." Clerk's backend already validates Supabase JWTs (`backend/app/auth/dependencies.py`). Putting Clerk (or a thin reverse proxy) in front of Omnigent and injecting the validated identity header is simpler than standing up OIDC and reuses `get_current_user`. Full OIDC (`OMNIGENT_OIDC_ISSUER` → Supabase) is the fallback if we later want Omnigent to own the login redirect.

**Env vars to enumerate:** `OMNIGENT_AUTH_ENABLED=1`, `OMNIGENT_AUTH_PROVIDER=header`, `OMNIGENT_AUTH_HEADER=<name>` (default `X-Forwarded-Email`), and the strip-prefix knob if needed.

**Acceptance:** Decision doc committed with env vars listed.

---

### Task 3.2: Build the auth-forwarding edge

**Files:**
- Create: `deploy/proxy/` (reverse-proxy config) **or** `backend/app/proxy/omnigent_gateway.py` (FastAPI passthrough that validates Supabase then proxies to Omnigent with the identity header)
- Test: `backend/tests/proxy/test_omnigent_gateway.py`

**Steps (TDD):**
1. Failing test: a request with a valid Supabase bearer token is proxied with `X-Forwarded-Email: <email>` (and a stable user-id header) injected; a request with no/invalid token is rejected 401 and never reaches Omnigent.
2. Implement the gateway reusing `get_current_user`. **Strip any client-supplied identity header** and overwrite it (security: per Omnigent's header-mode warning, the proxy MUST overwrite so a client can't spoof identity).
3. Run → PASS. Commit `feat(auth): supabase→omnigent header-injection gateway`.

**Acceptance:** Only Supabase-authenticated requests reach the Omnigent shell, carrying a trusted identity. This is security seam #2 — do not skip the header overwrite.

---

### Task 3.3: Map Omnigent user → Clerk user → project authorization

**Files:**
- Modify: `backend/app/mcp/context.py`
- Test: `backend/tests/mcp/test_identity_mapping.py`

**Steps:**
1. Failing test: given the identity header Omnigent forwards into an MCP tool call, `context.py` resolves it to a Clerk `CurrentUser` and authorizes the requested `project_id`.
2. Implement the mapping (email/sub → Supabase user id → membership check from Task 2.5).
3. Run → PASS. Commit.

**Acceptance:** The identity established at the edge (3.2) is the same identity enforced at the tool boundary (2.5) — closed loop, no bypass.

---

**When all tasks pass:** mark Phase 3 ☑ in [README.md](./README.md). Proceed to [Phase 6](./06-per-project-workspaces.md) (needs 2+3) and/or continue the UI track ([Phase 4](./04-strip-coding-chrome.md), [Phase 5](./05-dedicated-panels.md)).
