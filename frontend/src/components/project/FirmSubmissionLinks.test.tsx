import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/lib/api";

import { FirmSubmissionLinks } from "./FirmSubmissionLinks";
import type { EvidencePreview, ProcurementStrategyCandidate } from "@/lib/types/project";

const candidate: ProcurementStrategyCandidate = { id: "firm", slot: 1, company_name: "Alder", website_url: null, location_text: null, source_url: null, source_title: null, researched_at: null, submission_files: [] };
const evidence = ["fee", "programme"].map((id) => ({ id, workspace_file_id: `file-${id}`, filename: `${id}.pdf` })) as EvidencePreview[];
const cell = { projectId: "project", slot: 1, cellLabel: "Structural, Firm 1" };

afterEach(() => vi.restoreAllMocks());

describe("FirmSubmissionLinks", () => {
  it("links all selected canonical files to one firm", async () => {
    const onApply = vi.fn().mockResolvedValue(undefined);
    render(<FirmSubmissionLinks {...cell} candidate={candidate} rowId="row" evidence={evidence} selectedIds={new Set(["fee", "programme"])} disabled={false} onApply={onApply} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Quote files for Alder" }));
    await user.click(screen.getByRole("menuitem", { name: "Link 2 selected files" }));
    expect(onApply).toHaveBeenCalledWith([{ operation: "LINK_CANDIDATE_FILES", row_id: "row", candidate_id: "firm", workspace_file_ids: ["file-fee", "file-programme"] }]);
  });

  it("shows receipt and permits unlinking an existing attachment", async () => {
    const onApply = vi.fn().mockResolvedValue(undefined);
    render(<FirmSubmissionLinks {...cell} candidate={{ ...candidate, submission_files: [{ workspace_file_id: "file-fee", filename: "fee.pdf", workspace_path: "quotes/fee.pdf" }] }} rowId="row" evidence={evidence} selectedIds={new Set()} disabled={false} onApply={onApply} />);
    expect(screen.getByRole("button", { name: "Quote files for Alder" })).toHaveTextContent("1");
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Quote files for Alder" }));
    await user.click(screen.getByRole("menuitemcheckbox", { name: "fee.pdf" }));
    expect(onApply).toHaveBeenCalledWith([{ operation: "UNLINK_CANDIDATE_FILES", row_id: "row", candidate_id: "firm", workspace_file_ids: ["file-fee"] }]);
  });

  it("identifies and adds a firm when a document is linked to an empty cell", async () => {
    const identify = vi.spyOn(api, "identifySubmissionFirm").mockResolvedValue({ status: "identified", company_name: "Alder Engineers", message: null });
    const onApply = vi.fn().mockResolvedValue(undefined);
    render(<FirmSubmissionLinks {...cell} rowId="row" evidence={evidence} selectedIds={new Set()} disabled={false} onApply={onApply} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Link documents for Structural, Firm 1" }));
    await user.click(screen.getByRole("menuitemcheckbox", { name: "fee.pdf" }));
    expect(identify).toHaveBeenCalledWith("project", ["file-fee"]);
    expect(onApply).toHaveBeenCalledWith([{ operation: "CREATE_CANDIDATE_FROM_FILES", row_id: "row", slot: 1, company_name: "Alder Engineers", workspace_file_ids: ["file-fee"] }]);
  });

  it("retains selected files for manual naming when the issuer is unclear", async () => {
    vi.spyOn(api, "identifySubmissionFirm").mockResolvedValue({ status: "needs_name", company_name: null, message: "Enter the submitting firm." });
    const onApply = vi.fn().mockRejectedValueOnce(new Error("Failed")).mockResolvedValue(undefined);
    render(<FirmSubmissionLinks {...cell} rowId="row" evidence={evidence} selectedIds={new Set(["fee", "programme"])} disabled={false} onApply={onApply} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Link documents for Structural, Firm 1" }));
    await user.click(screen.getByRole("menuitem", { name: "Link 2 selected files" }));
    expect(onApply).not.toHaveBeenCalled();
    await user.type(screen.getByRole("textbox", { name: "Firm name for Structural, Firm 1" }), "Alder");
    await user.click(screen.getByRole("button", { name: "Add firm and link" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Could not save");
    expect(screen.getByRole("textbox")).toHaveValue("Alder");
    await user.click(screen.getByRole("button", { name: "Add firm and link" }));
    expect(onApply).toHaveBeenLastCalledWith([{ operation: "CREATE_CANDIDATE_FROM_FILES", row_id: "row", slot: 1, company_name: "Alder", workspace_file_ids: ["file-fee", "file-programme"] }]);
    expect(screen.queryByRole("textbox")).toBeNull();
  });

  it("does not group documents identified as different firms", async () => {
    vi.spyOn(api, "identifySubmissionFirm").mockResolvedValue({ status: "different_firms", company_name: null, message: "Select documents for one firm at a time." });
    const onApply = vi.fn();
    render(<FirmSubmissionLinks {...cell} rowId="row" evidence={evidence} selectedIds={new Set(["fee", "programme"])} disabled={false} onApply={onApply} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Link documents for Structural, Firm 1" }));
    await user.click(screen.getByRole("menuitem", { name: "Link 2 selected files" }));
    expect(screen.getByRole("alert")).toHaveTextContent("one firm at a time");
    expect(onApply).not.toHaveBeenCalled();
    expect(screen.queryByRole("textbox")).toBeNull();
  });

  it("shows identification progress and prevents a second submission", async () => {
    let finish!: (value: Awaited<ReturnType<typeof api.identifySubmissionFirm>>) => void;
    vi.spyOn(api, "identifySubmissionFirm").mockImplementation(() => new Promise((resolve) => { finish = resolve; }));
    render(<FirmSubmissionLinks {...cell} rowId="row" evidence={evidence} selectedIds={new Set(["fee"])} disabled={false} onApply={vi.fn()} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Link documents for Structural, Firm 1" }));
    await user.click(screen.getByRole("menuitem", { name: "Link 1 selected file" }));
    expect(screen.getByRole("status")).toHaveTextContent("Identifying firm");
    expect(screen.getByRole("button", { name: "Link documents for Structural, Firm 1" })).toBeDisabled();
    finish({ status: "needs_name", company_name: null, message: "Enter name" });
    await screen.findByRole("textbox");
  });
});
