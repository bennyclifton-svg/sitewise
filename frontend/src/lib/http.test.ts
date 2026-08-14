import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, formatErrorDetail, httpRequest } from "@/lib/http";

describe("formatErrorDetail", () => {
  it("returns a string detail unchanged", () => {
    expect(formatErrorDetail({ detail: "Not found." }, 404)).toBe("Not found.");
  });

  it("joins reasons from a structured workflow_capability_conflict detail", () => {
    const payload = {
      detail: {
        code: "workflow_capability_conflict",
        status: "unsupported",
        reasons: ["Cost Plan reference-data coverage is currently residential only."],
        required_fields: [],
      },
    };

    expect(formatErrorDetail(payload, 409)).toBe(
      "Cost Plan reference-data coverage is currently residential only.",
    );
  });

  it("appends required_fields when the structured detail includes them", () => {
    const payload = {
      detail: {
        code: "workflow_capability_conflict",
        status: "needs_input",
        reasons: ["Cost Plan needs additional project inputs."],
        required_fields: ["gfa_sqm", "site_address"],
      },
    };

    expect(formatErrorDetail(payload, 409)).toBe(
      "Cost Plan needs additional project inputs. Missing: gfa_sqm, site_address.",
    );
  });

  it("falls back to a short status string when there are no reasons", () => {
    const payload = { detail: { code: "workflow_capability_conflict", status: "unsupported" } };

    expect(formatErrorDetail(payload, 409)).toBe(
      "Request failed with status 409 (unsupported).",
    );
  });

  it("falls back to a generic message when detail is missing entirely", () => {
    expect(formatErrorDetail({}, 500)).toBe("Request failed with status 500");
  });

  it("joins FastAPI list details from profile validation", () => {
    expect(
      formatErrorDetail(
        { detail: ["scale 'length_km' must be a number", "scale 'stations' must be an integer"] },
        422,
      ),
    ).toBe("scale 'length_km' must be a number scale 'stations' must be an integer");
  });
});

describe("httpRequest error surfacing", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("surfaces structured 409 reasons through ApiError.message", async () => {
    const body = JSON.stringify({
      detail: {
        code: "workflow_capability_conflict",
        status: "unsupported",
        reasons: ["Cost Plan reference-data coverage is currently residential only."],
        required_fields: [],
      },
    });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(body, { status: 409, statusText: "Conflict" }),
      ),
    );

    await expect(httpRequest("https://example.test/api")).rejects.toMatchObject({
      message: "Cost Plan reference-data coverage is currently residential only.",
    });
  });

  it("throws an ApiError instance carrying the parsed body", async () => {
    const body = JSON.stringify({
      detail: {
        code: "workflow_capability_conflict",
        status: "unsupported",
        reasons: ["Cost Plan reference-data coverage is currently residential only."],
        required_fields: [],
      },
    });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(body, { status: 409, statusText: "Conflict" }),
      ),
    );

    try {
      await httpRequest("https://example.test/api");
      expect.unreachable("httpRequest should have thrown");
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      expect((error as ApiError).status).toBe(409);
    }
  });
});
