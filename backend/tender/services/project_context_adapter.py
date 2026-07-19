from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.projects.document_selections import read_selection
from app.projects.snapshot import get_project_snapshot
from app.schemas.document_selections import TenderQuoteSelection
from app.schemas.project_snapshot import ProjectSnapshot
from tender.schemas import ProjectContext

SnapshotReader = Callable[..., Awaitable[ProjectSnapshot]]
SelectionReader = Callable[..., Awaitable[TenderQuoteSelection]]


class TenderContextProvenance(BaseModel):
    snapshot_content_fingerprint: str
    source_profile_revision: int
    source_selection_revision: int
    selection_revision_id: str
    ordered_quotes: list[dict[str, Any]] = Field(default_factory=list)


class PreparedProjectContext(BaseModel):
    supported: bool
    ready: bool
    context: ProjectContext | None = None
    missing_fields: list[str] = Field(default_factory=list)
    unsupported_reasons: list[str] = Field(default_factory=list)
    provenance: TenderContextProvenance


class ProjectContextAdapter:
    def __init__(
        self,
        *,
        snapshot_reader: SnapshotReader = get_project_snapshot,
        selection_reader: SelectionReader = read_selection,
    ) -> None:
        self._snapshot_reader = snapshot_reader
        self._selection_reader = selection_reader

    async def prepare(
        self,
        session: AsyncSession,
        *,
        project_id,
        owner_user_id,
        expected_profile_revision: int,
        expected_selection_revision: int,
        overrides: dict[str, Any] | None = None,
    ) -> PreparedProjectContext:
        snapshot = await self._snapshot_reader(
            session, project_id=project_id, owner_user_id=owner_user_id
        )
        selection = await self._selection_reader(session, project_id=project_id)
        if snapshot.profile.profile_revision != expected_profile_revision:
            raise ContextRevisionConflict("profile", expected_profile_revision, snapshot.profile.profile_revision)
        if selection.revision != expected_selection_revision:
            raise ContextRevisionConflict("selection", expected_selection_revision, selection.revision)
        if selection.selection_revision_id is None:
            raise ContextValidationError("Tender quote selection has not been saved")
        return map_project_context(snapshot=snapshot, selection=selection, overrides=overrides)


class ContextRevisionConflict(ValueError):
    def __init__(self, resource: str, expected: int, current: int) -> None:
        self.resource = resource
        self.expected = expected
        self.current = current
        super().__init__(f"expected {resource} revision {expected}, current revision is {current}")


class ContextValidationError(ValueError):
    pass


def map_project_context(
    *, snapshot: ProjectSnapshot, selection: TenderQuoteSelection,
    overrides: dict[str, Any] | None = None,
) -> PreparedProjectContext:
    profile = snapshot.profile
    unsupported: list[str] = []
    if profile.building_class != "residential":
        unsupported.append("Tender Comparison supports residential Class 1a projects only")
    subclass_values = {
        item if isinstance(item, str) else item.value for item in profile.subclasses
    }
    if subclass_values and not subclass_values.intersection({"house", "class_1a", "detached_house"}):
        unsupported.append("Project subclass is not a supported Class 1a residence")
    build_type = {"new": "new_build", "refurb": "renovation", "extend": "addition"}.get(profile.work_type or "")
    if build_type is None:
        unsupported.append(f"Work type {profile.work_type or 'missing'} is unsupported")
    if profile.state not in {"NSW", "VIC", "QLD"}:
        unsupported.append(f"State {profile.state or 'missing'} is unsupported")

    values: dict[str, Any] = {
        "context_source": "repository_selection",
        "state": profile.state if profile.state in {"NSW", "VIC", "QLD"} else None,
        "build_type": build_type,
        "dwelling_class": "class_1a",
        "storeys": profile.scale.get("storeys"),
        "floor_area_m2": profile.scale.get("gfa_sqm"),
    }
    values.update(overrides or {})
    try:
        context = ProjectContext.model_validate(values)
    except ValidationError as exc:
        raise ContextValidationError(str(exc)) from exc
    missing = [field for field in ("state", "build_type", "storeys", "region", "spec_level") if getattr(context, field) is None]
    provenance = TenderContextProvenance(
        snapshot_content_fingerprint=snapshot.content_fingerprint,
        source_profile_revision=profile.profile_revision,
        source_selection_revision=selection.revision,
        selection_revision_id=str(selection.selection_revision_id),
        ordered_quotes=[
            {
                "builder_name": group.builder_name,
                "position": group.position,
                "ordered_files": [
                    {
                        "workspace_file_id": str(file.workspace_file_id),
                        "position": file.position,
                        "content_hash": file.content_hash,
                        "storage_bucket": file.storage_bucket,
                        "storage_key": file.storage_key,
                    }
                    for file in group.files
                ],
            }
            for group in selection.quote_groups
        ],
    )
    return PreparedProjectContext(
        supported=not unsupported,
        ready=not unsupported and not missing and 2 <= len(selection.quote_groups) <= 5,
        context=context,
        missing_fields=missing,
        unsupported_reasons=unsupported,
        provenance=provenance,
    )
