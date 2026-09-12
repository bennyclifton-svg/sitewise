from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user
from app.database.prompt_library import PromptLibrary
from app.database.session import get_db
from app.database.users import ensure_user_exists

router = APIRouter(prefix="/prompt-library", tags=["prompt-library"])


class SavedPrompt(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    id: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    title: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=12000)


class SavePromptLibrary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=0)
    prompts: list[SavedPrompt] = Field(max_length=100)

    @field_validator("prompts")
    @classmethod
    def unique_ids(cls, prompts: list[SavedPrompt]) -> list[SavedPrompt]:
        if len({prompt.id for prompt in prompts}) != len(prompts):
            raise ValueError("Prompt IDs must be unique")
        return prompts


class PromptLibraryResponse(BaseModel):
    version: int
    prompts: list[SavedPrompt] | None


@router.get("", response_model=PromptLibraryResponse)
async def get_prompt_library(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PromptLibraryResponse:
    library = await session.get(PromptLibrary, user.id)
    if library is None:
        return PromptLibraryResponse(version=0, prompts=None)
    return PromptLibraryResponse(version=library.version, prompts=library.prompts)


@router.put("", response_model=PromptLibraryResponse)
async def save_prompt_library(
    body: SavePromptLibrary,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PromptLibraryResponse:
    prompts = [prompt.model_dump() for prompt in body.prompts]
    version = body.expected_version + 1
    if body.expected_version == 0:
        await ensure_user_exists(session, user)
        statement = (
            insert(PromptLibrary)
            .values(user_id=user.id, version=version, prompts=prompts)
            .on_conflict_do_nothing(index_elements=[PromptLibrary.user_id])
            .returning(PromptLibrary.version)
        )
    else:
        statement = (
            update(PromptLibrary)
            .where(
                PromptLibrary.user_id == user.id,
                PromptLibrary.version == body.expected_version,
            )
            .values(version=version, prompts=prompts)
            .returning(PromptLibrary.version)
        )
    saved_version = (await session.execute(statement)).scalar_one_or_none()
    if saved_version is None:
        raise HTTPException(
            409, "Your prompt library changed elsewhere. Reload it before saving again."
        )
    return PromptLibraryResponse(version=saved_version, prompts=body.prompts)
