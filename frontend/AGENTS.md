# Frontend Agent Notes

This is the React SPA for Clerk. Read `../AGENTS.md` first; universal direction
and code rules live there. This file adds frontend-specific conventions.

## Current Direction

The frontend is extended, not replaced. Clerk already uses the Vercel AI SDK
chat primitives and `DefaultChatTransport`; Phase 4 builds on that path with
tool-call chips, a stop button, session list, artefact cards, and vitest render
tests. Do not vendor Omnigent's store or add Zustand. Use Omnigent only as a
visual reference where the July plans say so.

## Stack

- Vite + React SPA + TypeScript strict
- React Router
- Tailwind CSS
- shadcn/radix UI primitives
- TanStack Query where server state benefits from caching/invalidation
- `@supabase/supabase-js` for browser auth
- Vercel AI SDK (`@ai-sdk/react` + `ai`) for chat streaming
- Vitest/testing-library from Phase 4 onward

No Next.js, SSR, server components, or frontend route handlers.

## Package Manager

Use `pnpm` only. Do not use `npm install` or `yarn add`. The lockfile is
`pnpm-lock.yaml`; `package-lock.json` or `yarn.lock` should be removed if they
appear.

The `.npmrc` minimum release age policy protects against compromised fresh
package releases. Override only for a real need and justify it in the commit
message.

## Dependency Policy

See `../AGENTS.md` for universal policy. Frontend-specific rules:

- HTTP: use native `fetch` through `src/lib/http.ts` and `src/lib/api.ts`. No
  axios, ky, got, superagent, or redaxios.
- Dates: use `Date` and `Intl.DateTimeFormat` unless a real runtime boundary
  needs more.
- Utilities: use native `Array`, `Object`, `Map`, and `Set`. No lodash or ramda.
- State: local React state first; TanStack Query for server state. Do not add
  Zustand/Jotai/Redux for the chat work.
- Forms: native `<form>` and `FormData` first.
- Validation: add runtime schema libraries only at real boundaries.
- UI: use existing shadcn/radix primitives before building custom controls.

## Layout

```text
frontend/
|-- src/
|   |-- components/
|   |   |-- chat/
|   |   |-- project/
|   |   `-- ui/
|   |-- lib/
|   |-- pages/
|   |-- App.tsx
|   |-- main.tsx
|   `-- index.css
|-- index.html
|-- vite.config.ts
|-- tsconfig.json
`-- package.json
```

Use the `@/*` alias consistently.

## Code Style

- TypeScript strict. Avoid `any`; use `unknown` and narrow.
- Small, composable components over clever abstractions.
- One component per file unless a tiny local helper is truly private.
- Tailwind classes inline. Global theme tokens live in `src/index.css`.
- Keep UI text short and action-oriented. Do not add visible instructional copy
  that explains the application to itself.
- For chat UI work, preserve the existing AI-SDK stream contract and keep tool
  chips/artefact cards in component state keyed by message id.

## Configuration

All env reads go through `src/lib/env.ts`, which validates required values at
boot. Never read `import.meta.env.X` directly in components.

Env vars exposed to the browser must use the `VITE_` prefix.

## Backend Integration

- Talk to the Python backend over JSON/SSE.
- The base URL comes from `VITE_API_BASE_URL`.
- Use `api.get/post/put/patch/delete` from `@/lib/api`; it handles base URL,
  Supabase bearer token injection, timeouts, and typed `ApiError`s.
- Never thread auth tokens through component props.
- Chat transport must keep the backend's AI-SDK-compatible SSE vocabulary:
  `start`, `text-start`, `text-delta`, `text-end`, `data-clerk-status`,
  `source-document`, `finish`, and `[DONE]`.

## Testing

Before Phase 4, use manual browser verification plus:

```bash
pnpm tsc --noEmit
pnpm lint
```

Phase 4 introduces vitest, testing-library, jsdom, and focused render tests for
chat/tooling UI. After that point, frontend changes that touch tested surfaces
should add or update vitest coverage.

## Anti-Patterns

- Reading `import.meta.env.X` directly outside `src/lib/env.ts`.
- Importing an HTTP library when `fetch` is enough.
- Adding Zustand/Jotai/Redux for chat state.
- `any` annotations to silence TypeScript.
- Custom CSS modules or styled-components alongside Tailwind.
- Reimplementing a shadcn/radix primitive by hand.
- Reaching for Next.js or any framework that requires a Node server in front of
  the SPA.

