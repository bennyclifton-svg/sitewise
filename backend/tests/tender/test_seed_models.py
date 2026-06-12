import tender.models  # noqa: F401
from app.database.base import Base


def test_seed_tables_are_registered() -> None:
    assert {
        "taxonomy_cells",
        "taxonomy_synonyms",
        "expectation_rules",
        "benchmarks",
        "report_language",
    }.issubset(Base.metadata.tables)


def test_benchmark_stable_key_is_unique() -> None:
    constraint_names = {
        constraint.name for constraint in Base.metadata.tables["benchmarks"].constraints
    }

    assert "uq_benchmarks_stable_key" in constraint_names
