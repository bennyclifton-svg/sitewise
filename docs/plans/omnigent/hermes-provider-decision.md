# Hermes Provider Decision

Date: 2026-07-01

Status: **Provider configured and verified on Linux.** OAuth done, a Hermes turn
completed on the ChatGPT subscription with no API key. The only remaining Phase 0
item is the `omnigent setup` cross-check, which lands in Task 0.3 (Omnigent not
yet installed).

## Decision

Use Hermes' `openai-codex` provider authenticated by OAuth against the user's
ChatGPT/Codex subscription. Do **not** use an OpenAI API key, and do **not**
create a Nous Portal account for the Clerk shell integration preflight.

This preserves the plan requirement that Hermes stays model-agnostic: the active
provider/model can be changed later with `hermes model` without touching Clerk
application code.

## Verified Configuration (Linux)

Configured in **WSL2 Ubuntu 24.04** (the R2 Linux target for the spike), Hermes
`v0.17.0`. `~/.hermes/config.yaml` `model` block:

```yaml
model:
  default: gpt-5.5
  provider: openai-codex
  base_url: https://chatgpt.com/backend-api/codex
```

Acceptance turn (no API key set — `hermes config` shows all keys "(not set)"):

```text
$ hermes -z "Reply with exactly: hello from codex"
hello from codex
```

## Chosen Model — `gpt-5.5`

The Codex-OAuth picker offered `gpt-5.5`, `gpt-5.4`, `gpt-5.4-mini`,
`gpt-5.3-codex-spark`. Chose **`gpt-5.5`** (flagship): the Clerk agent is a
document-reasoning / prose-authoring / tool-calling domain lead — not a code-only
agent (so not `codex-spark`) — and needs reasoning headroom (so not `-mini`).

## api_mode (Hermes issue #5718)

Effective mode = **`codex_responses`** (native). `hermes model` auto-set
`base_url` to `https://chatgpt.com/backend-api/codex` (the Codex *responses*
backend) and a live turn succeeded on that default, so `chat_completions` was not
needed. Keep `codex_responses`; fall back to
`hermes config set model.api_mode chat_completions` only if a backend/tool-call
incompatibility surfaces later.

## Auth Procedure (as actually performed)

The plan's shorthand `hermes auth add codex-oauth` is not the v0.17.0 syntax. The
working command:

```bash
hermes auth add openai-codex --type oauth --no-browser
```

- `openai-codex` is the provider id; credential type is the flag `--type oauth`.
- `--no-browser` is required on WSL (auto-open fails: `gio: Operation not
  supported`). It prints the device URL `https://auth.openai.com/codex/device`
  plus a code; open it in the **Windows** browser. WSL2 shares `localhost`, so
  the callback completes.
- Do **not** run `hermes model` cold: with no provider configured it defaults to
  a **Nous Portal** login (`portal.nousresearch.com`) — an account we don't want.
  Add the `openai-codex` credential first; then `hermes model` shows
  "OpenAI ▸ … ← currently active" with no portal detour
  (OpenAI ▸ → **Use existing credentials** → pick model).

## Model Swap Procedure

To swap Hermes providers or models later (Hermes configuration only, not Clerk
code):

```bash
hermes model                                  # interactive: 30+ providers
# or directly:
hermes config set model.provider <provider>
hermes config set model.default  <model>
```

## Auxiliary Routing (R1 rate-limit tip) — TODO, recommended

To protect the ChatGPT rate limit, route auxiliary tasks (title generation,
context compression, vision detect, session search, goal judge) to a cheaper
model — planned target `gpt-5.4-mini` or a cheap OpenRouter model. **Not yet
configured.** Do via `hermes model` → "Configure auxiliary models…" or under
`auxiliary.<task>.*` in `config.yaml`. Deferred so the first gate proves the
primary ChatGPT path before adding a second provider.

## Verification Gate

- [x] `hermes --version` resolves on Linux (`v0.17.0`).
- [x] `hermes auth add openai-codex --type oauth` completes via device-code OAuth.
- [x] `~/.hermes/config.yaml` contains the `openai-codex` provider.
- [x] A Hermes turn completes without any OpenAI API key.
- [ ] `omnigent setup` reports Hermes ready on `openai-codex / gpt-5.5` — Task 0.3.

## Gotchas Log

- Install: `curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash`
  (uv-based; binary → `~/.local/bin/hermes`; prereqs `git curl xz-utils`; reload
  with `exec bash`).
- WSL DNS was flaky for the install host — fixed with
  `echo -e "nameserver 8.8.8.8\nnameserver 1.1.1.1" | sudo tee /etc/resolv.conf`
  (may reset on `wsl --shutdown`; make durable via `/etc/wsl.conf`
  `generateResolvConf = false` only if it recurs).
- Paste hazard: don't paste multi-line blocks containing a `sudo` line — the
  trailing lines get consumed by the password prompt. Run the installer alone.
