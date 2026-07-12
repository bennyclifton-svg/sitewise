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

function parseJsonText(text: string): unknown {
  if (!text) return undefined;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

async function parseJsonBody(response: Response): Promise<unknown> {
  return parseJsonText(await response.text());
}

function errorDetail(payload: unknown, status: number): string {
  return typeof payload === "object" &&
    payload !== null &&
    "detail" in payload &&
    typeof (payload as { detail: unknown }).detail === "string"
    ? (payload as { detail: string }).detail
    : `Request failed with status ${status}`;
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
      throw new ApiError(errorDetail(payload, response.status), {
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

export type UploadProgressHandler = (loadedBytes: number, totalBytes: number) => void;

/**
 * Multipart upload via XMLHttpRequest: fetch cannot observe request-body
 * progress, so uploads that want a byte-level progress callback go through
 * here. Error semantics match httpRequest.
 */
export function httpUploadRequest<T>(
  url: string,
  options: {
    method?: string;
    headers?: Record<string, string>;
    body: FormData;
    timeoutMs?: number;
    onUploadProgress?: UploadProgressHandler;
  },
): Promise<T> {
  const {
    method = "POST",
    headers = {},
    body,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    onUploadProgress,
  } = options;

  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open(method, url);
    xhr.timeout = timeoutMs;
    for (const [key, value] of Object.entries(headers)) {
      xhr.setRequestHeader(key, value);
    }

    if (onUploadProgress) {
      xhr.upload.addEventListener("progress", (event) => {
        if (event.lengthComputable) {
          onUploadProgress(event.loaded, event.total);
        }
      });
    }

    xhr.addEventListener("load", () => {
      const payload = parseJsonText(xhr.responseText);
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(payload as T);
        return;
      }
      reject(
        new ApiError(errorDetail(payload, xhr.status), {
          kind: "http",
          status: xhr.status,
          body: payload,
        }),
      );
    });
    xhr.addEventListener("timeout", () => {
      reject(new ApiError("Request timed out.", { kind: "timeout" }));
    });
    xhr.addEventListener("abort", () => {
      reject(new ApiError("Request was cancelled.", { kind: "network" }));
    });
    xhr.addEventListener("error", () => {
      reject(
        new ApiError(
          "Could not reach the server. Check your connection or CORS settings.",
          { kind: "network" },
        ),
      );
    });

    xhr.send(body);
  });
}
