# Phase 4 Frontend Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire the React SPA to the FastAPI backend with a typed shared API client, then deliver chat thread persistence UI so a signed-in user can create threads, revisit them, and see message history (empty messages OK).

**Architecture:** Two-layer HTTP stack — `http.ts` owns raw `fetch`, timeouts, and `ApiError` discrimination (network/CORS vs HTTP status); `api.ts` layers on base URL + Supabase bearer injection and exposes product calls (`listThreads`, `createThread`, `getMessages`). Pages consume `api` only; no raw `fetch` in components. Chat CRUD UI depends on backend routes from the same phase; implement the API client first so `HomePage` can migrate off its ad-hoc `fetch` immediately.

**Tech Stack:** Vite + React 19 + TypeScript strict, React Router, native `fetch`, `@supabase/supabase-js` (auth token only), Tailwind + shadcn/ui. No axios, no vitest (per `frontend/AGENTS.md`).

**Prerequisite (backend, same phase):** `GET/POST /chat/threads`, `GET /chat/threads/{id}/messages` must exist before the chat UI tasks pass manual verification. Frontend types assume the contract below.

**Expected backend JSON contract:**

```json
// GET /chat/threads → 200
[
  { "id": "uuid", "title": "New chat", "created_at": "ISO-8601", "updated_at": "ISO-8601" }
]

// POST /chat/threads → 201
{ "id": "uuid", "title": "New chat", "created_at": "ISO-8601", "updated_at": "ISO-8601" }

// GET /chat/threads/{id}/messages → 200
[
  { "id": "uuid", "thread_id": "uuid", "role": "user", "content": "...", "created_at": "ISO-8601" }
]
```

**CORS note:** Backend already defaults `ALLOWED_ORIGINS` to `http://localhost:5173,http://localhost:5174` in `backend/app/config.py` and `backend/.env.example`. Local `backend/.env` already includes `http://localhost:5173`. Phase 4 CORS work is **verify**, not build.

---

## Task 1: `src/lib/http.ts` — fetch wrapper + `ApiError`

**Files:**
- Create: `frontend/src/lib/http.ts`

**Step 1: Create `ApiError` class**

```typescript
export type ApiErrorKind = "network" | "timeout" | "http";

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status?: number;
  readonly body?: unknown;

  constructor(
    message: string,
    options: { kind: ApiErrorKind; status?: number; body?: unknown; cause?: unknown },
  ) {
    super(message, { cause: options.cause });
    this.name = "ApiError";
    this.kind = options.kind;
    this.status = options.status;
    this.body = options.body;
  }

  get isNetworkError(): boolean {
    return this.kind === "network" || this.kind === "timeout";
  }
}
```

**Step 2: Implement `httpRequest`**

```typescript
const DEFAULT_TIMEOUT_MS = 30_000;

export type HttpRequestOptions = {
  method?: string;
  headers?: HeadersInit;
  body?: BodyInit | null;
  timeoutMs?: number;
  signal?: AbortSignal;
};

async function parseJsonBody(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) return undefined;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

export async function httpRequest<T>(
  url: string,
  options: HttpRequestOptions = {},
): Promise<T> {
  const { method = "GET", headers, body = null, timeoutMs = DEFAULT_TIMEOUT_MS, signal } =
    options;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const onExternalAbort = () => controller.abort();
  signal?.addEventListener("abort", onExternalAbort, { once: true });

  try {
    const response = await fetch(url, {
      method,
      headers,
      body,
      signal: controller.signal,
    });

    const payload = await parseJsonBody(response);

    if (!response.ok) {
      const detail =
        typeof payload === "object" &&
        payload !== null &&
        "detail" in payload &&
        typeof (payload as { detail: unknown }).detail === "string"
          ? (payload as { detail: string }).detail
          : `Request failed with status ${response.status}`;

      throw new ApiError(detail, {
        kind: "http",
        status: response.status,
        body: payload,
      });
    }

    return payload as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;

    if (error instanceof DOMException && error.name === "AbortError") {
      if (signal?.aborted) {
        throw new ApiError("Request was cancelled.", {
          kind: "network",
          cause: error,
        });
      }
      throw new ApiError("Request timed out.", { kind: "timeout", cause: error });
    }

    throw new ApiError("Could not reach the server. Check your connection or CORS settings.", {
      kind: "network",
      cause: error,
    });
  } finally {
    clearTimeout(timeoutId);
    signal?.removeEventListener("abort", onExternalAbort);
  }
}
```

**Step 3: Type-check**

Run: `cd frontend && pnpm tsc --noEmit`
Expected: PASS (no import errors)

**Step 4: Lint**

Run: `cd frontend && pnpm lint`
Expected: PASS

---

## Task 2: `src/lib/api.ts` — authenticated client + chat calls

**Files:**
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/types/chat.ts` (shared response types)

**Step 1: Define chat types**

```typescript
// frontend/src/lib/types/chat.ts
export type ChatThread = {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
};

export type ChatMessage = {
  id: string;
  thread_id: string;
  role: string;
  content: string;
  created_at: string;
};
```

**Step 2: Implement `api` singleton**

```typescript
import { getAccessToken } from "@/lib/auth";
import { env } from "@/lib/env";
import { ApiError, httpRequest } from "@/lib/http";
import type { ChatMessage, ChatThread } from "@/lib/types/chat";

type JsonBody = Record<string, unknown> | unknown[] | null;

type ApiRequestOptions = {
  method?: string;
  body?: JsonBody;
  timeoutMs?: number;
  auth?: boolean;
};

async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const { method = "GET", body, timeoutMs, auth = true } = options;

  const headers: Record<string, string> = {
    Accept: "application/json",
  };

  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  if (auth) {
    const token = await getAccessToken();
    if (!token) {
      throw new ApiError("Not signed in.", { kind: "http", status: 401 });
    }
    headers.Authorization = `Bearer ${token}`;
  }

  const url = `${env.apiBaseUrl.replace(/\/$/, "")}${path.startsWith("/") ? path : `/${path}`}`;

  return httpRequest<T>(url, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    timeoutMs,
  });
}

export const api = {
  get: <T>(path: string, options?: Omit<ApiRequestOptions, "method" | "body">) =>
    apiRequest<T>(path, { ...options, method: "GET" }),

  post: <T>(path: string, body?: JsonBody, options?: Omit<ApiRequestOptions, "method">) =>
    apiRequest<T>(path, { ...options, method: "POST", body }),

  put: <T>(path: string, body?: JsonBody, options?: Omit<ApiRequestOptions, "method">) =>
    apiRequest<T>(path, { ...options, method: "PUT", body }),

  patch: <T>(path: string, body?: JsonBody, options?: Omit<ApiRequestOptions, "method">) =>
    apiRequest<T>(path, { ...options, method: "PATCH", body }),

  delete: <T>(path: string, options?: Omit<ApiRequestOptions, "method" | "body">) =>
    apiRequest<T>(path, { ...options, method: "DELETE" }),

  // Product-level chat helpers (Phase 4)
  listThreads: () => api.get<ChatThread[]>("/chat/threads"),

  createThread: (title?: string) =>
    api.post<ChatThread>("/chat/threads", title ? { title } : {}),

  getThreadMessages: (threadId: string) =>
    api.get<ChatMessage[]>(`/chat/threads/${threadId}/messages`),
};
```

**Step 3: Type-check + lint**

Run: `cd frontend && pnpm tsc --noEmit && pnpm lint`
Expected: PASS

---

## Task 3: Migrate `HomePage` auth smoke test to `api`

**Files:**
- Modify: `frontend/src/pages/HomePage.tsx`

**Step 1: Replace raw `fetch` with `api.get`**

Remove imports of `getAccessToken` and `env`. Import `api` and `ApiError`:

```typescript
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
```

Replace `handleCheckBackendAuth` body:

```typescript
async function handleCheckBackendAuth() {
  setIsCheckingAuth(true);
  setMeError(null);
  setMe(null);

  try {
    const payload = await api.get<MeResponse>("/auth/me");
    setMe(payload);
  } catch (error) {
    if (error instanceof ApiError) {
      if (error.isNetworkError) {
        setMeError("Could not reach the backend. Is it running on port 8000?");
      } else if (error.status === 401) {
        setMeError("Session expired or invalid. Sign in again.");
      } else {
        setMeError(error.message);
      }
    } else {
      setMeError("Unexpected error checking backend auth.");
    }
  } finally {
    setIsCheckingAuth(false);
  }
}
```

**Step 2: Manual verify**

1. Start backend: `cd backend && uv run uvicorn app.main:app --reload`
2. Start frontend: `cd frontend && pnpm dev`
3. Sign in → click **Verify backend auth** → should show email + id
4. Stop backend → click again → should show network/CORS message (not generic HTTP text)

**Step 3: Type-check + lint**

Run: `cd frontend && pnpm tsc --noEmit && pnpm lint`
Expected: PASS

---

## Task 4: Verify CORS configuration

**Files:**
- Verify: `backend/app/config.py` (default includes `http://localhost:5173`)
- Verify: `backend/.env` (`ALLOWED_ORIGINS` includes `http://localhost:5173`)
- Verify: `frontend/.env` (`VITE_API_BASE_URL=http://localhost:8000`)

**Step 1: Confirm backend CORS middleware**

`backend/app/main.py` already wires `CORSMiddleware` with `settings.allowed_origins_list`. No code change expected.

**Step 2: Browser network check**

1. With both servers running, open DevTools → Network
2. Trigger **Verify backend auth** from `HomePage`
3. Confirm response has `Access-Control-Allow-Origin: http://localhost:5173` (or the active Vite origin)
4. Confirm no CORS console errors

**Step 3: Mark todoist item**

Update `docs/todoist.md` Phase 4 CORS checkbox when verified.

---

## Task 5: Thread list + new chat on `HomePage`

**Depends on:** Backend `GET /chat/threads` and `POST /chat/threads`.

**Files:**
- Modify: `frontend/src/pages/HomePage.tsx`
- Optional: `frontend/src/components/ThreadList.tsx` (extract if `HomePage` exceeds ~120 lines)

**Step 1: Load threads on mount**

```typescript
const [threads, setThreads] = useState<ChatThread[]>([]);
const [threadsLoading, setThreadsLoading] = useState(true);
const [threadsError, setThreadsError] = useState<string | null>(null);

useEffect(() => {
  let cancelled = false;

  async function loadThreads() {
    setThreadsLoading(true);
    setThreadsError(null);
    try {
      const data = await api.listThreads();
      if (!cancelled) setThreads(data);
    } catch (error) {
      if (!cancelled) {
        setThreadsError(
          error instanceof ApiError ? error.message : "Could not load conversations.",
        );
      }
    } finally {
      if (!cancelled) setThreadsLoading(false);
    }
  }

  void loadThreads();
  return () => {
    cancelled = true;
  };
}, []);
```

**Step 2: New chat button**

```typescript
import { useNavigate } from "react-router-dom";

const navigate = useNavigate();
const [isCreating, setIsCreating] = useState(false);

async function handleNewChat() {
  setIsCreating(true);
  try {
    const thread = await api.createThread();
    navigate(`/chat/${thread.id}`);
  } catch (error) {
    setThreadsError(
      error instanceof ApiError ? error.message : "Could not create a new conversation.",
    );
  } finally {
    setIsCreating(false);
  }
}
```

**Step 3: Render thread list**

Replace the "Chat placeholder" card with:
- **New chat** primary button (`handleNewChat`, disabled while `isCreating`)
- List of threads as `Link` items to `/chat/{id}`, showing `title ?? "Untitled chat"` and formatted `updated_at` via `Intl.DateTimeFormat`
- Empty state: "No conversations yet. Start one above."
- Loading + error states with `role="alert"` on errors

Remove the hard-coded `/chat/demo-thread` sample link.

**Step 4: Manual verify**

1. Sign in → **New chat** → lands on `/chat/<uuid>`
2. Navigate home → thread appears in list
3. Refresh browser → thread still listed

---

## Task 6: Load messages on `ChatPage`

**Depends on:** Backend `GET /chat/threads/{id}/messages` (+ ownership enforcement).

**Files:**
- Modify: `frontend/src/pages/ChatPage.tsx`

**Step 1: Fetch messages when `threadId` changes**

```typescript
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import type { ChatMessage } from "@/lib/types/chat";

const [messages, setMessages] = useState<ChatMessage[]>([]);
const [messagesLoading, setMessagesLoading] = useState(true);
const [messagesError, setMessagesError] = useState<string | null>(null);

useEffect(() => {
  if (!threadId) return;

  let cancelled = false;

  async function loadMessages() {
    setMessagesLoading(true);
    setMessagesError(null);
    try {
      const data = await api.getThreadMessages(threadId);
      if (!cancelled) setMessages(data);
    } catch (error) {
      if (!cancelled) {
        if (error instanceof ApiError && error.status === 403) {
          setMessagesError("You do not have access to this conversation.");
        } else if (error instanceof ApiError && error.status === 404) {
          setMessagesError("Conversation not found.");
        } else {
          setMessagesError(
            error instanceof ApiError ? error.message : "Could not load messages.",
          );
        }
      }
    } finally {
      if (!cancelled) setMessagesLoading(false);
    }
  }

  void loadMessages();
  return () => {
    cancelled = true;
  };
}, [threadId]);
```

**Step 2: Render message history (read-only shell)**

Replace placeholder card content with:
- Loading state
- Error state (403/404/network distinct copy)
- Empty state: "No messages yet. Streaming arrives in Phase 5."
- Non-empty: simple list — role badge + `content` text, ordered by `created_at`

No chat input yet (Phase 5).

**Step 3: Manual verify**

1. Open a thread created in Task 5 → empty state shown
2. (Optional, once backend can seed messages) refresh → messages render
3. Manually navigate to another user's thread UUID → 403 message

---

## Task 7: Phase 4 completion checklist

**Files:**
- Modify: `docs/todoist.md` — check off Phase 4 frontend items

**Step 1: Full smoke path**

1. Sign in
2. Create thread → `/chat/:id`
3. See empty messages
4. Return home → thread in list
5. Re-open thread → still loads
6. Sign out → auth guard redirects to `/login`

**Step 2: Static checks**

Run: `cd frontend && pnpm tsc --noEmit && pnpm lint && pnpm build`
Expected: all PASS

**Step 3: Update todoist**

Check:
- `src/lib/http.ts`
- `src/lib/api.ts`
- CORS verified
- Thread list page
- New chat button
- Load initial messages

---

## Dependency order (recommended)

```text
Task 1 (http.ts)
    ↓
Task 2 (api.ts)
    ↓
Task 3 (HomePage auth migration) + Task 4 (CORS verify)  ← parallel
    ↓
[Backend chat CRUD routes must land here]
    ↓
Task 5 (thread list) + Task 6 (ChatPage messages)  ← parallel
    ↓
Task 7 (checklist)
```

## Out of scope (Phase 5+)

- Vercel AI SDK / `useChat`
- `src/components/chat/*` streaming UI
- `POST /chat/stream`
- Message composer / send

## Error UX reference

| Condition | `ApiError` signal | User-facing copy |
|-----------|-------------------|------------------|
| Backend down / CORS | `isNetworkError === true` | "Could not reach the backend…" |
| Timeout | `kind === "timeout"` | "Request timed out." |
| Expired session | `status === 401` | "Session expired…" |
| Wrong thread owner | `status === 403` | "You do not have access…" |
| Missing thread | `status === 404` | "Conversation not found." |
| Other HTTP | `kind === "http"` | `error.message` from backend `detail` |
