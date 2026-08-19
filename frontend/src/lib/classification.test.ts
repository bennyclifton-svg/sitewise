import { describe, expect, it } from "vitest";

import {
  DOCUMENT_CATEGORIES,
  documentCategoryLabel,
  resolveCategorySlug,
} from "@/lib/classification";

describe("documentCategoryLabel", () => {
  it("prefers a real category over folder location", () => {
    expect(
      documentCategoryLabel({
        documentSubject: "heritage",
        category: "Architectural",
      }),
    ).toBe("Heritage");
  });

  it("maps architectural discipline to Architect when subject is none", () => {
    expect(
      documentCategoryLabel({
        documentSubject: "none",
        category: "Mechanical",
      }),
    ).toBe("Mechanical");
    expect(
      resolveCategorySlug({
        documentSubject: "none",
        category: "Architectural",
      }),
    ).toBe("architect");
  });

  it("keeps hydraulic as Hydraulic", () => {
    expect(
      documentCategoryLabel({
        documentSubject: null,
        category: "Hydraulic",
      }),
    ).toBe("Hydraulic");
  });
});

describe("DOCUMENT_CATEGORIES", () => {
  it("includes the short consultant names", () => {
    expect(DOCUMENT_CATEGORIES).toContain("architect");
    expect(DOCUMENT_CATEGORIES).toContain("mechanical");
    expect(DOCUMENT_CATEGORIES).toContain("fire_services");
    expect(DOCUMENT_CATEGORIES).toContain("bca");
    expect(DOCUMENT_CATEGORIES).toContain("civil");
    expect(DOCUMENT_CATEGORIES).toContain("esd");
    expect(DOCUMENT_CATEGORIES).toContain("interior_design");
    expect(DOCUMENT_CATEGORIES).toContain("roof_access");
    expect(DOCUMENT_CATEGORIES).toContain("ecology");
    expect(DOCUMENT_CATEGORIES).toContain("archaeology");
    expect(DOCUMENT_CATEGORIES).not.toContain("civil_stormwater");
    expect(DOCUMENT_CATEGORIES).not.toContain("architecture");
    expect(DOCUMENT_CATEGORIES).not.toContain("services");
  });
});
