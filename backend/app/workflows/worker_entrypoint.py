from __future__ import annotations

import asyncio
import sys
from collections.abc import Sequence

from app.workflows.runs import SUPPORTED_WORKFLOWS
from app.workflows.worker import _healthcheck, _main


def validate_required_workflows(required_workflows: Sequence[str]) -> None:
    missing = sorted(set(required_workflows) - SUPPORTED_WORKFLOWS)
    if missing:
        raise RuntimeError(
            "Worker image is missing required workflows: " + ", ".join(missing)
        )


async def run(
    *, required_workflows: Sequence[str], healthcheck: bool = False
) -> None:
    validate_required_workflows(required_workflows)
    if healthcheck:
        await _healthcheck()
        return
    await _main()


def main(argv: Sequence[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    healthcheck = "--healthcheck" in args
    required_workflows = [arg for arg in args if arg != "--healthcheck"]
    if not required_workflows:
        raise RuntimeError("Worker entrypoint requires at least one workflow capability")
    asyncio.run(
        run(
            required_workflows=required_workflows,
            healthcheck=healthcheck,
        )
    )


if __name__ == "__main__":
    main()
