# Phase 0 — Preflight & Environment

> Part of [Omnigent Shell Integration](./README.md) — **read the README first** for architecture, decisions, and risks.
> **Depends on:** nothing. This is the start.
> **Resume context:** Nothing has been built yet. This phase de-risks the two things that can sink the project (Hermes' provider — R1, now resolved; and Linux/Hermes end-to-end — R2) before any code is written. **Do not start Phase 1 until Task 0.3 passes.**

**Goal:** Prove that a Hermes-backed Omnigent session runs end-to-end on the (Linux) deploy target, on the user's ChatGPT subscription, before we vendor or modify anything.

---

### Task 0.1: Snapshot current state and create the integration branch

**Files:** none (git operations)

**Steps:**
1. From repo root, confirm the working tree state: `git -C "d:/AI Projects/clerk-old" status`.
2. Create branch: `git switch -c feature/omnigent-shell`.
3. Tag the pre-integration commit for rollback reference: `git tag pre-omnigent-integration`.
4. Commit the plan: `git add docs/plans/omnigent-shell-integration && git commit -m "docs: omnigent shell integration plan (sharded)"`.

**Acceptance:** On branch `feature/omnigent-shell`; tag exists; plan committed.

---

### Task 0.2: Configure Hermes on the ChatGPT/Codex subscription (R1 resolved)

**Files:**
- Create: `docs/plans/omnigent/hermes-provider-decision.md` (record the config + swap procedure)

**Steps:**
1. Install Hermes CLI in a Linux environment (or WSL): confirm `hermes --version` resolves. Record install method.
2. Authenticate the ChatGPT subscription: `hermes auth add codex-oauth` (device-code OAuth in a browser; no API key). Confirm it writes the `openai-codex` provider into `~/.hermes/config.yaml`.
3. Set `openai-codex` as the default brain via `hermes model` → OpenAI Codex, and pick the model. Decide the `api_mode` (`chat_completions` vs `codex_responses`, per Hermes issue #5718) and record which you chose and why.
4. (Optional, recommended) Route auxiliary tasks (title generation, context compression, vision detect, session search, goal judge) to a cheaper provider under `auxiliary.<task>.*` in `~/.hermes/config.yaml` to preserve the ChatGPT rate limit for real turns.
5. Verify Omnigent sees it: `omnigent setup` should report Hermes as ready with `openai-codex / <model>`.
6. Write the decision doc: provider (`openai-codex` via OAuth), chosen model + `api_mode`, the model-swap procedure (`hermes model` — stays model-agnostic), and the auxiliary-routing choice.

**Acceptance:** `omnigent setup` shows Hermes ready on `openai-codex`; a Hermes turn runs without any OpenAI API key; decision doc committed.

---

### Task 0.3: Stand up vanilla Omnigent on Linux with a trivial agent (spike, throwaway)

**Files:**
- Create: `docs/plans/omnigent/spike-notes.md`

**Steps:**
1. On the Linux/VPS/Docker target, install Omnigent (`uv tool install omnigent` or the bootstrap script `curl -fsSL https://raw.githubusercontent.com/omnigent-ai/omnigent/main/scripts/install_oss.sh | sh`).
2. Run a ship example on Hermes: `omnigent run examples/scribe --harness hermes` (scribe is a prose-authoring orchestrator — closest shape to our domain agent).
3. Open the web UI at `http://localhost:6767`, send a message, confirm a Hermes turn completes end-to-end.
4. Record in spike-notes: exact install steps, the port, where `chat.db` lands, how the web UI is served, and any Hermes boot errors + fixes.

**Acceptance:** A Hermes-backed session completes a turn in the browser on the Linux target. This de-risks R1+R2 before any code is written. **Gate: do not proceed to Phase 1 until this passes.**

---

**When all three tasks pass:** mark Phase 0 ☑ in [README.md](./README.md) and proceed to [Phase 1](./01-vendor-omnigent.md).
