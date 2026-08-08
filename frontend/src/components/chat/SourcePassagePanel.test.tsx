import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SourcePassagePanel } from "@/components/chat/SourcePassagePanel";

describe("SourcePassagePanel", () => {
  it("shows official web provenance and a safe outbound link", () => {
    render(
      <SourcePassagePanel
        citation={{
          sourceId: "web:abc123",
          chunkId: "abc123",
          documentId: "https://www.legislation.qld.gov.au/current-act",
          title: "Planning Act 2016",
          project: "Queensland Government",
          phase: null,
          sourceType: "web_legislation",
          pageOrSection: "section 8",
          excerpt: "A planning instrument sets out policies.",
          label: "current",
          url: "https://www.legislation.qld.gov.au/current-act",
          publisher: "Queensland Government",
          jurisdiction: "QLD",
          versionStatus: "current",
          effectiveDate: "29 November 2024",
          retrievedAt: "2026-08-08T10:00:00+00:00",
        }}
      />,
    );

    expect(screen.getByText("Web source details")).toBeInTheDocument();
    expect(screen.getByText("Official legislation")).toBeInTheDocument();
    expect(screen.getByText("Queensland Government")).toBeInTheDocument();
    const link = screen.getByRole("link", { name: "Open official source" });
    expect(link).toHaveAttribute(
      "href",
      "https://www.legislation.qld.gov.au/current-act",
    );
    expect(link).toHaveAttribute("rel", "noreferrer noopener");
  });
});
