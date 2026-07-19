from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class QuoteCandidateInput(BaseModel):
    builder_name: str = Field(min_length=1, max_length=512)
    ordered_workspace_file_ids: list[uuid.UUID] = Field(min_length=1)

    @field_validator("builder_name")
    @classmethod
    def strip_builder_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("ordered_workspace_file_ids")
    @classmethod
    def unique_files(cls, value: list[uuid.UUID]) -> list[uuid.UUID]:
        if len(value) != len(set(value)):
            raise ValueError("a quote group cannot contain the same file twice")
        return value


class ReplaceTenderQuoteSelection(BaseModel):
    expected_revision: int = Field(ge=0)
    quote_candidates: list[QuoteCandidateInput] = Field(min_length=2, max_length=5)

    @model_validator(mode="after")
    def unique_files_across_groups(self) -> "ReplaceTenderQuoteSelection":
        file_ids = [file_id for group in self.quote_candidates for file_id in group.ordered_workspace_file_ids]
        if len(file_ids) != len(set(file_ids)):
            raise ValueError("a workspace file can belong to only one quote group")
        return self


class SelectedWorkspaceFile(BaseModel):
    workspace_file_id: uuid.UUID
    workspace_path: str
    filename: str
    content_hash: str
    storage_bucket: str
    storage_key: str
    position: int


class TenderQuoteGroup(BaseModel):
    group_id: uuid.UUID
    builder_name: str
    position: int
    files: list[SelectedWorkspaceFile]


class TenderQuoteSelection(BaseModel):
    selection_id: uuid.UUID | None = None
    selection_revision_id: uuid.UUID | None = None
    project_id: uuid.UUID
    purpose: Literal["tender_comparison"] = "tender_comparison"
    revision: int = Field(ge=0)
    selected_by: uuid.UUID | None = None
    created_at: datetime | None = None
    quote_groups: list[TenderQuoteGroup] = Field(default_factory=list)
