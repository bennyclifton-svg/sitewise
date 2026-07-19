import uuid
import time
from dataclasses import dataclass

import httpx
import structlog
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

logger = structlog.get_logger(__name__)
security = HTTPBearer(auto_error=False)
_AUTH_CACHE_TTL_SECONDS = 60.0
_AUTH_CACHE_MAX_SIZE = 512
_auth_user_cache: dict[str, tuple[float, dict]] = {}


@dataclass(frozen=True, slots=True)
class CurrentUser:
    id: uuid.UUID
    email: str


def create_auth_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=5.0),
        limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
    )


async def _fetch_supabase_user(client: httpx.AsyncClient, access_token: str) -> dict:
    start = time.perf_counter()
    response = await client.get(
        f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
        headers={
            "Authorization": f"Bearer {access_token}",
            "apikey": settings.supabase_anon_key,
        },
    )
    elapsed_ms = int((time.perf_counter() - start) * 1000)

    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    payload = response.json()
    logger.info("auth_user_verified", auth_path="cold", elapsed_ms=elapsed_ms)
    user = payload.get("user", payload)
    if not isinstance(user, dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    return user


async def _verified_supabase_user(
    client: httpx.AsyncClient, access_token: str
) -> dict:
    start = time.perf_counter()
    now = time.monotonic()
    cached = _auth_user_cache.get(access_token)
    if cached is not None:
        expires_at, user = cached
        if expires_at > now:
            logger.info(
                "auth_user_verified",
                auth_path="warm_cache",
                elapsed_ms=int((time.perf_counter() - start) * 1000),
            )
            return user
        _auth_user_cache.pop(access_token, None)

    user = await _fetch_supabase_user(client, access_token)
    if len(_auth_user_cache) >= _AUTH_CACHE_MAX_SIZE:
        _auth_user_cache.clear()
    _auth_user_cache[access_token] = (now + _AUTH_CACHE_TTL_SECONDS, user)
    return user


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> CurrentUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
        )

    client: httpx.AsyncClient = request.app.state.auth_http_client
    user = await _verified_supabase_user(client, credentials.credentials)
    user_id = user.get("id")
    email = user.get("email")
    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    return CurrentUser(id=uuid.UUID(str(user_id)), email=str(email))
