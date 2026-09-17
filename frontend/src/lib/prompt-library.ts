export type SavedPrompt = { id: string; title: string; text: string };
export type PromptLibrary = { version: number; prompts: SavedPrompt[] | null };

export const STARTER_PROMPTS: SavedPrompt[] = [
  {
    id: "project-management-plan",
    title: "Project management plan",
    text: "Turn the brief and reports into a coordinated project plan. Reconcile evidence, flag conflicts, and populate scope, responsibilities, approvals, procurement, risks and decisions. Convert gaps into owned actions. Save the plan and flag critical decisions.",
  },
  {
    id: "cost-plan",
    title: "Cost plan",
    text: "Build the cost plan from the PMP, advice and proposals. Cover fees, approvals, construction, client costs and contingency. Keep quotes, estimates and unpriced scope distinct. Check forecast against budget and recommend closing any shortfall without changing scope.",
  },
  {
    id: "programme",
    title: "Programme",
    text: "Build a linked programme to the target date. Cover appointments, design, decisions, approvals, tendering and construction. Mark the critical path and latest decision dates. Separate supported durations from assumptions. If unrealistic, explain why and compare recovery.",
  },
  {
    id: "consultant-procurement",
    title: "Consultant procurement",
    text: "Prepare coordinated RFPs for architecture, planning, structural, civil/stormwater and building services from the plan. Set scopes, deliverables, interfaces, exclusions and dates. Resolve evidence-supported gaps. Save the five drafts, update the register, and flag decisions before issue.",
  },
  {
    id: "appointment",
    title: "Appointment",
    text: "Record the civil engineer’s appointment from the signed letter against their proposal and RFP. Note changes to scope, exclusions, fees and dates. Update the appointment, fee, programme and PMP. Flag discrepancies needing a decision.",
  },
  {
    id: "trade-procurement",
    title: "Trade procurement",
    text: "Draft a civil works tender pack from current scope, drawings, specs and deliverables. Check revisions, interfaces and gaps. Research three local firms, showing suitability evidence and separating verified from unknown. Save the pack and align tender dates.",
  },
  {
    id: "tender-comparison",
    title: "Tender comparison",
    text: "Compare the three builder tenders on the same scope. Reconcile exclusions, qualifications, provisional sums, alternatives and programme. Separate submitted prices from like-for-like adjustments; leave unsupported items unpriced. Explain whether the lowest remains preferable. Save the comparison and draft clarifications.",
  },
  {
    id: "document-issue",
    title: "Document issue",
    text: "Find current drawings for the next package. Check revisions, superseded documents and conflicts. Prepare a transmittal with numbers, revisions, recipient and purpose. Save the draft and record outstanding coordination.",
  },
  {
    id: "invoice-processing",
    title: "Invoice processing",
    text: "Process this month’s invoices against appointments, contracts and the cost plan. Check duplicates, previous claims, arithmetic errors and over-commitment. Allocate supported invoices, update the register and claimed-to-date, and show remaining commitments and forecast. Keep uncertain or disputed amounts visible.",
  },
  {
    id: "connected-change",
    title: "Connected change",
    text: "Assess revised drawings, consultant advice and cost and time as one change. Trace affected scope, appointments, procurement and construction. Update the forecast, linked programme and PMP where evidence supports it; keep the approved baseline. Prepare procurement amendments and a revised transmittal. Report unresolved impacts and decisions.",
  },
];
