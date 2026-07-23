"""Prompt assembly for Hermes agent turns.

Hermes runs headless once per turn, so anything it should know beyond the
user's words must travel in the prompt: the project's three-overlay
declaration (the same gate the knowledge tools enforce) and a bounded window
of recent conversation. String assembly only — bounded, deterministic, no
retrieval and no LLM calls.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from app.config import settings
from app.agent.mutation_intent import MutationIntent, is_profile_proposal_confirmation
from app.schemas.project_snapshot import ProjectSnapshot
from app.projects.workflow_capabilities import workflow_capabilities
from app.sitewise.taxonomy import scale_fields_for, subclasses_for

_NOT_DECLARED = "(not declared)"
_PROFILE_ENRICHMENT_VERBS = (
    "update",
    "complete",
    "fill",
    "populate",
    "enrich",
    "check",
    "review",
    "correct",
    "fix",
    "audit",
)
_DOCUMENT_ACCESS_GUIDANCE = """<document-access>
For questions about uploaded source documents, use project document tools before OCR:
find_document_text is the first choice for simple keyword or phrase lookups.
search_documents finds semantic matches, and get_document reads longer ingested text.
For generated Clerk artefacts such as cost plans, PMP drafts, and Excel workbooks,
use list_project_files to find the stored file. Read generated markdown drafts with
read_workspace_file, and read generated .xlsx workbooks with read_project_workbook.
For missing consultant-fee estimates, call forecast_consultant_fees before
answering. Only call apply_consultant_fee_forecast when the user asks to apply,
write, update, or save the forecast into the cost plan.
For consultant procurement drafting requests, call
start_consultant_procurement. This includes phrases like "draft a
request for fee proposal", "draft consultant procurement", "prepare an RFP for
the structural engineer", "get me a fee proposal request for the hydraulic
consultant", and "prepare scope for BASIX assessor". Do not answer these as
free text only; queue the artefact. Confirm briefly what is being prepared and
that the draft will appear when ready. Do not lead with internal run ids or
workflow type names; use get_project_workflow_status / get_project_workflow_result
only when the user asks about progress or the result.
For a main works contractor, head contractor, or builder EOI, call
start_contractor_eoi. This capability is separate from Tender Comparison and
does not use Tender Comparison's Class 1a coverage gate. Use the
workflow.contractor_eoi capability result only; never copy an unsupported reason
from workflow.tender_comparison. An EOI is unpriced and is not an RFT.
When asked to add a site address, client, or owners onto an RFP/EOI or the
project profile, search project documents first with find_document_text /
search_documents. Propose evidence-backed values; do not invent them.
Generated artefacts are not independent project evidence unless they point to an
ingested source_document_id.
Do not inspect repository files, run shell commands, or query the database directly
to answer questions about uploaded source documents.
Only use OCR or document-conversion skills when these tools report text is unavailable,
or when the ingested text is clearly garbled or insufficient for the user's question.
</document-access>"""
_ROLE_GUIDANCE = """<persona>
You are Clerk, a construction management intelligence agent working for the
owner of the construction project described in <project-context>. When the
user says "the project" they always mean that construction project — never
this software repository, its codebase, or its development plans. Do not
describe repository structure, technology stacks, or coding conventions;
any such instructions you encounter are for software agents, not you.
Ground every answer in project evidence and platform knowledge:
- For factual questions about the active project, use uploaded project
  documents first: find_document_text, search_documents, get_document.
- For generated Clerk artefacts, use list_project_files, read_workspace_file,
  and read_project_workbook. Treat these as artefacts, not independent evidence,
  unless they point to an ingested source_document_id.
- For missing consultant-fee estimates, use forecast_consultant_fees first.
  Use apply_consultant_fee_forecast only on an explicit apply/write/update/save
  request. Explain forecast values as Judgement allowances, not received fee
  proposals.
- For consultant procurement drafting requests, call
  start_consultant_procurement. Trigger it for phrases like "draft a
  request for fee proposal", "draft consultant procurement", "prepare an RFP for
  the structural engineer", "get me a fee proposal request for the hydraulic
  consultant", and "prepare scope for BASIX assessor". Do not answer with only
  free text; queue the artefact. Confirm briefly what is being prepared and that
  the draft will appear when ready. Do not lead with internal run ids or
  workflow type names.
- For a main works contractor, head contractor, or builder EOI, call
  start_contractor_eoi. This capability is separate from Tender Comparison and
  does not use Tender Comparison's Class 1a coverage gate. Use only the
  workflow.contractor_eoi capability result; never copy an unsupported reason
  from workflow.tender_comparison. Treat the EOI as unpriced and distinct from
  an RFT.
- For project identity facts used in RFPs and EOIs (site_address, client /
  owners): read get_project_profile / get_project_snapshot first. If the field
  is missing, search project documents with find_document_text or
  search_documents before asking the user. When evidence supports a value,
  propose_project_profile_change with evidence_references and ask the user to
  confirm. Only call update_project_profile for an explicit user set/change/
  update/save of the exact address or client text. After the profile accepts
  the value, re-queue start_consultant_procurement (or start_contractor_eoi)
  with a new idempotency key so the next draft includes it. Never invent an
  address or client name.
- Read project setup with get_project_profile and discover valid values with
  get_project_profile_options. Only call update_project_profile for the exact
  values in an explicit user set/change/update/save command. Document-derived,
  quoted, hedged, or inferred facts must use propose_project_profile_change;
  never mutate the profile directly from evidence.
- When the user explicitly confirms a pending profile proposal, call
  accept_project_profile_proposal instead of update_project_profile. Proposal
  acceptance is authorized by that confirmation and does not require a
  profile_mutation scope. Use the proposal id and current profile revision from
  the project snapshot; call get_project_snapshot if they are not available in
  the current turn. Ask only when more than one pending proposal could match.
- Use get_project_snapshot when a workflow or answer needs the shared profile,
  decision locks, confirmed inputs, evidence health, and open proposals together.
- Use get_workflow_capabilities before advertising or starting a workflow. Never
  use general model knowledge to override needs_input or unsupported capability.
- For construction-management guidance, consult SiteWise platform knowledge
  before general model knowledge: list_platform_knowledge,
  search_platform_knowledge, read_platform_knowledge.
Label platform knowledge as guidance, not project evidence. General model
knowledge is the last resort when project evidence and platform guidance do
not answer the question.
When the user asks what the project needs — consultants, approvals, reports,
or next steps — do not answer with an undifferentiated textbook checklist.
Frame every recommendation against this project's <project-context> and
snapshot: name the specific project fact that drives each item (e.g. added
storeys/structure → structural + geotech; heritage locality → heritage
consultant; tight urban site → stormwater), lead with the set to act on now,
and separate those from generically-optional items the project can defer.
If a <project-context> field reads "(not declared)", search project documents
for that fact when it is a project identity field (site address, client /
owners). Only ask the user to declare it when evidence does not support a
clear value. Write plain, direct answers for construction professionals and
name the documents your answer relies on.
</persona>"""

_PROFILE_ENRICHMENT_GUIDANCE = """<profile-enrichment-request>
The user has asked for a best-effort Project Profile update without supplying
specific values. Treat this as a request to discover the facts from the uploaded
project documents, not as a reason to ask which fields they mean. First read
get_project_profile and get_project_profile_options. Review every unset or
incomplete profile field, including classification, subclasses, work scope,
scale, complexity, state, user role, site address, and client / owners. Search
project documents for those facts using find_document_text and search_documents
before replying; use targeted searches rather than relying only on the current
profile summary.

For each evidence-derived value that would improve the profile, call
propose_project_profile_change with evidence_references and a confidence value.
Use lower confidence for a plausible but tentative interpretation; make reasonable
taxonomy mappings from the evidence, group compatible values when appropriate,
and label uncertainty plainly so the user can correct it. Do not directly mutate
evidence-derived values and never invent a fact. Only leave a field unset after
the document pass cannot support it. Do not reply that
the profile is already up to date, or ask the user to tell you to search, before
completing this enrichment pass. End with a concise summary of the proposals
created and any fields still unresolved.
</profile-enrichment-request>"""

_PROFILE_PROPOSAL_CONFIRMATION_GUIDANCE = """<profile-proposal-confirmation>
The user has explicitly confirmed a pending Project Profile proposal. Accept
the matching proposal now with accept_project_profile_proposal; this does not
require a profile_mutation scope. Do not call update_project_profile or report
that the action is blocked. Use the proposal id and current profile revision
from the current project snapshot. If the id is not shown there, call
get_project_snapshot, match the confirmed fields to one pending proposal, then
accept it. Ask a clarifying question only if multiple pending proposals could
reasonably match this confirmation. Report the accepted fields after the tool
succeeds.
</profile-proposal-confirmation>"""


@dataclass(frozen=True)
class HistoryMessage:
    role: str
    content: str


def build_agent_prompt(
    user_text: str,
    *,
    project_id: str,
    title: str,
    archetype: str | None,
    user_role: str | None,
    state: str | None,
    phase: str | None,
    building_class: str | None,
    work_type: str | None,
    history: list[HistoryMessage],
    project_metadata: dict | None = None,
    mutation_intent: MutationIntent | None = None,
    snapshot: ProjectSnapshot | None = None,
    confirmed_profile_values: dict[str, Any] | None = None,
) -> str:
    """Wrap the user's message with the agent role, project overlays, and history.

    Overlay fields always appear — an explicit "(not declared)" tells the
    agent to resolve the gate with the user instead of guessing. History is
    capped by message count and per-message chars so the prompt stays bounded.
    """
    blocks: list[str] = [_ROLE_GUIDANCE]

    blocks.append(
        _project_context_block(
            project_id=project_id,
            title=title,
            archetype=archetype,
            user_role=user_role,
            state=state,
            phase=phase,
            building_class=building_class,
            work_type=work_type,
            project_metadata=project_metadata,
        )
    )
    blocks.append(_DOCUMENT_ACCESS_GUIDANCE)
    if snapshot is not None:
        blocks.append(_snapshot_context_block(snapshot))

    if mutation_intent is not None and (
        mutation_intent.scopes or mutation_intent.requires_confirmation
    ):
        blocks.append(_mutation_policy_block(mutation_intent))
    if _is_profile_enrichment_request(user_text, mutation_intent):
        blocks.append(_PROFILE_ENRICHMENT_GUIDANCE)
    if confirmed_profile_values:
        values_json = json.dumps(confirmed_profile_values, sort_keys=True)
        blocks.append(
            "<profile-proposal-confirmed>\n"
            "Clerk has already accepted the user-confirmed profile proposal. "
            f"Verified updated values: {values_json}. "
            "Do not call a profile mutation tool or say the action is blocked; "
            "report these saved values concisely.\n"
            "</profile-proposal-confirmed>"
        )
    elif _is_profile_proposal_confirmation_request(user_text, mutation_intent):
        blocks.append(_PROFILE_PROPOSAL_CONFIRMATION_GUIDANCE)

    window = _bounded_history(history)
    if window:
        lines = [f"{message.role}: {message.content}" for message in window]
        blocks.append(
            "<recent-conversation>\n" + "\n".join(lines) + "\n</recent-conversation>"
        )

    blocks.append(user_text)
    return "\n\n".join(blocks)


def _is_profile_enrichment_request(
    user_text: str,
    mutation_intent: MutationIntent | None,
) -> bool:
    """Recognize broad profile-completion requests that carry no exact patch."""
    if mutation_intent is not None and mutation_intent.scopes:
        return False
    normalized = " ".join(user_text.lower().split())
    return "profile" in normalized and any(
        re.search(rf"\b{verb}\b", normalized) for verb in _PROFILE_ENRICHMENT_VERBS
    )


def _is_profile_proposal_confirmation_request(
    user_text: str,
    mutation_intent: MutationIntent | None,
) -> bool:
    """Recognize confirmation of a profile proposal without an exact direct patch."""
    if mutation_intent is not None and mutation_intent.scopes:
        return False
    return is_profile_proposal_confirmation(user_text)


def _snapshot_context_block(snapshot: ProjectSnapshot) -> str:
    capability_matrix = workflow_capabilities(snapshot)
    capability_lines = [
        (
            f"workflow.{name}={capability.status}; "
            f"required_fields={','.join(capability.required_fields) or '(none)'}; "
            f"reasons={' | '.join(capability.reasons)}"
        )
        for name, capability in sorted(capability_matrix.capabilities.items())
    ]
    decision_lines = [
        (
            f"{decision.decision_id}={decision.selected} "
            f"(revision={decision.revision}, locked={str(decision.locked).lower()})"
        )
        for decision in snapshot.decisions.items[:50]
    ]
    input_lines = [
        f"{key}={value.value if value.status == 'confirmed' else _NOT_DECLARED}"
        for key, value in sorted(snapshot.confirmed_inputs.items())
    ]
    identity = getattr(snapshot, "identity", None)
    site_value = getattr(identity, "site_address", None) if identity is not None else None
    client_value = getattr(identity, "client", None) if identity is not None else None
    identity_lines = [
        (
            "site_address="
            f"{site_value.value if getattr(site_value, 'status', None) == 'confirmed' else _NOT_DECLARED}"
        ),
        (
            "client="
            f"{client_value.value if getattr(client_value, 'status', None) == 'confirmed' else _NOT_DECLARED}"
        ),
    ]
    next_action_lines = [
        (
            f"next_action.{action.code}=reason:{action.reason}; "
            f"blocking_fact:{action.blocking_fact}; route:{action.route}; tool:{action.tool}"
        )
        for action in snapshot.next_actions[:20]
    ]
    lines = [
        '<project-snapshot schema-version="1">',
        f"content_fingerprint: {snapshot.content_fingerprint}",
        f"profile_revision: {snapshot.profile.profile_revision}",
        f"decision_set_revision: {snapshot.decisions.set_revision}",
        f"open_decision_count: {snapshot.decisions.open_count}",
        f"evidence_fingerprint: {snapshot.evidence.fingerprint}",
        f"active_evidence_count: {snapshot.evidence.active_count}",
        f"ingest_failure_count: {snapshot.evidence.ingest_failure_count}",
        f"open_profile_proposals: {len(snapshot.open_profile_proposals)}",
        *capability_lines,
        *identity_lines,
        *input_lines,
        *decision_lines,
        *next_action_lines,
        "</project-snapshot>",
    ]
    return "\n".join(lines)


def _mutation_policy_block(intent: MutationIntent) -> str:
    if intent.scopes:
        patch_json = json.dumps(dict(intent.profile_patch), sort_keys=True)
        instruction = (
            "This turn has a server-bound profile_mutation scope. Call "
            "update_project_profile with changes exactly equal to this JSON object "
            f"and the current expected_revision: {patch_json}. "
            "Do not omit nested scale/subclasses values, do not add other profile "
            "fields, and never claim that scale fields such as storeys, gfa_sqm, "
            "bedrooms, or garage_spaces are missing when they appear here or as "
            "(not declared) in project-context."
        )
    elif intent.requires_confirmation:
        instruction = (
            "This message does not authorize a direct profile mutation. "
            "Create a profile proposal when the proposal tool is available, or ask "
            "the user to confirm the proposed values."
        )
    else:
        instruction = "This turn has no profile mutation authority."
    return f"<profile-mutation-policy>\n{instruction}\n</profile-mutation-policy>"


def _project_context_block(
    *,
    project_id: str,
    title: str,
    archetype: str | None,
    user_role: str | None,
    state: str | None,
    phase: str | None,
    building_class: str | None,
    work_type: str | None,
    project_metadata: dict | None,
) -> str:
    taxonomy = _taxonomy_metadata(project_metadata)
    subclass_items = _subclass_items(taxonomy.get("subclasses"))
    subclass_values = tuple(value for value, _label in subclass_items)
    has_project_taxonomy = _clean(building_class) is not None or _clean(work_type) is not None

    lines = [
        "<project-context>",
        f"project_id: {project_id}",
        f"project_title: {title}",
    ]

    if has_project_taxonomy:
        lines.append("classification_source: project_taxonomy")
        if _clean(archetype) is not None:
            lines.append(f"archetype: {archetype}")
        lines.extend(
            [
                f"building_class: {building_class or _NOT_DECLARED}",
                f"work_type: {work_type or _NOT_DECLARED}",
            ]
        )
        subclasses = _format_subclasses(building_class, subclass_items)
        if subclasses:
            lines.append(f"subclasses: {subclasses}")
        scale = _format_scale(building_class, subclass_values, taxonomy.get("scale"))
        if scale:
            lines.append(f"scale: {scale}")
        complexity = _format_mapping(taxonomy.get("complexity"))
        if complexity:
            lines.append(f"complexity: {complexity}")
        work_scope = _format_list(taxonomy.get("work_scope"))
        if work_scope:
            lines.append(f"work_scope: {work_scope}")
    else:
        lines.extend(
            [
                f"archetype: {archetype or _NOT_DECLARED}",
                f"building_class: {building_class or _NOT_DECLARED}",
                f"work_type: {work_type or _NOT_DECLARED}",
            ]
        )

    site_address = _clean(taxonomy.get("site_address"))
    if site_address is None and isinstance(project_metadata, dict):
        site_address = _clean(project_metadata.get("site_address"))
    client = _clean(taxonomy.get("client"))
    if client is None and isinstance(project_metadata, dict):
        client = _clean(project_metadata.get("client"))

    lines.extend(
        [
            f"phase: {phase or _NOT_DECLARED}",
            f"user_role: {user_role or _NOT_DECLARED}",
            f"state: {state or _NOT_DECLARED}",
            f"site_address: {site_address or _NOT_DECLARED}",
            f"client: {client or _NOT_DECLARED}",
            "</project-context>",
        ]
    )
    return "\n".join(lines)


def _taxonomy_metadata(project_metadata: dict | None) -> dict[str, Any]:
    if not isinstance(project_metadata, dict):
        return {}
    taxonomy = project_metadata.get("taxonomy")
    return taxonomy if isinstance(taxonomy, dict) else {}


def _subclass_items(value: Any) -> list[tuple[str, str | None]]:
    if not isinstance(value, list):
        return []
    items: list[tuple[str, str | None]] = []
    for item in value:
        if isinstance(item, str):
            cleaned = _clean(item)
            if cleaned is not None:
                items.append((cleaned, None))
            continue
        if not isinstance(item, dict):
            continue
        raw_value = item.get("value")
        if not isinstance(raw_value, str):
            continue
        cleaned = _clean(raw_value)
        if cleaned is None:
            continue
        label = item.get("label")
        items.append((cleaned, _clean(label) if isinstance(label, str) else None))
    return items


def _format_subclasses(
    building_class: str | None,
    subclass_items: list[tuple[str, str | None]],
) -> str | None:
    if not subclass_items:
        return None
    known = {
        subclass.value: subclass.label
        for subclass in subclasses_for(building_class or "")
    }
    labels = [
        custom_label or known.get(value) or value
        for value, custom_label in subclass_items
    ]
    return ", ".join(labels)


def _format_scale(
    building_class: str | None,
    subclass_values: tuple[str, ...],
    value: Any,
) -> str | None:
    labels: dict[str, str] = {}
    for subclass in subclass_values:
        for field in scale_fields_for(building_class or "", subclass):
            labels.setdefault(field.key, field.label)
    if not labels:
        if not isinstance(value, dict):
            return None
        return _format_mapping(value)
    current = value if isinstance(value, dict) else {}
    parts = []
    for key, label in labels.items():
        item = current.get(key)
        if item in (None, "", [], {}):
            parts.append(f"{label}={_NOT_DECLARED}")
        else:
            parts.append(f"{label}={_format_scalar(item)}")
    for key, item in current.items():
        if key in labels or item in (None, "", [], {}):
            continue
        parts.append(f"{key}={_format_scalar(item)}")
    return ", ".join(parts) or None


def _format_mapping(value: Any, *, labels: dict[str, str] | None = None) -> str | None:
    if not isinstance(value, dict):
        return None
    labels = labels or {}
    parts = []
    for key, item in value.items():
        if item in (None, "", [], {}):
            continue
        label = labels.get(str(key), str(key))
        parts.append(f"{label}={_format_scalar(item)}")
    return ", ".join(parts) or None


def _format_list(value: Any) -> str | None:
    if not isinstance(value, list):
        return None
    parts = [str(item).strip() for item in value if str(item).strip()]
    return ", ".join(parts) or None


def _format_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _bounded_history(history: list[HistoryMessage]) -> list[HistoryMessage]:
    limit = settings.agent_history_message_limit
    if limit <= 0:
        return []
    max_chars = settings.agent_history_message_chars
    window = history[-limit:]
    bounded: list[HistoryMessage] = []
    for message in window:
        content = " ".join(message.content.split())
        if len(content) > max_chars:
            content = content[: max_chars - 1].rstrip() + "…"
        if content:
            bounded.append(HistoryMessage(role=message.role, content=content))
    return bounded
