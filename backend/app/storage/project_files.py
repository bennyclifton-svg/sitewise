import mimetypes
import time
from typing import Callable, TypeVar

import httpx
import structlog

from app.config import settings
from app.database.supabase import get_service_client
from app.storage.keys import sanitize_storage_key

logger = structlog.get_logger(__name__)

T = TypeVar("T")

STORAGE_MAX_ATTEMPTS = 3
STORAGE_BACKOFF_BASE_SECONDS = 0.5

# Connection-level faults only. A dropped keep-alive connection says nothing
# about the request, so replaying it is safe; a 4xx/5xx from the storage API is
# a real answer and must surface immediately rather than burn the job's retries.
TRANSIENT_TRANSPORT_ERRORS = (
    httpx.RemoteProtocolError,
    httpx.ConnectError,
    httpx.ReadError,
    httpx.WriteError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
)


def _with_transport_retry(operation: str, storage_key: str, call: Callable[[], T]) -> T:
    """Run ``call``, replaying it when the HTTP connection drops underneath us.

    Supabase's edge closes idle or long-lived connections; the page-image upload
    loop in tender ingest is a burst of dozens of sequential requests, so it hits
    that window regularly. Without this, a single closed socket fails an entire
    multi-page document.
    """

    for attempt in range(1, STORAGE_MAX_ATTEMPTS + 1):
        try:
            return call()
        except TRANSIENT_TRANSPORT_ERRORS as exc:
            if attempt == STORAGE_MAX_ATTEMPTS:
                logger.error(
                    "storage_transport_error_exhausted",
                    operation=operation,
                    storage_key=storage_key,
                    attempts=attempt,
                    error=f"{type(exc).__name__}: {exc}",
                )
                raise
            backoff = STORAGE_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
            logger.warning(
                "storage_transport_error_retrying",
                operation=operation,
                storage_key=storage_key,
                attempt=attempt,
                backoff_seconds=backoff,
                error=f"{type(exc).__name__}: {exc}",
            )
            time.sleep(backoff)

    raise AssertionError("unreachable")  # pragma: no cover


def _content_type(filename: str) -> str:
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


def upload_project_file(*, storage_key: str, content: bytes, filename: str) -> str:
    storage_key = sanitize_storage_key(storage_key)
    bucket = settings.supabase_storage_bucket
    content_type = _content_type(filename)

    def _upload() -> None:
        get_service_client().storage.from_(bucket).upload(
            storage_key,
            content,
            file_options={"content-type": content_type, "upsert": "true"},
        )

    _with_transport_retry("upload", storage_key, _upload)
    logger.info("storage_uploaded", bucket=bucket, storage_key=storage_key, size_bytes=len(content))
    return storage_key


def download_project_file(*, storage_key: str) -> bytes:
    bucket = settings.supabase_storage_bucket

    def _download():
        return get_service_client().storage.from_(bucket).download(storage_key)

    payload = _with_transport_retry("download", storage_key, _download)
    if isinstance(payload, bytes):
        return payload
    return bytes(payload)


def delete_project_file(*, storage_key: str) -> None:
    bucket = settings.supabase_storage_bucket
    client = get_service_client()
    client.storage.from_(bucket).remove([storage_key])
    logger.info("storage_deleted", bucket=bucket, storage_key=storage_key)


def delete_project_files(*, storage_keys: list[str]) -> None:
    """Remove several object-storage files in a single storage API call.

    Intended to run as a background task after the database delete has already
    committed, so a slow or failing storage round-trip never blocks the
    response. Failures are logged, not raised.
    """

    keys = [key for key in storage_keys if key]
    if not keys:
        return

    bucket = settings.supabase_storage_bucket
    client = get_service_client()
    try:
        client.storage.from_(bucket).remove(keys)
        logger.info("storage_deleted_batch", bucket=bucket, count=len(keys))
    except Exception:
        logger.warning("storage_delete_batch_failed", bucket=bucket, storage_keys=keys)


def move_project_file(
    *,
    source_key: str,
    destination_key: str,
    content: bytes,
    filename: str,
) -> str:
    upload_project_file(
        storage_key=destination_key,
        content=content,
        filename=filename,
    )
    delete_project_file(storage_key=source_key)
    logger.info(
        "storage_moved",
        source_key=source_key,
        destination_key=destination_key,
        size_bytes=len(content),
    )
    return destination_key
