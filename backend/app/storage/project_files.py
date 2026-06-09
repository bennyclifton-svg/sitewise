import mimetypes

import structlog

from app.config import settings
from app.database.supabase import get_service_client

logger = structlog.get_logger(__name__)


def _content_type(filename: str) -> str:
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


def upload_project_file(*, storage_key: str, content: bytes, filename: str) -> str:
    bucket = settings.supabase_storage_bucket
    client = get_service_client()
    client.storage.from_(bucket).upload(
        storage_key,
        content,
        file_options={"content-type": _content_type(filename), "upsert": "true"},
    )
    logger.info("storage_uploaded", bucket=bucket, storage_key=storage_key, size_bytes=len(content))
    return storage_key


def download_project_file(*, storage_key: str) -> bytes:
    bucket = settings.supabase_storage_bucket
    client = get_service_client()
    payload = client.storage.from_(bucket).download(storage_key)
    if isinstance(payload, bytes):
        return payload
    return bytes(payload)


def delete_project_file(*, storage_key: str) -> None:
    bucket = settings.supabase_storage_bucket
    client = get_service_client()
    client.storage.from_(bucket).remove([storage_key])
    logger.info("storage_deleted", bucket=bucket, storage_key=storage_key)


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
