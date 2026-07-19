from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.project_document_selection import (
    ProjectDocumentSelection,
    ProjectDocumentSelectionGroup,
    ProjectDocumentSelectionItem,
    ProjectDocumentSelectionRevision,
    WorkflowInputRetentionLock,
)
from app.database.workspace_file import WorkspaceFile
from app.database.project import Project
from app.projects.events import publish_project_event
from app.schemas.document_selections import (
    QuoteCandidateInput,
    SelectedWorkspaceFile,
    TenderQuoteGroup,
    TenderQuoteSelection,
)

TENDER_COMPARISON_PURPOSE = "tender_comparison"


class SelectionRevisionConflict(ValueError):
    def __init__(self, expected: int, current: int) -> None:
        self.expected = expected
        self.current = current
        super().__init__(f"expected selection revision {expected}, current revision is {current}")


class SelectionValidationError(ValueError):
    pass


async def _selection_row(session: AsyncSession, *, project_id: uuid.UUID, purpose: str, lock: bool = False) -> ProjectDocumentSelection | None:
    statement = select(ProjectDocumentSelection).where(
        ProjectDocumentSelection.project_id == project_id,
        ProjectDocumentSelection.purpose == purpose,
    )
    if lock:
        statement = statement.with_for_update()
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def _revision_row(session: AsyncSession, *, selection_id: uuid.UUID, revision: int) -> ProjectDocumentSelectionRevision | None:
    result = await session.execute(
        select(ProjectDocumentSelectionRevision)
        .options(
            selectinload(ProjectDocumentSelectionRevision.groups)
            .selectinload(ProjectDocumentSelectionGroup.items)
        )
        .where(
            ProjectDocumentSelectionRevision.selection_id == selection_id,
            ProjectDocumentSelectionRevision.revision == revision,
        )
    )
    return result.scalar_one_or_none()


async def read_selection(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    purpose: str = TENDER_COMPARISON_PURPOSE,
    revision: int | None = None,
) -> TenderQuoteSelection:
    selection = await _selection_row(session, project_id=project_id, purpose=purpose)
    if selection is None:
        return TenderQuoteSelection(project_id=project_id, revision=0)
    wanted = selection.revision if revision is None else revision
    revision_row = await _revision_row(session, selection_id=selection.id, revision=wanted)
    if revision_row is None:
        raise SelectionValidationError(f"selection revision {wanted} does not exist")
    file_ids = [item.workspace_file_id for group in revision_row.groups for item in group.items]
    files: dict[uuid.UUID, WorkspaceFile] = {}
    if file_ids:
        result = await session.execute(select(WorkspaceFile).where(WorkspaceFile.id.in_(file_ids)))
        files = {row.id: row for row in result.scalars().all()}
    groups = []
    for group in sorted(revision_row.groups, key=lambda row: row.position):
        items = []
        for item in sorted(group.items, key=lambda row: row.position):
            file = files.get(item.workspace_file_id)
            if file is None or file.project_id != project_id:
                raise SelectionValidationError("selected workspace file is unavailable")
            items.append(SelectedWorkspaceFile(
                workspace_file_id=file.id,
                workspace_path=file.workspace_path,
                filename=file.filename,
                content_hash=file.content_hash,
                storage_bucket=file.storage_bucket,
                storage_key=file.storage_key,
                position=item.position,
            ))
        groups.append(TenderQuoteGroup(group_id=group.id, builder_name=group.label, position=group.position, files=items))
    return TenderQuoteSelection(
        selection_id=selection.id,
        selection_revision_id=revision_row.id,
        project_id=project_id,
        revision=revision_row.revision,
        selected_by=revision_row.selected_by,
        created_at=revision_row.created_at,
        quote_groups=groups,
    )


async def replace_selection(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    selected_by: uuid.UUID,
    expected_revision: int,
    quote_candidates: list[QuoteCandidateInput],
    actor_source: str,
) -> TenderQuoteSelection:
    if not 2 <= len(quote_candidates) <= 5 or any(not group.ordered_workspace_file_ids for group in quote_candidates):
        raise SelectionValidationError("Tender selection requires 2-5 non-empty quote groups")
    requested_ids = [file_id for group in quote_candidates for file_id in group.ordered_workspace_file_ids]
    if len(requested_ids) != len(set(requested_ids)):
        raise SelectionValidationError("a workspace file can belong to only one quote group")
    project_result = await session.execute(
        select(Project).where(Project.id == project_id).with_for_update()
    )
    locked_project = project_result.scalar_one_or_none()
    if locked_project is None:
        raise SelectionValidationError("Project not found")
    result = await session.execute(
        select(WorkspaceFile).where(WorkspaceFile.project_id == project_id, WorkspaceFile.id.in_(requested_ids))
    )
    owned_ids = {row.id for row in result.scalars().all()}
    if owned_ids != set(requested_ids):
        raise SelectionValidationError("every selected workspace file must belong to the project")

    selection = await _selection_row(session, project_id=project_id, purpose=TENDER_COMPARISON_PURPOSE, lock=True)
    if selection is None:
        if expected_revision != 0:
            raise SelectionRevisionConflict(expected_revision, 0)
        selection = ProjectDocumentSelection(project_id=project_id, purpose=TENDER_COMPARISON_PURPOSE, selected_by=selected_by)
        session.add(selection)
        await session.flush()
    elif selection.revision != expected_revision:
        raise SelectionRevisionConflict(expected_revision, selection.revision)

    selection.revision += 1
    selection.selected_by = selected_by
    revision_row = ProjectDocumentSelectionRevision(
        selection_id=selection.id, project_id=project_id, purpose=TENDER_COMPARISON_PURPOSE,
        revision=selection.revision, selected_by=selected_by,
    )
    session.add(revision_row)
    await session.flush()
    for group_position, candidate in enumerate(quote_candidates):
        group = ProjectDocumentSelectionGroup(
            selection_revision_id=revision_row.id, project_id=project_id,
            label=candidate.builder_name, position=group_position,
        )
        session.add(group)
        await session.flush()
        for file_position, file_id in enumerate(candidate.ordered_workspace_file_ids):
            session.add(ProjectDocumentSelectionItem(
                group_id=group.id, project_id=project_id,
                workspace_file_id=file_id, position=file_position,
            ))
    await session.flush()
    await publish_project_event(
        session, project_id=project_id, actor_source=actor_source,
        resource_type="project_document_selection", resource_id=selection.id,
        resource_revision=selection.revision, action="replaced",
        payload={"purpose": TENDER_COMPARISON_PURPOSE, "quote_group_count": len(quote_candidates)},
        locked_project=locked_project,
    )
    return await read_selection(session, project_id=project_id)


async def lock_workflow_inputs(
    session: AsyncSession, *, project_id: uuid.UUID, workflow_type: str,
    workflow_id: uuid.UUID, workspace_file_ids: list[uuid.UUID], state: str = "active",
) -> None:
    for file_id in workspace_file_ids:
        session.add(WorkflowInputRetentionLock(
            project_id=project_id, workspace_file_id=file_id, workflow_type=workflow_type,
            workflow_id=workflow_id, state=state,
        ))
    await session.flush()


async def file_has_retention_lock(session: AsyncSession, *, project_id: uuid.UUID, workspace_file_id: uuid.UUID) -> bool:
    result = await session.execute(select(WorkflowInputRetentionLock.id).where(
        WorkflowInputRetentionLock.project_id == project_id,
        WorkflowInputRetentionLock.workspace_file_id == workspace_file_id,
        WorkflowInputRetentionLock.state.in_(("active", "approved")),
    ).limit(1))
    return result.scalar_one_or_none() is not None
