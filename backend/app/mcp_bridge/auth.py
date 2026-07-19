"""The security seam: every tool call is authorized per project. Never bypass."""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.project import Project
from app.database.projects import get_project, user_owns_project
from app.mcp_bridge.tokens import TurnClaims
from app.mcp_bridge.tokens import TurnTokenError, verify_turn_token
from app.billing.usage import require_active_mutation_turn


class ToolAuthError(Exception):
    """Raised when a tool call is not permitted; message is safe to show the model."""


@dataclass(frozen=True, slots=True)
class ToolAuthorization:
    project: Project
    claims: TurnClaims


async def authorize_project_access(
    session: AsyncSession,
    *,
    authorization_header: str | None,
    project_id: uuid.UUID,
) -> Project:
    authorization = await authorize_project_access_with_claims(
        session,
        authorization_header=authorization_header,
        project_id=project_id,
    )
    return authorization.project


async def authorize_project_access_with_claims(
    session: AsyncSession,
    *,
    authorization_header: str | None,
    project_id: uuid.UUID,
) -> ToolAuthorization:
    if not authorization_header or not authorization_header.lower().startswith("bearer "):
        raise ToolAuthError("missing turn token")
    try:
        claims = verify_turn_token(authorization_header[7:])
    except TurnTokenError as exc:
        raise ToolAuthError(f"invalid turn token: {exc}") from exc
    if claims.project_id != project_id:
        raise ToolAuthError("turn token is not scoped to this project")
    project = await get_project(session, project_id)
    if project is None or not user_owns_project(project, claims.user_id):
        raise ToolAuthError("project not found or not accessible")
    return ToolAuthorization(project=project, claims=claims)


async def authorize_project_mutation_with_claims(
    session: AsyncSession,
    *,
    authorization_header: str | None,
    project_id: uuid.UUID,
    required_scope: str | None = None,
    requested_profile_patch: dict | None = None,
) -> ToolAuthorization:
    authorization = await authorize_project_access_with_claims(
        session,
        authorization_header=authorization_header,
        project_id=project_id,
    )
    turn_id = authorization.claims.turn_id
    if turn_id is None:
        raise ToolAuthError("mutation requires a durable turn capability")
    try:
        await require_active_mutation_turn(
            session,
            turn_id=turn_id,
            project_id=project_id,
            user_id=authorization.claims.user_id,
            required_scope=required_scope,
            requested_profile_patch=requested_profile_patch,
        )
    except PermissionError as exc:
        raise ToolAuthError(str(exc)) from exc
    return authorization
