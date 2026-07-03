"""The security seam: every tool call is authorized per project. Never bypass."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.projects import get_project, user_owns_project
from app.mcp_bridge.tokens import TurnTokenError, verify_turn_token


class ToolAuthError(Exception):
    """Raised when a tool call is not permitted; message is safe to show the model."""


async def authorize_project_access(
    session: AsyncSession,
    *,
    authorization_header: str | None,
    project_id: uuid.UUID,
):
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
    return project
