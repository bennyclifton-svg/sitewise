from __future__ import annotations

from collections import defaultdict, deque
from typing import Iterable

from app.cost_plan.schemas import DependencySnapshot
from app.schemas.project_snapshot import ProjectSnapshot

ROOTS = frozenset({"profile", "evidence", "decisions"})
DEFAULT_EDGES = (
    ("profile", "project_plan"),
    ("profile", "cost_plan"),
    ("profile", "tender"),
    ("evidence", "project_plan"),
    ("evidence", "cost_plan"),
    ("evidence", "tender"),
    ("decisions", "project_plan"),
    ("decisions", "cost_plan"),
    ("decisions", "tender"),
    ("tender", "cost_plan"),
    ("cost_plan", "project_plan"),
)


class DependencyCycleError(ValueError):
    pass


def validate_acyclic(edges: Iterable[tuple[str, str]]) -> None:
    graph: dict[str, set[str]] = defaultdict(set)
    indegree: dict[str, int] = defaultdict(int)
    nodes: set[str] = set()
    for source, target in edges:
        if source == target:
            raise DependencyCycleError(f"dependency cycle at {source}")
        nodes.update((source, target))
        if target not in graph[source]:
            graph[source].add(target)
            indegree[target] += 1
            indegree.setdefault(source, 0)
    queue = deque(node for node in nodes if indegree[node] == 0)
    visited = 0
    while queue:
        source = queue.popleft()
        visited += 1
        for target in graph[source]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if visited != len(nodes):
        raise DependencyCycleError("dependency graph contains a cycle")


def dependency_snapshot(
    snapshot: ProjectSnapshot,
    *,
    upstream_artefacts: list[dict] | None = None,
    model_version: str | None = None,
    prompt_version: str | None = None,
    runtime_version: str,
) -> DependencySnapshot:
    validate_acyclic(DEFAULT_EDGES)
    return DependencySnapshot(
        profile_revision=snapshot.profile.profile_revision,
        evidence_fingerprint=snapshot.evidence.fingerprint,
        decision_set_revision=snapshot.decisions.set_revision,
        upstream_artefacts=upstream_artefacts or [],
        model_version=model_version,
        prompt_version=prompt_version,
        runtime_version=runtime_version,
    )


def stale_reasons(
    recorded: DependencySnapshot,
    current: ProjectSnapshot,
    *,
    current_upstream_versions: dict[str, int] | None = None,
    tender_approved_after_cost_plan: bool = False,
) -> list[str]:
    reasons: list[str] = []
    if current.profile.profile_revision != recorded.profile_revision:
        reasons.append("profile_changed")
    if current.evidence.fingerprint != recorded.evidence_fingerprint:
        reasons.append("evidence_added_removed_or_revised")
    if current.decisions.set_revision != recorded.decision_set_revision:
        reasons.append("decision_changed")
    upstream = current_upstream_versions or {}
    if any(
        upstream.get(str(item.get("id"))) not in (None, item.get("version"))
        for item in recorded.upstream_artefacts
    ):
        reasons.append("upstream_artefact_revised")
    if tender_approved_after_cost_plan:
        reasons.append("tender_approved_after_cost_plan")
    return reasons
