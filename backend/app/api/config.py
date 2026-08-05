from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.agent.pi_models import PiModelsResponse, pi_models_response
from app.assistant.chat_models import ChatModelsResponse, chat_models_response
from app.auth.dependencies import CurrentUser, get_current_user

router = APIRouter(prefix="/config", tags=["config"])


class AgentConfigurationResponse(BaseModel):
    agent: PiModelsResponse
    legacy: ChatModelsResponse


@router.get("/llm/models")
async def get_llm_models(
    user: CurrentUser = Depends(get_current_user),
) -> ChatModelsResponse:
    return chat_models_response()


@router.get("/agent/models")
async def get_agent_models(
    user: CurrentUser = Depends(get_current_user),
) -> PiModelsResponse:
    return pi_models_response()


@router.get("/agent")
async def get_agent_configuration(
    user: CurrentUser = Depends(get_current_user),
) -> AgentConfigurationResponse:
    return AgentConfigurationResponse(
        agent=pi_models_response(), legacy=chat_models_response()
    )
