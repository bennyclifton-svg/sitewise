export type SavedPrompt = { id: string; title: string; text: string };
export type PromptLibrary = { version: number; prompts: SavedPrompt[] | null };

export const STARTER_PROMPTS: SavedPrompt[] = [
  {
    id: "project-management-plan",
    title: "Project management plan",
    text: "Take this project from its uploaded brief and consultant reports to a coordinated project management plan. Reconcile the evidence with the project profile and identify conflicting requirements. Populate the scope, responsibilities, approvals, procurement approach, risks and decision points. Turn missing information into specific actions with proposed owners and required-by stages. Save the plan and identify the unresolved decisions that could most affect cost, time or delivery.",
  },
  {
    id: "cost-plan",
    title: "Cost plan",
    text: "Build the project cost plan from the project management plan, available cost advice and received proposals. Reconcile overlapping scope and include consultant fees, approvals, construction, client costs and contingency. Distinguish quoted amounts, estimates and unpriced scope, retaining the source and basis of each. Check the forecast against the project budget, update the PMP’s cost risks and actions, and recommend ways to address any shortfall without silently changing the agreed scope.",
  },
  {
    id: "programme",
    title: "Programme",
    text: "Build a linked delivery programme from the project plan and procurement approach, working towards the target completion date. Include consultant appointments, design deliverables, client decisions, approvals, tendering and construction. Identify the critical path and latest decision dates, and distinguish supported durations from planning assumptions. If the target is unrealistic, explain the constraint and compare recovery options. Save the programme and reconcile its milestones and responsibilities with the PMP.",
  },
  {
    id: "consultant-procurement",
    title: "Consultant procurement",
    text: "Use the project plan, cost allowances and programme to prepare coordinated RFPs for architecture, planning, structural, civil/stormwater and building services. Define project-specific scopes, deliverables, interfaces, exclusions, submission requirements and delivery dates. Identify gaps or overlaps between disciplines and resolve what the project evidence supports. Save all five drafts in the repository, update the procurement strategy and register, and flag decisions needed before issue.",
  },
  {
    id: "appointment",
    title: "Appointment",
    text: "Record the civil engineer’s appointment from the signed letter and reconcile it against their proposal and our RFP. Identify changes to scope, exclusions, fees, payment stages and deliverable dates. Update the appointment record, committed fee, procurement status, programme obligations and PMP responsibilities. Preserve any remaining unappointed scope or allowance, and surface discrepancies that need a decision.",
  },
  {
    id: "trade-procurement",
    title: "Trade procurement",
    text: "Prepare a draft civil works tender pack from the current project scope, drawings, specifications and consultant deliverables. Check document revisions, scope interfaces and missing information before assembling it. Research three suitable local firms, show the evidence for their suitability and distinguish verified facts from unknown capacity or availability. Save the pack, populate the procurement register and align proposed tender dates with the programme. Keep the pack ready for review before issue.",
  },
  {
    id: "tender-comparison",
    title: "Tender comparison",
    text: "Compare the three builder tenders against the same current scope and tender documents. Reconcile exclusions, qualifications, provisional sums, alternatives and programme differences. Show submitted prices separately from like-for-like adjustments, using documented amounts and leaving unsupported adjustments unpriced. Explain what drives the differences and whether the apparent lowest price remains preferable. Save the comparison, draft bidder-specific clarification questions, and show the cost and programme implications of the recommended next steps.",
  },
  {
    id: "document-issue",
    title: "Document issue",
    text: "Find the current drawings across all disciplines required for the head contractor’s next construction package. Check revision and issue status, identify superseded documents and flag missing or conflicting information. Prepare a transmittal with the exact document numbers, revisions, recipient and issue purpose. Save the draft and record outstanding coordination actions against the relevant programme activity.",
  },
  {
    id: "invoice-processing",
    title: "Invoice processing",
    text: "Process this month’s uploaded invoices against the appointments, contracts and cost plan. Check for duplicates, previous claims, arithmetic discrepancies and amounts exceeding the available commitment. Allocate supported invoices, update the invoice register and claimed-to-date totals, and show the effect on remaining commitments and the forecast where supported. Keep uncertain allocations and disputed amounts visible for review, with a clear explanation of what is needed to resolve each exception.",
  },
  {
    id: "connected-change",
    title: "Connected change",
    text: "Assess the revised drawings, supporting consultant advice and documented cost and time assessments as one project change. Trace the affected scope, appointments, procurement packages and construction activities. Update the forecast, linked programme and relevant PMP sections where the evidence supports the change, preserving the approved baseline and distinguishing forecast impacts from approved variations. Prepare any necessary procurement amendments and a revised transmittal draft. Report the before-and-after position, unresolved impacts and decisions required, then check that all affected project records agree.",
  },
];
