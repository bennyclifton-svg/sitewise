from ingest.platform import sitewise_knowledge_kind
from ingest.types import ProjectContext

_DOCTRINE_PATH = "docs/clerk-brief.md"
_INTEGRATION_PRD = "docs/plans/2026-06-07-clerk-practice-intelligence-integration-prd.md"


def infer_project_context(relative_path: str) -> ProjectContext:
    normalized = relative_path.replace("\\", "/")
    parts = normalized.split("/")

    if normalized == _DOCTRINE_PATH or normalized.endswith("/clerk-brief.md"):
        return ProjectContext(project="sitewise-platform", phase="reference", source_type="doctrine")

    if normalized == _INTEGRATION_PRD:
        return ProjectContext(project="sitewise-platform", phase="reference", source_type="doctrine")

    if not parts:
        return ProjectContext(project="unknown", phase="reference", source_type="project_evidence")

    top = parts[0]

    if sitewise_knowledge_kind(normalized) is not None:
        return ProjectContext(project="sitewise-platform", phase="reference", source_type="reference")

    if top.startswith("delivery-"):
        return ProjectContext(project=top, phase="delivery", source_type="project_evidence")

    if top.startswith("procurement-") or top.startswith("procurment-"):
        return ProjectContext(project=top, phase="procurement", source_type="project_evidence")

    if top.startswith("advisary-"):
        return ProjectContext(project=top, phase="advisory", source_type="project_evidence")

    if top.startswith("consultants-"):
        return ProjectContext(project=top, phase="consultants", source_type="project_evidence")

    if top == "04-projects" and len(parts) >= 2:
        return ProjectContext(project=parts[1], phase="reference", source_type="project_evidence")

    return ProjectContext(project=top, phase="reference", source_type="project_evidence")


def infer_document_type(filename: str, document_class: str) -> str | None:
    lowered = filename.lower()
    if document_class != "unknown":
        return document_class
    if "contract" in lowered or "agreement" in lowered or "fioa" in lowered:
        return "contract"
    if "spec" in lowered:
        return "specification"
    if "basix" in lowered or "certificate" in lowered:
        return "certificate"
    return None
