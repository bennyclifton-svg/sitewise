"""Print project slugs for local inbound tests."""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import text

from app.database.session import get_engine


async def main() -> None:
    needle = sys.argv[1].strip().lower() if len(sys.argv) > 1 else ""
    engine = get_engine()
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "select slug, title, count(*) over (partition by lower(slug)) "
                    "as slug_count from projects order by slug"
                )
            )
        ).all()
    for slug, title, slug_count in rows:
        if needle and needle not in slug.lower() and needle not in title.lower():
            continue
        extra = f"\tDUPLICATE x{slug_count}" if slug_count > 1 else ""
        print(f"{slug}\t{title}{extra}")


if __name__ == "__main__":
    asyncio.run(main())
