from fastapi import APIRouter, Depends

from app.agent.hermes_models import HermesModelsResponse, hermes_models_response
from app.assistant.chat_models import ChatModelsResponse, chat_models_response
from app.auth.dependencies import CurrentUser, get_current_user
from app.database.session import get_db
from app.database.users import ensure_user_exists
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/llm/models")
async def get_llm_models(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ChatModelsResponse:
    await ensure_user_exists(session, user)
    return chat_models_response()


@router.get("/agent/models")
async def get_agent_models(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> HermesModelsResponse:
    await ensure_user_exists(session, user)
    return hermes_models_response()
