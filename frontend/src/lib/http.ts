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
  const {
    method = "GET",
    headers,
    body = null,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    signal,
  } = options;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const onExternalAbort = () => controller.abort();
  signal?.addEventListener("abort", onExternalAbort, { once: true });

  try {
    const response = await fetch(url, {
      method,
      headers,
      ...(body !== undefined && body !== null ? { body } : {}),
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

    throw new ApiError(
      "Could not reach the server. Check your connection or CORS settings.",
      {
        kind: "network",
        cause: error,
      },
    );
  } finally {
    clearTimeout(timeoutId);
    signal?.removeEventListener("abort", onExternalAbort);
  }
}
