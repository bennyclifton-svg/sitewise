from typing import Literal

SiteWiseKnowledgeKind = Literal["doctrine", "seed", "skill", "template"]


def sitewise_knowledge_kind(relative_path: str) -> SiteWiseKnowledgeKind | None:
    normalized = relative_path.replace("\\", "/")

    if normalized == "docs/clerk-brief.md":
        return "doctrine"
    if normalized.endswith("clerk-practice-intelligence-integration-prd.md"):
        return "doctrine"

    top = normalized.split("/", maxsplit=1)[0]
    if top == "seed":
        return "seed"
    if top == "skills":
        return "skill"
    if top == "project-template":
        return "template"
    return None


def sitewise_platform_metadata(relative_path: str) -> dict[str, str]:
    kind = sitewise_knowledge_kind(relative_path)
    if kind is None:
        return {}
    return {
        "knowledge_scope": "platform",
        "platform": "sitewise",
        "sitewise_knowledge_kind": kind,
    }
