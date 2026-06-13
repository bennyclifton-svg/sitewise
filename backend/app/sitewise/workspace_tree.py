"""Merge the SiteWise folder template with hosted workspace file paths."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas.projects import WorkspaceTreeNode
from app.sitewise.template import SITEWISE_PROJECT_TEMPLATE, WorkspaceTemplateNode
from ingest.document_metadata import DISCIPLINE_FOLDER_LABELS

_TEMPLATE_ORDER = [node.name for node in SITEWISE_PROJECT_TEMPLATE]


def _looks_like_file(name: str) -> bool:
    if "." not in name:
        return False
    extension = name.rsplit(".", maxsplit=1)[-1]
    return bool(extension) and "/" not in extension


def _dynamic_folder_description(name: str, parent_name: str | None) -> str:
    slug = name.replace("_", "-").lower()
    if parent_name in {"02-consultant", "03-design"}:
        label = DISCIPLINE_FOLDER_LABELS.get(slug)
        if label:
            return f"{label} records filed under {parent_name}."
    if name == "_inbox":
        return "Incoming project evidence awaiting Sort Files."
    return f"Project records in {name}."


@dataclass
class _MutableNode:
    name: str
    path: str
    description: str
    related_workflows: list[str] = field(default_factory=list)
    kind: str = "directory"
    children: dict[str, _MutableNode] = field(default_factory=dict)

    def get_or_create_child(
        self,
        *,
        name: str,
        path: str,
        description: str,
        kind: str = "directory",
    ) -> _MutableNode:
        existing = self.children.get(name)
        if existing is not None:
            return existing
        child = _MutableNode(
            name=name,
            path=path,
            description=description,
            kind=kind,
        )
        self.children[name] = child
        return child


def _seed_from_template(template_node: WorkspaceTemplateNode, parent_path: str) -> _MutableNode:
    path = f"{parent_path.rstrip('/')}/{template_node.name}"
    node = _MutableNode(
        name=template_node.name,
        path=path,
        description=template_node.description,
        related_workflows=list(template_node.related_workflows),
    )
    for child in template_node.children:
        seeded = _seed_from_template(child, path)
        node.children[seeded.name] = seeded
    return node


def _merge_workspace_path(
    roots: dict[str, _MutableNode],
    *,
    root_path: str,
    workspace_path: str,
) -> None:
    normalised_root = root_path.rstrip("/")
    normalised_path = workspace_path.replace("\\", "/")
    prefix = f"{normalised_root}/"
    if not normalised_path.startswith(prefix):
        return

    relative_parts = [part for part in normalised_path[len(prefix) :].split("/") if part]
    if not relative_parts:
        return

    path_so_far = normalised_root
    current = roots
    parent_node: _MutableNode | None = None
    parent_name: str | None = None

    for index, part in enumerate(relative_parts):
        path_so_far = f"{path_so_far}/{part}"
        is_file = index == len(relative_parts) - 1 and _looks_like_file(part)

        if is_file:
            if parent_node is None:
                return
            parent_node.get_or_create_child(
                name=part,
                path=path_so_far,
                description=part,
                kind="file",
            )
            return

        if part in current:
            parent_node = current[part]
        elif parent_node is None:
            parent_node = _MutableNode(
                name=part,
                path=path_so_far,
                description=_dynamic_folder_description(part, None),
            )
            current[part] = parent_node
        else:
            parent_node = parent_node.get_or_create_child(
                name=part,
                path=path_so_far,
                description=_dynamic_folder_description(part, parent_name),
            )

        parent_name = part
        current = parent_node.children


def _child_sort_key(node: _MutableNode) -> tuple[int, str]:
    if node.kind == "file":
        return (2, node.name.lower())
    return (1, node.name.lower())


def _top_level_sort_key(node: _MutableNode) -> tuple[int, int | str]:
    if node.name == "_inbox":
        return (-1, 0)
    try:
        return (0, _TEMPLATE_ORDER.index(node.name))
    except ValueError:
        return (1, node.name)


def _to_schema(node: _MutableNode) -> WorkspaceTreeNode:
    children = sorted(node.children.values(), key=_child_sort_key)
    child_nodes = [_to_schema(child) for child in children if child.kind != "file"]
    file_nodes = [
        WorkspaceTreeNode(
            name=child.name,
            path=child.path,
            kind="file",
            description=child.description,
            document_count=1,
            related_workflows=[],
            children=[],
        )
        for child in children
        if child.kind == "file"
    ]
    merged_children = child_nodes + file_nodes
    direct_files = len(file_nodes)
    nested_files = sum(child.document_count for child in child_nodes)
    return WorkspaceTreeNode(
        name=node.name,
        path=node.path,
        kind=node.kind,
        description=node.description,
        document_count=direct_files + nested_files,
        related_workflows=list(node.related_workflows),
        children=merged_children,
    )


def _seed_inbox_folder(root_path: str) -> _MutableNode:
    path = f"{root_path.rstrip('/')}/_inbox"
    return _MutableNode(
        name="_inbox",
        path=path,
        description=_dynamic_folder_description("_inbox", None),
    )


def build_project_workspace_tree(
    *,
    root_path: str,
    workspace_paths: list[str],
) -> list[WorkspaceTreeNode]:
    roots: dict[str, _MutableNode] = {"_inbox": _seed_inbox_folder(root_path)}
    for template_node in SITEWISE_PROJECT_TEMPLATE:
        seeded = _seed_from_template(template_node, root_path)
        roots[seeded.name] = seeded

    for workspace_path in workspace_paths:
        _merge_workspace_path(roots, root_path=root_path, workspace_path=workspace_path)

    ordered_roots = sorted(roots.values(), key=_top_level_sort_key)
    return [_to_schema(node) for node in ordered_roots]
