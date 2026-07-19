from contextlib import asynccontextmanager
import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

import app.database.models  # noqa: F401 — register all SQLAlchemy mappers before API routes
from app.api.auth import router as auth_router
from app.api.billing import router as billing_router
from app.api.chat import router as chat_router
from app.api.config import router as config_router
from app.api.projects import router as projects_router
from app.api.projects import sitewise_router
from app.config import settings
from app.database.session import get_engine
from app.logging import configure_logging, get_logger
from app.mcp_bridge.server import mcp
from app.tender_worker import start_inprocess_tender_worker, stop_inprocess_tender_worker
from tender.router import router as tender_router
from tender.services.artefact_publisher import configure_tender_artefact_publisher
from app.projects.tender_artefact_adapter import CoreTenderArtefactPublisher

configure_logging()
configure_tender_artefact_publisher(CoreTenderArtefactPublisher())
log = get_logger(__name__)
_access_log = logging.getLogger("clerk.access")

mcp_app = mcp.http_app(path="/")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    log.info(
        "clerk_backend_started",
        chat_model=settings.openai_chat_model,
        pmp_model=settings.pmp_model,
        pmp_model_provider=settings.pmp_model_provider,
        pmp_model_label=settings.pmp_model_label,
        hermes_model=settings.hermes_model,
        hermes_model_provider=settings.hermes_model_provider,
        pi_model=settings.pi_model,
        pi_model_provider=settings.pi_model_provider,
        embedding_model=settings.openai_embedding_model,
        log_level=settings.log_level,
    )
    # The MCP session manager needs its own lifespan running alongside ours.
    worker_handle = await start_inprocess_tender_worker()
    try:
        async with mcp_app.lifespan(_app):
            yield
    finally:
        await stop_inprocess_tender_worker(worker_handle)
        await get_engine().dispose()


fastapi_app = FastAPI(title="Clerk API", lifespan=lifespan)


@fastapi_app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    start_line = f"-> {request.method} {request.url.path}"
    _access_log.info(start_line)
    response = await call_next(request)
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    end_line = f"<- {request.method} {request.url.path} {response.status_code} ({elapsed_ms}ms)"
    _access_log.info(end_line)
    return response


@fastapi_app.exception_handler(SQLAlchemyError)
async def database_error_handler(request: Request, exc: SQLAlchemyError):
    log.exception("database_error", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Database unavailable. Check DATABASE_URL and network access.",
        },
    )


fastapi_app.include_router(auth_router)
fastapi_app.include_router(billing_router)
fastapi_app.include_router(config_router)
fastapi_app.include_router(chat_router)
fastapi_app.include_router(projects_router)
fastapi_app.include_router(sitewise_router)
fastapi_app.include_router(tender_router)
fastapi_app.mount("/mcp", mcp_app)


@fastapi_app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "chat_model": settings.openai_chat_model,
        "chat_provider": f"openai-chat:{settings.openai_chat_model}",
        "pmp_model": settings.pmp_model,
        "pmp_model_provider": settings.pmp_model_provider,
        "pmp_model_label": settings.pmp_model_label,
        "hermes_model": settings.hermes_model,
        "hermes_model_provider": settings.hermes_model_provider,
        "pi_model": settings.pi_model,
        "pi_model_provider": settings.pi_model_provider,
        "embedding_model": settings.openai_embedding_model,
    }


app = CORSMiddleware(
    fastapi_app,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
