import argparse
import sys
from pathlib import Path

import structlog

from app.config import settings
from ingest.pipeline import ingest_file, ingest_folder

logger = structlog.get_logger(__name__)
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Clerk corpus ingestion CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Discover and ingest corpus files")
    target = run_parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--folder", help="Top-level data/ folder name")
    target.add_argument(
        "--file",
        type=Path,
        help="Single file path (under data/ or repo docs/)",
    )
    run_parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Override corpus root (default: settings.data_dir)",
    )
    run_parser.add_argument(
        "--execute",
        action="store_true",
        help="Extract, embed, and persist (default: plan-only dry run)",
    )
    run_parser.add_argument("--limit", type=int, default=None, help="Process at most N files")
    run_parser.add_argument(
        "--force",
        action="store_true",
        help="Re-ingest even when content hash is unchanged",
    )
    return parser


def _resolve_file_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    candidates = [
        Path.cwd() / path,
        settings.data_dir / path,
        _REPO_ROOT / path,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return Path.cwd() / path


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    data_dir = args.data_dir
    dry_run = not args.execute
    skip_if_unchanged = not args.force

    if args.command == "run":
        if args.folder:
            summary = ingest_folder(
                args.folder,
                dry_run=dry_run,
                data_dir=data_dir,
                limit=args.limit,
                skip_if_unchanged=skip_if_unchanged,
            )
            logger.info(
                "ingest_summary",
                folder=summary.folder,
                planned=summary.planned,
                skipped=summary.skipped,
                by_class=summary.by_class,
                dry_run=dry_run,
            )
            return 0

        file_path = _resolve_file_path(args.file)
        ok = ingest_file(
            file_path,
            data_dir=data_dir,
            dry_run=dry_run,
            skip_if_unchanged=skip_if_unchanged,
        )
        return 0 if ok else 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
