import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { FirmSubmissionLinks } from "./FirmSubmissionLinks";
import type { EvidencePreview, ProcurementStrategyCandidate } from "@/lib/types/project";

const candidate: ProcurementStrategyCandidate = { id: "firm", slot: 1, company_name: "Alder", website_url: null, location_text: null, source_url: null, source_title: null, researched_at: null, submission_files: [] };
const evidence = ["fee", "programme"].map((id) => ({ id, workspace_file_id: `file-${id}`, filename: `${id}.pdf` })) as EvidencePreview[];

describe("FirmSubmissionLinks", () => {
  it("links all selected canonical files to one firm", async () => {
    const onApply = vi.fn().mockResolvedValue(undefined);
    render(<FirmSubmissionLinks candidate={candidate} rowId="row" evidence={evidence} selectedIds={new Set(["fee", "programme"])} disabled={false} onApply={onApply} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Quote files for Alder" }));
    await user.click(screen.getByRole("menuitem", { name: "Link 2 selected files" }));
    expect(onApply).toHaveBeenCalledWith([{ operation: "LINK_CANDIDATE_FILES", row_id: "row", candidate_id: "firm", workspace_file_ids: ["file-fee", "file-programme"] }]);
  });

  it("shows receipt and permits unlinking an existing attachment", async () => {
    const onApply = vi.fn().mockResolvedValue(undefined);
    render(<FirmSubmissionLinks candidate={{ ...candidate, submission_files: [{ workspace_file_id: "file-fee", filename: "fee.pdf", workspace_path: "quotes/fee.pdf" }] }} rowId="row" evidence={evidence} selectedIds={new Set()} disabled={false} onApply={onApply} />);
    expect(screen.getByText("1 file")).toBeTruthy();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Quote files for Alder" }));
    await user.click(screen.getByRole("menuitemcheckbox", { name: "fee.pdf" }));
    expect(onApply).toHaveBeenCalledWith([{ operation: "UNLINK_CANDIDATE_FILES", row_id: "row", candidate_id: "firm", workspace_file_ids: ["file-fee"] }]);
  });
});
