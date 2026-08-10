from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
import uuid

from app.database.activity_event import ActivityEvent
from app.database.project import Project
from app.schemas.projects import (
    ProjectProfileChange,
    ProjectProfileField,
    ProjectProfilePatch,
    ProjectProfileView,
    ProjectSubclassSelection,
)
from app.sitewise.gate import (
    DEFAULT_USER_ROLE,
    SUPPORTED_STATES,
    overlay_status,
)
from app.sitewise.taxonomy import (
    ScaleField,
    complexity_dimensions_for,
    derive_risk_flags,
    scale_fields_for,
    subclasses_for,
    taxonomy_options_payload,
    validate_project_taxonomy,
    work_scope_items_for,
)
from app.projects.events import publish_project_event

PROFILE_FIELDS: tuple[ProjectProfileField, ...] = (
    "building_class",
    "work_type",
    "subclasses",
    "scale",
    "complexity",
    "work_scope",
    "state",
    "site_address",
    "client",
)


class ProfileValidationError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


class ProfileRevisionConflict(RuntimeError):
    def __init__(self, *, expected_revision: int, current_revision: int) -> None:
        self.expected_revision = expected_revision
        self.current_revision = current_revision
        super().__init__(
            f"profile revision conflict: expected {expected_revision}, "
            f"current {current_revision}"
        )


class ProfileDependencyConflict(ValueError):
    def __init__(self, fields: tuple[ProjectProfileField, ...]) -> None:
        self.fields = fields
        super().__init__(
            "profile parent change conflicts with dependent fields: "
            + ", ".join(fields)
        )


@dataclass(frozen=True, slots=True)
class ProfileUpdatePlan:
    before: ProjectProfileView
    after: ProjectProfileView
    changed_fields: tuple[ProjectProfileField, ...]
    cleared_fields: tuple[ProjectProfileField, ...]


def profile_options() -> dict[str, Any]:
    return taxonomy_options_payload()


async def apply_profile_patch(
    session,
    *,
    project: Project,
    patch: ProjectProfilePatch,
    actor_source: str,
) -> ProjectProfileChange:
    await session.refresh(project, with_for_update=True)
    plan = validate_profile_patch(project, patch)
    if not plan.changed_fields and not plan.cleared_fields:
        return _profile_change(project, plan, new_revision=project.profile_revision)

    new_revision = plan.before.profile_revision + 1
    _write_profile(project, plan.after)
    _update_identity_review_marker(
        project,
        changed_fields=(*plan.changed_fields, *plan.cleared_fields),
        actor_source=actor_source,
    )
    from app.projects.dependencies import (
        dirty_categories_for_profile_fields,
        mark_project_dirty,
    )

    mark_project_dirty(
        project,
        dirty_categories_for_profile_fields(
            (*plan.changed_fields, *plan.cleared_fields)
        ),
    )
    project.profile_revision = new_revision
    session.add(
        ActivityEvent(
            project_id=project.id,
            run_id=uuid.uuid4(),
            source=actor_source,
            reference_type="project_profile",
            reference_id=project.id,
            step="project_profile_update",
            status="complete",
            message="Project profile updated",
            event_metadata={
                "previous_revision": plan.before.profile_revision,
                "new_revision": new_revision,
                "changed_fields": list(plan.changed_fields),
                "cleared_fields": list(plan.cleared_fields),
                "before": plan.before.model_dump(mode="json"),
                "after": plan.after.model_dump(mode="json"),
            },
        )
    )
    await publish_project_event(
        session,
        project_id=project.id,
        actor_source=actor_source,
        resource_type="project_profile",
        resource_id=project.id,
        resource_revision=new_revision,
        action="updated",
        payload={
            "previous_revision": plan.before.profile_revision,
            "new_revision": new_revision,
            "changed_fields": list(plan.changed_fields),
            "cleared_fields": list(plan.cleared_fields),
        },
        changes_context=True,
        locked_project=project,
    )
    return _profile_change(project, plan, new_revision=new_revision)


def validate_profile_patch(
    project: Project,
    patch: ProjectProfilePatch,
) -> ProfileUpdatePlan:
    before = read_profile(project)
    if patch.expected_revision != before.profile_revision:
        raise ProfileRevisionConflict(
            expected_revision=patch.expected_revision,
            current_revision=before.profile_revision,
        )
    updates = {
        field: getattr(patch, field)
        for field in PROFILE_FIELDS
        if field in patch.model_fields_set
    }
    after = before.model_copy(update=updates)
    dependent_conflicts = _dependent_conflicts(before, after, patch)
    if dependent_conflicts and not patch.clear_incompatible:
        raise ProfileDependencyConflict(dependent_conflicts)
    if dependent_conflicts:
        after = after.model_copy(
            update={field: _empty_profile_value(field) for field in dependent_conflicts}
        )
    errors = validate_project_taxonomy(
        building_class=after.building_class,
        work_type=after.work_type,
        subclasses=_subclass_values(after.subclasses),
    )
    errors.extend(_validate_scale(after))
    errors.extend(_validate_complexity(after))
    errors.extend(_validate_work_scope(after))
    if after.state is not None and after.state not in SUPPORTED_STATES:
        errors.append(f"Unknown state: {after.state!r}")
    if errors:
        raise ProfileValidationError(errors)
    effective_changes = tuple(
        field
        for field in PROFILE_FIELDS
        if getattr(before, field) != getattr(after, field)
    )
    cleared = tuple(
        field for field in effective_changes if getattr(after, field) in (None, [], {})
    )
    changed = tuple(field for field in effective_changes if field not in cleared)
    return ProfileUpdatePlan(
        before=before,
        after=after,
        changed_fields=changed,
        cleared_fields=cleared,
    )


def read_profile(project: Project) -> ProjectProfileView:
    metadata = getattr(project, "project_metadata", None) or {}
    taxonomy = metadata.get("taxonomy") if isinstance(metadata, dict) else None
    taxonomy = taxonomy if isinstance(taxonomy, dict) else {}
    return ProjectProfileView(
        project_id=project.id,
        profile_revision=getattr(project, "profile_revision", 1) or 1,
        building_class=getattr(project, "building_class", None),
        work_type=getattr(project, "work_type", None),
        subclasses=_list_value(taxonomy.get("subclasses")),
        scale=_dict_value(taxonomy.get("scale")),
        complexity=_dict_value(taxonomy.get("complexity")),
        work_scope=[
            item
            for item in _list_value(taxonomy.get("work_scope"))
            if isinstance(item, str)
        ],
        user_role=getattr(project, "user_role", None),
        state=getattr(project, "state", None),
        site_address=_optional_text(
            taxonomy.get("site_address")
            if taxonomy.get("site_address") is not None
            else metadata.get("site_address")
            if isinstance(metadata, dict)
            else None
        ),
        client=_optional_text(
            taxonomy.get("client")
            if taxonomy.get("client") is not None
            else metadata.get("client")
            if isinstance(metadata, dict)
            else None
        ),
    )


def _dict_value(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list_value(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _subclass_values(
    values: list[str | ProjectSubclassSelection],
) -> list[str]:
    return [item if isinstance(item, str) else item.value for item in values]


def _validate_scale(profile: ProjectProfileView) -> list[str]:
    fields: dict[str, ScaleField] = {}
    if profile.building_class:
        for subclass in _subclass_values(profile.subclasses):
            fields.update(
                (field.key, field)
                for field in scale_fields_for(profile.building_class, subclass)
            )
    errors: list[str] = []
    for key, value in profile.scale.items():
        field = fields.get(key)
        if field is None:
            errors.append(f"Unknown scale field: {key!r}")
            continue
        if field.type == "integer" and (
            isinstance(value, bool) or not isinstance(value, int)
        ):
            errors.append(f"scale {key!r} must be an integer")
            continue
        if field.type == "number" and (
            isinstance(value, bool) or not isinstance(value, (int, float))
        ):
            errors.append(f"scale {key!r} must be a number")
            continue
        if field.type == "text" and not isinstance(value, str):
            errors.append(f"scale {key!r} must be text")
            continue
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if field.minimum is not None and value < field.minimum:
                errors.append(f"scale {key!r} must be at least {field.minimum}")
            if field.maximum is not None and value > field.maximum:
                errors.append(f"scale {key!r} must be at most {field.maximum}")
    return errors


def _validate_complexity(profile: ProjectProfileView) -> list[str]:
    dimensions = {
        dimension.key: dimension
        for dimension in complexity_dimensions_for(
            profile.building_class or "",
            _subclass_values(profile.subclasses),
        )
    }
    errors: list[str] = []
    for key, value in profile.complexity.items():
        dimension = dimensions.get(key)
        if dimension is None:
            errors.append(f"Unknown complexity dimension: {key!r}")
            continue
        valid_options = {option.value for option in dimension.options}
        if value not in valid_options:
            errors.append(f"Unknown option for complexity {key!r}: {value!r}")
    return errors


def _validate_work_scope(profile: ProjectProfileView) -> list[str]:
    valid = {
        item.value
        for item in work_scope_items_for(profile.work_type, profile.work_scope)
    }
    return [
        f"Unknown work_scope for {profile.work_type!r}: {value!r}"
        for value in profile.work_scope
        if value not in valid
    ]


def _dependent_conflicts(
    before: ProjectProfileView,
    after: ProjectProfileView,
    patch: ProjectProfilePatch,
) -> tuple[ProjectProfileField, ...]:
    conflicts: set[ProjectProfileField] = set()
    class_changed = before.building_class != after.building_class
    if class_changed:
        subclass_values = _subclass_values(after.subclasses)
        valid_subclasses = {
            item.value for item in subclasses_for(after.building_class or "")
        }
        if "subclasses" not in patch.model_fields_set and any(
            value not in valid_subclasses for value in subclass_values
        ):
            conflicts.add("subclasses")
        dependent_view = after.model_copy(
            update={"subclasses": []} if "subclasses" in conflicts else {}
        )
        if (
            dependent_view.scale
            and "scale" not in patch.model_fields_set
            and _validate_scale(dependent_view)
        ):
            conflicts.add("scale")
        if (
            dependent_view.complexity
            and "complexity" not in patch.model_fields_set
            and _validate_complexity(dependent_view)
        ):
            conflicts.add("complexity")
    if (
        before.work_type != after.work_type
        and after.work_scope
        and "work_scope" not in patch.model_fields_set
        and _validate_work_scope(after)
    ):
        conflicts.add("work_scope")
    return tuple(field for field in PROFILE_FIELDS if field in conflicts)


def _empty_profile_value(
    field: ProjectProfileField,
) -> None | list[Any] | dict[str, Any]:
    if field in {"subclasses", "work_scope"}:
        return []
    if field in {"scale", "complexity"}:
        return {}
    return None


def _profile_change(
    project: Project,
    plan: ProfileUpdatePlan,
    *,
    new_revision: int,
) -> ProjectProfileChange:
    profile = plan.after.model_copy(update={"profile_revision": new_revision})
    return ProjectProfileChange(
        profile=profile,
        previous_revision=plan.before.profile_revision,
        new_revision=new_revision,
        changed_fields=list(plan.changed_fields),
        cleared_fields=list(plan.cleared_fields),
        overlay_status=overlay_status(
            archetype=project.archetype,
            building_class=profile.building_class,
            work_type=profile.work_type,
            state=profile.state,
        ),
        risk_flags=[
            asdict(flag)
            for flag in derive_risk_flags(
                {key: str(value) for key, value in profile.complexity.items()},
                profile.work_scope,
            )
        ],
    )


def _optional_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _write_profile(project: Project, profile: ProjectProfileView) -> None:
    project.building_class = profile.building_class
    project.work_type = profile.work_type
    # Role is not user-editable; every project is pinned to the single role.
    project.user_role = DEFAULT_USER_ROLE
    project.state = profile.state
    metadata = dict(project.project_metadata or {})
    existing_taxonomy = metadata.get("taxonomy")
    preserved: dict[str, Any] = {}
    if isinstance(existing_taxonomy, dict):
        for key, value in existing_taxonomy.items():
            if key in {
                "subclasses",
                "scale",
                "complexity",
                "work_scope",
                "site_address",
                "client",
            }:
                continue
            preserved[key] = value
    taxonomy: dict[str, Any] = {
        **preserved,
        "subclasses": [
            item if isinstance(item, str) else item.model_dump(exclude_none=True)
            for item in profile.subclasses
        ],
        "scale": dict(profile.scale),
        "complexity": dict(profile.complexity),
        "work_scope": list(profile.work_scope),
    }
    if profile.site_address:
        taxonomy["site_address"] = profile.site_address
    if profile.client:
        taxonomy["client"] = profile.client
    metadata["taxonomy"] = taxonomy
    # Prefer taxonomy as the canonical store; drop legacy top-level copies.
    metadata.pop("site_address", None)
    metadata.pop("client", None)
    project.project_metadata = metadata


def _update_identity_review_marker(
    project: Project,
    *,
    changed_fields: tuple[ProjectProfileField, ...],
    actor_source: str,
) -> None:
    """Keep document-derived identity visible until the user reviews the fields."""
    identity_fields = {"client", "site_address"} & set(changed_fields)
    if not identity_fields:
        return

    metadata = dict(project.project_metadata or {})
    existing = metadata.get("identity_review")
    marked_fields = (
        set(existing.get("fields", [])) if isinstance(existing, dict) else set()
    )
    if actor_source in {"agent", "ingest", "identity_autofill"}:
        marked_fields.update(identity_fields)
    elif actor_source == "user":
        marked_fields.difference_update(identity_fields)
    else:
        return

    if marked_fields:
        metadata["identity_review"] = {"fields": sorted(marked_fields)}
    else:
        metadata.pop("identity_review", None)
    project.project_metadata = metadata
