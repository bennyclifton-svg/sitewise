import uuid
from datetime import datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class CreateThreadRequest(BaseModel):
    title: str | None = Field(default=None, max_length=512)
    project_id: uuid.UUID | None = Field(
        default=None,
        validation_alias=AliasChoices("projectId", "project_id"),
    )


class UpdateThreadRequest(BaseModel):
    title: str = Field(min_length=1, max_length=512)


class ThreadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID | None
    title: str | None
    hermes_session_id: str | None = None
    created_at: datetime
    updated_at: datetime


class ThreadListResponse(BaseModel):
    threads: list[ThreadResponse]


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    message_data: dict | None
    created_at: datetime


class MessageListResponse(BaseModel):
    messages: list[MessageResponse]


class StreamChatRequest(BaseModel):
    thread_id: uuid.UUID = Field(
        validation_alias=AliasChoices("threadId", "thread_id", "id"),
    )
    messages: list[dict[str, Any]] = Field(default_factory=list)
    chat_model: str | None = Field(
        default=None,
        max_length=128,
        validation_alias=AliasChoices("chatModel", "chat_model"),
    )
    agent_model: str | None = Field(
        default=None,
        max_length=256,
        validation_alias=AliasChoices("agentModel", "agent_model"),
    )

    @field_validator("chat_model")
    @classmethod
    def validate_chat_model(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None
        from app.assistant.chat_models import InvalidChatModelError, resolve_chat_model

        try:
            return resolve_chat_model(stripped)
        except InvalidChatModelError as exc:
            raise ValueError(str(exc)) from exc

    @field_validator("agent_model")
    @classmethod
    def validate_agent_model(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None
        from app.agent.hermes_models import (
            HERMES_DEFAULT_MODEL_ID,
            InvalidHermesModelError,
            resolve_hermes_model_override,
        )

        if stripped == HERMES_DEFAULT_MODEL_ID:
            return None
        try:
            resolve_hermes_model_override(stripped)
        except InvalidHermesModelError as exc:
            raise ValueError(str(exc)) from exc
        return stripped
