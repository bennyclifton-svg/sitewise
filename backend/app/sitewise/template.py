from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class WorkspaceTemplateNode:
    name: str
    description: str
    related_workflows: tuple[str, ...] = ()
    children: tuple["WorkspaceTemplateNode", ...] = field(default_factory=tuple)


SITEWISE_PROJECT_TEMPLATE: tuple[WorkspaceTemplateNode, ...] = (
    WorkspaceTemplateNode(
        name="00-brief-pmp",
        description="Brief, project setup, PMP drafts, assumptions, and authority stack decisions.",
        related_workflows=("create_pmp", "update_pmp"),
    ),
    WorkspaceTemplateNode(
        name="01-cost",
        description="Cost plans, estimates, claims, invoices, variations, and cost reporting.",
        related_workflows=("create_cost_plan", "process_invoices", "process_variations"),
        children=(
            WorkspaceTemplateNode(
                name="invoices",
                description="Incoming invoices and allocation evidence.",
                related_workflows=("process_invoices",),
            ),
            WorkspaceTemplateNode(
                name="variations",
                description="Variation submissions, assessments, and approval records.",
                related_workflows=("process_variations",),
            ),
        ),
    ),
    WorkspaceTemplateNode(
        name="02-consultant",
        description="Consultant scopes, procurement records, coordination notes, and RFP drafts.",
        related_workflows=("consultant_procurement",),
    ),
    WorkspaceTemplateNode(
        name="03-design",
        description="Design documents, RFIs, review notes, consultant outputs, and issue tracking.",
        related_workflows=("design_review", "rfi"),
    ),
    WorkspaceTemplateNode(
        name="04-planning-and-authorities",
        description="Planning pathway, authority correspondence, approvals, certificates, and conditions.",
        related_workflows=("approval_pathway",),
    ),
    WorkspaceTemplateNode(
        name="05-procurement",
        description="Market sounding, tender packages, addenda, submissions, evaluations, and TRR drafts.",
        related_workflows=("rft", "tender_evaluation", "tender_recommendation"),
    ),
    WorkspaceTemplateNode(
        name="06-programme",
        description="Baseline programme, lookaheads, sequencing assumptions, and time-risk evidence.",
        related_workflows=("programme",),
    ),
    WorkspaceTemplateNode(
        name="07-construction",
        description="Site delivery, registers, RFIs, variations, EOTs, progress claims, and meeting records.",
        related_workflows=("risk_register", "rfi", "process_invoices", "process_variations"),
        children=(
            WorkspaceTemplateNode(
                name="01-site-records",
                description="Site diaries, photos, inspections, and delivery records.",
            ),
            WorkspaceTemplateNode(
                name="02-rfis",
                description="Request-for-information register and supporting evidence.",
                related_workflows=("rfi",),
            ),
            WorkspaceTemplateNode(
                name="03-meetings",
                description="Meeting minutes, actions, and decisions.",
                related_workflows=("meeting_minutes",),
            ),
            WorkspaceTemplateNode(
                name="04-progress-claims",
                description="Progress claims, assessments, and payment evidence.",
                related_workflows=("payment_claims",),
            ),
            WorkspaceTemplateNode(
                name="05-eot",
                description="Extension-of-time notices, assessments, and time-impact evidence.",
            ),
            WorkspaceTemplateNode(
                name="06-variations",
                description="Variation submissions, approvals, and cost/time impacts.",
                related_workflows=("process_variations",),
            ),
        ),
    ),
    WorkspaceTemplateNode(
        name="08-reporting",
        description="Project reports, cost reports, dashboards, and recurring status outputs.",
        related_workflows=("project_report", "cost_report"),
    ),
    WorkspaceTemplateNode(
        name="09-handover-dlp",
        description="Handover records, defects liability period evidence, close-out items, and warranties.",
        related_workflows=("handover_closeout",),
    ),
)

