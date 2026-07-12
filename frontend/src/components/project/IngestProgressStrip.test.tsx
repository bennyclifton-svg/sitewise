import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  IngestProgressStrip,
  type IngestUploadProgress,
} from "@/components/project/IngestProgressStrip";

function progress(overrides: Partial<IngestUploadProgress> = {}): IngestUploadProgress {
  return {
    total: 3,
    completed: 1,
    currentFilename: "NexusBuilt.pdf",
    stage: "uploading",
    failedCount: 0,
    ...overrides,
  };
}

describe("IngestProgressStrip", () => {
  it("announces the uploading stage with the filename and batch position", () => {
    render(<IngestProgressStrip progress={progress()} />);
    expect(screen.getByRole("status")).toHaveTextContent("Uploading NexusBuilt.pdf");
    expect(screen.getByRole("status")).toHaveTextContent("2 of 3");
  });

  it("announces the ingesting stage once the bytes are on the server", () => {
    render(<IngestProgressStrip progress={progress({ stage: "ingesting" })} />);
    expect(screen.getByRole("status")).toHaveTextContent("Ingesting NexusBuilt.pdf");
  });

  it("renders a determinate progress bar with the remaining-time estimate", () => {
    render(
      <IngestProgressStrip
        progress={progress()}
        getSnapshot={() => ({ fraction: 0.4, etaSeconds: 42 })}
      />,
    );
    const bar = screen.getByRole("progressbar");
    expect(bar).toHaveAttribute("aria-valuenow", "40");
    expect(screen.getByRole("status")).toHaveTextContent("~40s left");
  });

  it("summarises the batch when every file has settled", () => {
    render(
      <IngestProgressStrip
        progress={progress({ completed: 3, currentFilename: null, stage: null, failedCount: 1 })}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Finished ingesting 3 documents");
    expect(screen.getByRole("status")).toHaveTextContent("1 failed");
  });
});
