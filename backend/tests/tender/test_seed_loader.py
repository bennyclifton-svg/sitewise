import asyncio
import selectors
import sys
from collections.abc import Coroutine
from typing import Any

from tender.seeds.load import (
    DEFAULT_DATA_DIR,
    MemorySeedStore,
    load_tender_seeds,
    read_seed_tables,
    read_synonyms,
    read_taxonomy,
)


def test_seed_tables_are_read_in_contract_order() -> None:
    names = [spec.name for spec, _rows in read_seed_tables(DEFAULT_DATA_DIR)]

    assert names == [
        "taxonomy_cells",
        "taxonomy_synonyms",
        "expectation_rules",
        "benchmarks",
        "report_language",
    ]


def test_taxonomy_defaults_aliases_and_group_derivation() -> None:
    cells = {row["code"]: row for row in read_taxonomy(DEFAULT_DATA_DIR / "taxonomy.yaml")}

    retaining = cells["03.05"]
    assert retaining["grp"] == "Site costs & groundworks"
    assert retaining["build_type_tags"] == ["new_build", "renovation", "addition"]
    assert retaining["region_tags"] == ["NSW", "VIC", "QLD"]
    assert retaining["active"] is True
    assert retaining["bundling_parents"] == ["03.01"]
    assert retaining["benchmark_key"] == "site.retaining"

    nsw_home_warranty = cells["21.01"]
    assert nsw_home_warranty["region_tags"] == ["NSW"]


def test_synonym_sources_are_normalized_to_prd_values() -> None:
    rows = read_synonyms(DEFAULT_DATA_DIR / "synonyms.seed.csv")
    expanded = next(row for row in rows if row["phrase"] == "building approvals")

    assert expanded["source"] == "seed"
    assert expanded["phrase_norm"] == "building approvals"


def test_loading_twice_produces_zero_changes() -> None:
    store = MemorySeedStore()

    first = run(load_tender_seeds(store, DEFAULT_DATA_DIR))
    second = run(load_tender_seeds(store, DEFAULT_DATA_DIR))

    assert first.changed == first.total
    assert second.changed == 0
    assert second.total == first.total
    assert all(counts.unchanged > 0 for counts in second.tables.values())


def run(coro: Coroutine[Any, Any, Any]) -> Any:
    if sys.platform == "win32":
        loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    return asyncio.run(coro)
