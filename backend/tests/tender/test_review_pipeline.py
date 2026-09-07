import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.procurement.strategy import (
    ProcurementStrategyConflict,
    ProcurementStrategyValidationError,
)
from tender.models import TenderDocument, TenderQuote
from tender.review_schemas import ReviewExtraction
from tender.services import procurement_intake
from tender.services.review_extraction import extract_review_window
from tender.services import review_extraction
from tender.services.review_dates import printed_dates, normalize_source_dates
from tests.conftest import run_async


def test_many_files_become_one_quote_per_firm_and_intake_replays():
    async def exercise():
        project_id, owner_id, row_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        files = [
            SimpleNamespace(
                id=uuid.uuid4(),
                content_hash=str(i) * 64,
                workspace_path=f"quotes/{i}.pdf",
                filename=f"{i}.pdf",
                storage_key=f"objects/{i}",
                storage_bucket="project-files",
            )
            for i in range(3)
        ]
        candidates = [
            SimpleNamespace(
                id=uuid.uuid4(),
                slot=i,
                company_name=f"Firm {i}",
                submission_files=[
                    SimpleNamespace(workspace_file_id=f.id) for f in group
                ],
            )
            for i, group in enumerate([files[:2], files[2:]])
        ]
        row = SimpleNamespace(
            id=row_id,
            submission_revision=4,
            candidates=candidates,
            discipline_code="consultant.structural",
            discipline_label="Structural",
            participant_type="consultant",
            request_kind="consultant_rfp",
            recommendation_draft_id=None,
            status="responses_received",
        )
        session = AsyncMock()

        def add(record):
            record.id = record.id or uuid.uuid4()

        session.add = MagicMock(side_effect=add)
        session.scalar.side_effect = [SimpleNamespace(id=project_id), row, None]
        args = dict(
            project_id=project_id,
            row_id=row_id,
            owner_user_id=owner_id,
            expected_submission_revision=4,
        )
        with (
            patch.object(
                procurement_intake,
                "resolve_submission_files",
                AsyncMock(side_effect=[files[:2], files[2:]]),
            ),
            patch.object(procurement_intake, "lock_workflow_inputs", AsyncMock()),
            patch.object(procurement_intake.jobs, "enqueue", AsyncMock()) as enqueue,
        ):
            comparison = await procurement_intake.start_procurement_review(
                session, **args
            )
            records = [call.args[0] for call in session.add.call_args_list]
            assert len([r for r in records if isinstance(r, TenderQuote)]) == 2
            documents = [r for r in records if isinstance(r, TenderDocument)]
            assert len(documents) == enqueue.await_count == 3
            assert (
                documents[0].quote_id == documents[1].quote_id != documents[2].quote_id
            )
            assert comparison.context["review_profile"] == "consultant"
            assert (
                comparison.context_provenance["submissions"][0]["files"][1]["hash"]
                == "1" * 64
            )
        session.scalar.side_effect = [SimpleNamespace(id=project_id), row, comparison]
        session.add.reset_mock()
        with patch.object(
            procurement_intake,
            "resolve_submission_files",
            AsyncMock(side_effect=[files[:2], files[2:]]),
        ):
            assert (
                await procurement_intake.start_procurement_review(session, **args)
                is comparison
            )
            session.add.assert_not_called()
        session.scalar.side_effect = [
            SimpleNamespace(id=project_id),
            row,
            comparison,
            None,
        ]
        session.add.reset_mock()
        with (
            patch.object(
                procurement_intake,
                "resolve_submission_files",
                AsyncMock(side_effect=[files[:2], files[2:]]),
            ),
            patch.object(procurement_intake, "lock_workflow_inputs", AsyncMock()),
            patch.object(procurement_intake.jobs, "enqueue", AsyncMock()) as enqueue,
        ):
            replacement = await procurement_intake.start_procurement_review(
                session, **args, rerun=True
            )
            assert replacement.id != comparison.id
            assert enqueue.await_count == 3
            assert (
                replacement.context_provenance["submissions"]
                == comparison.context_provenance["submissions"]
            )
        session.scalar.side_effect = [
            SimpleNamespace(id=project_id),
            row,
            replacement,
            uuid.uuid4(),
        ]
        session.add.reset_mock()
        with patch.object(
            procurement_intake,
            "resolve_submission_files",
            AsyncMock(side_effect=[files[:2], files[2:]]),
        ):
            assert (
                await procurement_intake.start_procurement_review(
                    session, **args, rerun=True
                )
                is replacement
            )
            session.add.assert_not_called()
        session.scalar.side_effect = [None]
        with pytest.raises(
            ProcurementStrategyValidationError, match="Project not found"
        ):
            await procurement_intake.start_procurement_review(session, **args)
        session.scalar.side_effect = [SimpleNamespace(id=project_id), row]
        with pytest.raises(ProcurementStrategyConflict):
            await procurement_intake.start_procurement_review(
                session, **{**args, "expected_submission_revision": 3}
            )

    run_async(exercise())


def test_dates_are_grounded_in_printed_values_not_model_generated_years():
    assert printed_dates("30.06.2026; Jul 6th, 2026; 4/7/2026") == [
        "2026-06-30",
        "2026-07-06",
        "2026-07-04",
    ]
    result = ReviewExtraction(
        coverage=[{"page_no": 2, "readable": True, "blank": False}],
        facts=[
            {
                "page_no": 2,
                "label": "Validity",
                "kind": "validity",
                "excerpt": "Quote valid for 30 days",
                "issued_on": "4847-07-04",
                "validity_days": 30,
            }
        ],
    )
    normalize_source_dates(
        result, {2: "Quote valid for 30 days"}, "Quote Date: 4/7/2026"
    )
    assert result.facts[0].issued_on == "2026-07-04"
    assert result.facts[0].validity_days == 30


@pytest.mark.parametrize(
    ("opening_page", "expected_date"),
    [("Proposal date | 26 June 2025 |", "2025-06-26"), ("Fee proposal", None)],
)
def test_invalid_model_dates_are_corrected_before_calendar_validation(
    opening_page, expected_date
):
    async def exercise():
        source = "| Validity | 60 days |\nSupporting proposal terms and conditions."
        client = SimpleNamespace(
            request=AsyncMock(
                return_value=ReviewExtraction(
                    coverage=[{"page_no": 1, "readable": True, "blank": False}],
                    facts=[
                        {
                            "page_no": 1,
                            "kind": "validity",
                            "label": "Offer validity",
                            "excerpt": "| Validity | 60 days |",
                            "issued_on": "2606-26-26",
                            "valid_until": "2025-08-60",
                            "validity_days": 60,
                        }
                    ],
                )
            )
        )
        image_loader = AsyncMock()
        result, missing = await extract_review_window(
            [SimpleNamespace(page_no=1, text_content=source, image_path="page-1")],
            client=client,
            context={"opening_page_context": opening_page},
            image_loader=image_loader,
        )
        assert result.facts[0].issued_on == expected_date
        assert result.facts[0].valid_until is None
        assert result.facts[0].validity_days == 60
        assert not missing
        client.request.assert_awaited_once()
        image_loader.assert_not_awaited()

    run_async(exercise())


def test_date_normalization_does_not_bypass_source_page_validation():
    async def exercise():
        client = SimpleNamespace(
            request=AsyncMock(
                return_value=ReviewExtraction(
                    coverage=[{"page_no": 1, "readable": True, "blank": False}],
                    facts=[
                        {
                            "page_no": 2,
                            "kind": "validity",
                            "label": "Offer validity",
                            "excerpt": "Valid for 60 days",
                            "issued_on": "2606-26-26",
                        }
                    ],
                )
            )
        )
        with pytest.raises(ValueError, match="outside the document window"):
            await extract_review_window(
                [
                    SimpleNamespace(
                        page_no=1,
                        text_content="Proposal terms " * 8,
                        image_path="page-1",
                    )
                ],
                client=client,
                context={"opening_page_context": "26 June 2025"},
                image_loader=AsyncMock(return_value=b"image"),
            )

    run_async(exercise())


def test_retry_reads_only_the_unfinished_page_window():
    async def exercise():
        document = SimpleNamespace(
            id=uuid.uuid4(),
            page_count=4,
            original_filename="Quote.pdf",
            content_hash="hash",
            review_data={},
        )
        comparison = SimpleNamespace(
            project_id=uuid.uuid4(), context={"package_name": "Structural"}
        )
        job = SimpleNamespace(
            payload={"document_id": str(document.id)}, comparison_id=uuid.uuid4()
        )
        session = AsyncMock()
        session.get.side_effect = lambda cls, key: (
            document if cls is TenderDocument else comparison
        )
        result = MagicMock()
        result.scalars.return_value = [
            SimpleNamespace(
                page_no=i, text_content="Scope text", image_path=f"page-{i}"
            )
            for i in range(1, 5)
        ]
        session.execute.return_value = result

        def extracted(numbers):
            return ReviewExtraction(
                coverage=[
                    {"page_no": i, "readable": True, "blank": False} for i in numbers
                ],
                facts=[],
            ), []

        reader = AsyncMock(
            side_effect=[extracted([1, 2, 3]), RuntimeError("interrupted")]
        )
        with (
            patch.object(review_extraction, "extract_review_window", reader),
            patch.object(review_extraction.jobs, "assert_lease", AsyncMock()),
            patch.object(
                review_extraction.extract_cache,
                "get_cached_extract",
                AsyncMock(return_value=None),
            ),
            patch.object(
                review_extraction.extract_cache, "put_cached_extract", AsyncMock()
            ),
        ):
            with pytest.raises(RuntimeError, match="interrupted"):
                await review_extraction.read_review_document(
                    session, job, client=object()
                )
            assert list(document.review_data["windows"]) == ["0"]
            reader.side_effect = [extracted([4])]
            reader.reset_mock()
            await review_extraction.read_review_document(session, job, client=object())
            assert reader.await_count == 1
            assert reader.await_args.args[0][0].page_no == 4
            assert document.review_data["complete"] is True
            assert list(document.review_data["windows"]) == ["0", "3"]

    run_async(exercise())


def test_image_only_pages_are_read_and_money_census_requests_visual_recovery():
    async def exercise():
        client = SimpleNamespace(
            request=AsyncMock(
                side_effect=[
                    ReviewExtraction(
                        coverage=[{"page_no": 1, "readable": True, "blank": False}],
                        facts=[],
                    ),
                    ReviewExtraction(
                        coverage=[{"page_no": 1, "readable": True, "blank": False}],
                        facts=[
                            {
                                "page_no": 1,
                                "label": "Fee",
                                "excerpt": "Fee $1,200.00",
                                "kind": "component",
                                "amount_printed": "$1,200.00",
                            }
                        ],
                    ),
                ]
            )
        )
        image_loader = AsyncMock(return_value=b"image")
        source = "Fee $1,200.00 " + "Supporting text " * 6
        result, missing = await extract_review_window(
            [SimpleNamespace(page_no=1, text_content=source, image_path="page-1")],
            client=client,
            context={},
            image_loader=image_loader,
        )
        assert not missing
        assert result.facts[0].amount_printed == "$1,200.00"
        assert client.request.await_count == 2
        assert client.request.await_args.kwargs["images"] == {1: b"image"}
        image_loader.reset_mock()
        client.request = AsyncMock(
            return_value=ReviewExtraction(
                coverage=[{"page_no": 8, "readable": True, "blank": True}], facts=[]
            )
        )
        await extract_review_window(
            [SimpleNamespace(page_no=8, text_content="", image_path="scan")],
            client=client,
            context={},
            image_loader=image_loader,
        )
        image_loader.assert_awaited_once_with("scan")
        assert client.request.await_args.kwargs["images"] == {8: b"image"}

    run_async(exercise())
