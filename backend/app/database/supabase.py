from functools import lru_cache

import httpx
from supabase import Client, create_client
from supabase.lib.client_options import SyncClientOptions

from app.config import settings

# storage3 builds its httpx client with ``http2=True``, which multiplexes every
# request from the whole process onto a single TCP connection. When that
# connection drops, httpcore caches the error on the connection object and
# re-raises it for every in-flight stream, so one dead socket fails all the
# worker lanes uploading page images at once. HTTP/1.1 gives each concurrent
# caller its own pooled connection, keeping a failure local to one request.
_STORAGE_LIMITS = httpx.Limits(max_connections=20, max_keepalive_connections=10)
_STORAGE_TIMEOUT = httpx.Timeout(connect=10.0, read=60.0, write=60.0, pool=10.0)


def build_client_options() -> SyncClientOptions:
    """Client options pinning Supabase HTTP traffic to HTTP/1.1."""

    return SyncClientOptions(
        httpx_client=httpx.Client(
            http1=True,
            http2=False,
            limits=_STORAGE_LIMITS,
            timeout=_STORAGE_TIMEOUT,
        )
    )


@lru_cache
def get_service_client() -> Client:
    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
        build_client_options(),
    )


def get_user_client(access_token: str) -> Client:
    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    client.postgrest.auth(access_token)
    return client
