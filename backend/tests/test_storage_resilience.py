"""Storage-layer resilience against transient HTTP transport failures.

Regression cover for the tender ingest outage of 2026-07-18: a single
process-wide Supabase client multiplexed every page-image upload over one
HTTP/2 connection, so when that connection dropped, httpcore poisoned it and
every concurrent upload died at once with ``RemoteProtocolError`` — with no
retry at any layer, each ingest job burned all three attempts.
"""

from __future__ import annotations

import httpx
import pytest

from app.storage import project_files


class _FlakyBucket:
    """Storage bucket that fails the first ``failures`` calls, then succeeds."""

    def __init__(self, failures: int, exc: Exception | None = None) -> None:
        self.failures = failures
        self.exc = exc or httpx.RemoteProtocolError("Server disconnected")
        self.upload_calls = 0
        self.download_calls = 0

    def upload(self, *args, **kwargs):
        self.upload_calls += 1
        if self.upload_calls <= self.failures:
            raise self.exc
        return {"Key": "ok"}

    def download(self, *args, **kwargs):
        self.download_calls += 1
        if self.download_calls <= self.failures:
            raise self.exc
        return b"payload"


class _FakeClient:
    def __init__(self, bucket: _FlakyBucket) -> None:
        self._bucket = bucket
        self.storage = self

    def from_(self, _bucket_name: str) -> _FlakyBucket:
        return self._bucket


@pytest.fixture
def patch_client(monkeypatch):
    def _install(bucket: _FlakyBucket) -> _FlakyBucket:
        monkeypatch.setattr(
            project_files, "get_service_client", lambda: _FakeClient(bucket)
        )
        # Keep the suite fast: no real backoff sleeping.
        monkeypatch.setattr(project_files.time, "sleep", lambda _seconds: None)
        return bucket

    return _install


def test_upload_retries_after_server_disconnect(patch_client):
    bucket = patch_client(_FlakyBucket(failures=2))

    key = project_files.upload_project_file(
        storage_key="tender/page-0001.png", content=b"png", filename="page-0001.png"
    )

    assert key == "tender/page-0001.png"
    assert bucket.upload_calls == 3, "should retry twice then succeed"


def test_download_retries_after_server_disconnect(patch_client):
    bucket = patch_client(_FlakyBucket(failures=1))

    assert project_files.download_project_file(storage_key="quotes/q.pdf") == b"payload"
    assert bucket.download_calls == 2


def test_upload_gives_up_after_max_attempts(patch_client):
    bucket = patch_client(_FlakyBucket(failures=99))

    with pytest.raises(httpx.RemoteProtocolError):
        project_files.upload_project_file(
            storage_key="tender/page-0001.png", content=b"png", filename="page.png"
        )

    assert bucket.upload_calls == project_files.STORAGE_MAX_ATTEMPTS


def test_non_transport_errors_are_not_retried(patch_client):
    """A genuine 4xx must fail fast — retrying it just wastes the job's attempts."""

    bucket = patch_client(_FlakyBucket(failures=99, exc=ValueError("bad bucket")))

    with pytest.raises(ValueError):
        project_files.upload_project_file(
            storage_key="tender/page-0001.png", content=b"png", filename="page.png"
        )

    assert bucket.upload_calls == 1


def test_service_client_does_not_multiplex_over_http2():
    """Lanes must not share one HTTP/2 connection.

    With ``http2=True`` a single dropped connection takes down every in-flight
    upload across all worker lanes simultaneously.
    """

    from app.database import supabase

    client_options = supabase.build_client_options()

    assert client_options.httpx_client is not None, (
        "must inject an explicit httpx client rather than accept storage3's "
        "http2=True default"
    )
    # httpx exposes the negotiated protocols via the transport's pool.
    pool = client_options.httpx_client._transport._pool
    assert pool._http2 is False
    assert pool._http1 is True
