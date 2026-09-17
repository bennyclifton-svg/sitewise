# Selected-commit release procedure

This is a preparation and operator-run procedure, not permission to deploy.
Auto Deploy stays disabled. A push alone never restarts production.

1. Select a full Git SHA, with no uncommitted release changes. Use a detached,
   clean checkout of that SHA; do not build from the shared development tree.
   Require successful CI for that SHA: backend offline, frontend, tender seeds,
   disposable database smoke, and Release image gate. Configure these as required
   checks in branch protection. A report with failing checks is not a release approval.
2. Record the operator, approval, SHA, existing API/web image IDs, effective Compose
   configuration location, environment backup location (no secrets in the report),
   current Alembic revision, and backup/restore point. Confirm restore access.
   Review every pending migration for old/new code compatibility. Incompatible
   migrations require a maintenance window and a rehearsed restore or forward fix.
3. Build candidate images in the clean checkout using the pinned lockfiles and
   Node 22.20.0 / pnpm 11.5.2. CI uses dummy public frontend values; the release
   build must use the real public Supabase URL/anon key and `/api`. Never supply a
   service-role key as a VITE argument. Set `BUILD_SHA` to the selected full SHA.
   Set `PREVIOUS_WEB_IMAGE` to the retained current web image tagged by its prior
   SHA (tag its existing image ID first when migrating from legacy `latest`).
   The web Dockerfile copies prior hashed `/assets` before adding new assets, so
   open browser tabs can still load old chunks. Keep previous images for rollback;
   prune retained assets only in a separately planned expiry/migration window.

   ```sh
   docker compose --env-file "$RELEASE_ENV" -f deploy/dokploy.compose.yml build sitewise-api sitewise-web
   python scripts/smoke-web-image.py "sitewise-production-web:$BUILD_SHA" "sitewise-production-api:$BUILD_SHA"
   docker image inspect "sitewise-production-api:$BUILD_SHA" "sitewise-production-web:$BUILD_SHA" --format '{{.Id}} {{json .RepoTags}}'
   ```

   `RELEASE_ENV` is an explicitly selected, protected operator file outside git.
   Do not print resolved Compose configuration: it contains secrets. Smoke uses
   disposable containers and a fake SSE backend, never production credentials.
   Confirm an asset URL from the old image exists in the candidate too.
4. Validate runtime settings in the candidate image before schema changes.
   Production requires `ENVIRONMENT=production`, `EMAIL_PROVIDER=mailgun`, real
   Mailgun configuration, `BILLING_PROVIDER=stripe`, valid Stripe price/webhook
   settings, Pi turn-token secret, and both OpenAI and xAI credentials for the
   advertised models. Persist these in Dokploy, not only its generated `.env`.
   Compose defaults do not override previously saved explicit environment values.
5. Run `python -m alembic current`, `heads`, then `upgrade head` from the candidate
   API image using the explicitly selected production environment **only after
   approval and backup**. Never use a transaction pooler. Record the revision
   before and after. Application startup does not run migrations automatically.
6. Use Dokploy's effective Compose with the selected source configuration and
   its generated domain/network labels preserved. Verify the selected SHA tags
   resolve to the recorded candidate image IDs. Run Compose `config --quiet`,
   then `up -d --no-build` for API, both workers and web. Never use `--build` or
   a moving `main` checkout at this promotion step. Do not overwrite generated
   routing labels with a pristine source Compose file.
7. Verify API health/build identity, all worker health, HTML `Cache-Control:
   no-cache`, gzip JS with `Vary: Accept-Encoding`, hashed asset immutable caching,
   missing assets returning 404, and an open pre-release tab loading lazy routes.
   In an isolated staging account, verify login, cross-account denials, upload /
   download, chat stream first-event latency, Stop while queued/running, quota,
   both model choices, and worker artefact creation. Test Mailgun acceptance and
   recipient delivery separately; an accepted API request is not proof of delivery.
   Test Stripe signature rejection, retries, out-of-order subscription events and
   entitlement changes in Stripe test mode. No real charge is needed.
8. Rollback on failed smoke: select the recorded previous API/worker/web image
   IDs and matching saved configuration, and run `up -d --no-build`. Check health
   and streaming again. Roll back application images only if the migrated schema
   is backward compatible. Never blindly downgrade a live database; use the
   reviewed forward fix or approved backup restore procedure otherwise. Preserve
   workspaces/storage. Record the result and pause customer onboarding until green.

## Model behaviour

Application, Compose and example environment now agree: Fast is
`openai:gpt-5.6-luna`; Thorough is `xai:grok-4.6`; default is Fast. Compose forwards
`XAI_API_KEY`. `/config` exposes allowed options; check the effective running
configuration, since saved environment values take precedence over defaults.

An explicit selected chat model overrides normal task routing. When none is
supplied, `task_routing.py` selects Luna for small mappings, Sol for comparisons,
and Terra for narrative work. Exact create/generate/prepare/draft PMP or project
plan commands, and update/refresh variants, are application actions that queue
the plan workflow without a Pi chat call. The plan worker uses PMP settings.
Tool-internal extraction, tender adjudication, embeddings, thread titles and
other workflow model calls have their own settings; changing the chat selector
does not change them.

## Local preparation limits

The CI image gate builds and tests; it neither pushes images nor deploys. A local
frontend build is not an nginx/container test. If Docker is unavailable, image,
database and proxy smoke remain mandatory gates on a Docker-equipped machine.
