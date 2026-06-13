from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_pmp_workspace_sync():
    with patch(
        "app.workflows.create_pmp.sync_pmp_draft_workspace",
        new=AsyncMock(return_value="04-projects/mock/00-brief-pmp/PMP.md"),
    ):
        yield
