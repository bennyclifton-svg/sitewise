from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.database.session import get_db
from app.main import fastapi_app as app
from tender import worker
from tender.services import qa, report

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
COMPARISON_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
REPORT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
DRAFT_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
NOW = datetime(2026, 6, 13, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def client(mock_session: AsyncMock) -> TestClient:
    current_user = CurrentUser(id=USER_ID, email="operator@example.com")

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: current_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_build_report_endpoint_blocks_pending_review(client: TestClient) -> None:
    with (
        patch("tender.router.require_comparison_owner", new=AsyncMock()),
        patch("tender.router.require_active_entitlement", new=AsyncMock()),
        patch(
            "tender.router.report.build_report_draft",
            new=AsyncMock(side_effect=qa.PendingReviewError("pending review")),
        ),
    ):
        response = client.post(f"/api/tender/comparisons/{COMPARISON_ID}/report/build")

    assert response.status_code == 409
    assert response.json()["detail"] == "Comparison has QA items still needing review"


def test_build_approve_and_deliver_report_endpoints(client: TestClient) -> None:
    built = _lifecycle(status="report_draft", html_path="draft.html", pdf_path="draft.pdf")
    approved = _lifecycle(
        status="approved",
        html_path="final.html",
        pdf_path="final.pdf",
        approved_at=NOW,
    )
    delivered = _lifecycle(
        status="delivered",
        html_path="final.html",
        pdf_path="final.pdf",
        approved_at=NOW,
        delivered_at=NOW,
    )

    with (
        patch("tender.router.require_comparison_owner", new=AsyncMock()),
        patch("tender.router.require_active_entitlement", new=AsyncMock()),
        patch("tender.router.report.build_report_draft", new=AsyncMock(return_value=built)),
        patch("tender.router.report.approve_report", new=AsyncMock(return_value=approved)),
        patch(
            "tender.router.report.mark_report_delivered",
            new=AsyncMock(return_value=delivered),
        ),
    ):
        build_response = client.post(
            f"/api/tender/comparisons/{COMPARISON_ID}/report/build"
        )
        approve_response = client.post(
            f"/api/tender/comparisons/{COMPARISON_ID}/report/approve"
        )
        delivered_response = client.post(
            f"/api/tender/comparisons/{COMPARISON_ID}/report/delivered",
            json={"delivery_note": "Sent to owner"},
        )

    assert build_response.status_code == 200
    assert build_response.json()["status"] == "report_draft"
    assert approve_response.status_code == 200
    assert approve_response.json()["approved_at"] == NOW.isoformat().replace("+00:00", "Z")
    assert approve_response.json()["pdf_path"] == "final.pdf"
    assert delivered_response.status_code == 200
    assert delivered_response.json()["status"] == "delivered"


def test_worker_registers_report_assembly_handler() -> None:
    assert worker.HANDLERS["assemble_report_draft"] is report.assemble_report_draft


def test_approve_report_endpoint_maps_weasyprint_unavailable(
    client: TestClient,
) -> None:
    provider_detail = "native-library-secret-" + ("x" * 24)
    with (
        patch("tender.router.require_comparison_owner", new=AsyncMock()),
        patch("tender.router.require_active_entitlement", new=AsyncMock()),
        patch(
            "tender.router.report.approve_report",
            new=AsyncMock(
                side_effect=report.WeasyPrintUnavailable(provider_detail)
            ),
        ),
    ):
        response = client.post(
            f"/api/tender/comparisons/{COMPARISON_ID}/report/approve"
        )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Tender PDF generation is temporarily unavailable. Please try again."
    }
    assert provider_detail not in response.text


def test_build_report_endpoint_hides_weasyprint_error(client: TestClient) -> None:
    provider_detail = "native-library-secret-" + ("x" * 24)
    with (
        patch("tender.router.require_comparison_owner", new=AsyncMock()),
        patch("tender.router.require_active_entitlement", new=AsyncMock()),
        patch(
            "tender.router.report.build_report_draft",
            new=AsyncMock(
                side_effect=report.WeasyPrintUnavailable(provider_detail)
            ),
        ),
    ):
        response = client.post(
            f"/api/tender/comparisons/{COMPARISON_ID}/report/build"
        )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Tender PDF generation is temporarily unavailable. Please try again."
    }
    assert provider_detail not in response.text


def test_approve_report_endpoint_blocks_unapproved_customer_quality_gate(
    client: TestClient,
) -> None:
    with (
        patch("tender.router.require_comparison_owner", new=AsyncMock()),
        patch("tender.router.require_active_entitlement", new=AsyncMock()),
        patch(
            "tender.router.report.approve_report",
            new=AsyncMock(
                side_effect=report.CustomerQualityGateError(
                    ["QS review is not approved"]
                )
            ),
        ),
    ):
        response = client.post(
            f"/api/tender/comparisons/{COMPARISON_ID}/report/approve"
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "Tender customer quality gate is blocked"


def test_report_pdf_endpoint_downloads_generated_bytes(client: TestClient) -> None:
    with (
        patch("tender.router.require_comparison_owner", new=AsyncMock()),
        patch(
            "tender.router.report.load_report_pdf",
            new=AsyncMock(return_value=(b"%PDF-tender", "Tender_Comparison_Report_v02.pdf")),
        ),
    ):
        response = client.get(f"/api/tender/comparisons/{COMPARISON_ID}/report/pdf")

    assert response.status_code == 200
    assert response.content == b"%PDF-tender"
    assert response.headers["content-type"] == "application/pdf"
    assert "Tender_Comparison_Report_v02.pdf" in response.headers["content-disposition"]


def test_load_report_pdf_converts_html_when_pdf_path_is_missing() -> None:
    record = SimpleNamespace(
        version=2,
        pdf_path=None,
        html_path="reports/draft.html",
    )

    async def run() -> tuple[bytes, str]:
        session = AsyncMock()
        with (
            patch(
                "tender.services.report._latest_report",
                new=AsyncMock(return_value=record),
            ),
            patch(
                "tender.services.report.download_project_file",
                new=MagicMock(return_value=b"<html>draft</html>"),
            ),
            patch(
                "tender.services.report.render_pdf_bytes",
                new=MagicMock(return_value=b"%PDF-from-html"),
            ),
            patch("tender.services.report.upload_project_file", new=MagicMock()),
        ):
            return await report.load_report_pdf(session, comparison_id=COMPARISON_ID)

    content, filename = asyncio.run(run())
    assert content == b"%PDF-from-html"
    assert filename == "Tender_Comparison_Report_v02.pdf"
    assert record.pdf_path == "reports/draft.pdf"


def test_report_pdf_endpoint_maps_missing_report(client: TestClient) -> None:
    with (
        patch("tender.router.require_comparison_owner", new=AsyncMock()),
        patch(
            "tender.router.report.load_report_pdf",
            new=AsyncMock(side_effect=report.ReportLifecycleError("missing")),
        ),
    ):
        response = client.get(f"/api/tender/comparisons/{COMPARISON_ID}/report/pdf")

    assert response.status_code == 404
    assert response.json() == {"detail": "Tender report PDF is not available."}


def _lifecycle(
    *,
    status: str,
    html_path: str,
    pdf_path: str,
    approved_at: datetime | None = None,
    delivered_at: datetime | None = None,
) -> report.ReportLifecycleResult:
    return report.ReportLifecycleResult(
        report_id=REPORT_ID,
        comparison_id=COMPARISON_ID,
        draft_id=DRAFT_ID,
        version=2,
        html_path=html_path,
        pdf_path=pdf_path,
        status=status,
        approved_at=approved_at,
        delivered_at=delivered_at,
    )
