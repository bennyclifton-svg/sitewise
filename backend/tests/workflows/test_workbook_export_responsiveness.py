import asyncio
import threading
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.workflows.create_cost_plan import save_cost_plan_workbook_artifact
from tests.conftest import run_async
from tests.workflows.hybrid_cost_plan_fixtures import harrison_clarke_cost_project


def test_requests_can_progress_while_workbook_is_built():
    async def scenario():
        loop = asyncio.get_running_loop()
        started = asyncio.Event()
        release = threading.Event()
        other_request_progressed = []

        def build(**kwargs):
            loop.call_soon_threadsafe(started.set)
            other_request_progressed.append(release.wait(timeout=2))
            return SimpleNamespace(
                content=b"workbook",
                filename="Cost_Plan_v02.draft.xlsx",
                row_count=10,
                cost_item_lookup_count=10,
                warnings=[],
            )

        with (
            patch(
                "app.workflows.create_cost_plan.build_typed_cost_plan_workbook",
                side_effect=build,
            ),
            patch(
                "app.workflows.create_cost_plan.list_invoice_register_rows",
                new=AsyncMock(return_value=[]),
            ),
            patch("app.workflows.create_cost_plan.upload_project_file"),
            patch(
                "app.workflows.create_cost_plan.upsert_workspace_file", new=AsyncMock()
            ),
            patch(
                "app.projects.artefact_revisions.set_export_result_for_path",
                new=AsyncMock(),
            ),
        ):
            task = asyncio.create_task(
                save_cost_plan_workbook_artifact(
                    AsyncMock(),
                    project=harrison_clarke_cost_project(),
                    draft=SimpleNamespace(version=2),
                    markdown="",
                    typed_state=SimpleNamespace(items=[1]),
                )
            )
            await asyncio.wait_for(started.wait(), timeout=4)
            release.set()
            metadata = await task
        assert other_request_progressed == [True]
        assert metadata["row_count"] == 10
        assert metadata["size_bytes"] == len(b"workbook")

    run_async(scenario())
