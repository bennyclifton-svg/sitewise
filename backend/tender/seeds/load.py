from __future__ import annotations

import argparse
import asyncio
import csv
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol

import yaml
from sqlalchemy import Select, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from tender.models import (  # noqa: E402
    Benchmark,
    ExpectationRule,
    ReportLanguageEntry,
    TaxonomyCell,
    TaxonomySynonym,
)
from tender.services.expectations import (  # noqa: E402
    PredicateValidationError,
    validate_predicate,
)


DEFAULT_DATA_DIR = REPO_ROOT / "data" / "tender"
SOURCE_ALIASES = {"seed_expanded": "seed"}


@dataclass(frozen=True)
class TableSpec:
    name: str
    table: Any
    key_fields: tuple[str, ...]
    write_fields: tuple[str, ...]

    @property
    def compare_fields(self) -> tuple[str, ...]:
        return self.key_fields + tuple(
            field for field in self.write_fields if field not in self.key_fields
        )


@dataclass
class UpsertCounts:
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0

    @property
    def changed(self) -> int:
        return self.inserted + self.updated


@dataclass
class SeedLoadResult:
    tables: dict[str, UpsertCounts] = field(default_factory=dict)

    @property
    def changed(self) -> int:
        return sum(counts.changed for counts in self.tables.values())

    @property
    def total(self) -> int:
        return sum(
            counts.inserted + counts.updated + counts.unchanged
            for counts in self.tables.values()
        )


class SeedStore(Protocol):
    async def upsert(self, spec: TableSpec, rows: Sequence[dict[str, Any]]) -> UpsertCounts:
        ...


class DatabaseSeedStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(self, spec: TableSpec, rows: Sequence[dict[str, Any]]) -> UpsertCounts:
        _assert_unique_keys(spec, rows)
        existing = await self._existing_rows(spec)
        changed_rows: list[dict[str, Any]] = []
        counts = UpsertCounts()

        for row in rows:
            key = _row_key(row, spec.key_fields)
            existing_row = existing.get(key)
            incoming = _comparable(row, spec.compare_fields)
            if existing_row is None:
                counts.inserted += 1
                changed_rows.append(row)
            elif incoming == existing_row:
                counts.unchanged += 1
            else:
                counts.updated += 1
                changed_rows.append(row)

        if changed_rows:
            statement = insert(spec.table).values(changed_rows)
            update_values = {
                field: getattr(statement.excluded, field)
                for field in spec.write_fields
                if field not in spec.key_fields
            }
            if spec.name == "report_language":
                update_values["updated_at"] = func.now()
            statement = statement.on_conflict_do_update(
                index_elements=list(spec.key_fields),
                set_=update_values,
            )
            await self.session.execute(statement)

        return counts

    async def _existing_rows(
        self, spec: TableSpec
    ) -> dict[tuple[Any, ...], dict[str, Any]]:
        columns = [spec.table.c[field] for field in spec.compare_fields]
        statement: Select[tuple[Any, ...]] = select(*columns)
        result = await self.session.execute(statement)
        existing: dict[tuple[Any, ...], dict[str, Any]] = {}
        for row in result.mappings():
            row_dict = dict(row)
            existing[_row_key(row_dict, spec.key_fields)] = _comparable(
                row_dict, spec.compare_fields
            )
        return existing


class MemorySeedStore:
    """Small test store that exercises the same stable-key comparison rules."""

    def __init__(self) -> None:
        self.rows: dict[str, dict[tuple[Any, ...], dict[str, Any]]] = {}

    async def upsert(self, spec: TableSpec, rows: Sequence[dict[str, Any]]) -> UpsertCounts:
        _assert_unique_keys(spec, rows)
        table = self.rows.setdefault(spec.name, {})
        counts = UpsertCounts()
        for row in rows:
            key = _row_key(row, spec.key_fields)
            incoming = _comparable(row, spec.compare_fields)
            if key not in table:
                counts.inserted += 1
                table[key] = incoming
            elif table[key] == incoming:
                counts.unchanged += 1
            else:
                counts.updated += 1
                table[key] = incoming
        return counts


TAXONOMY_SPEC = TableSpec(
    name="taxonomy_cells",
    table=TaxonomyCell.__table__,
    key_fields=("code",),
    write_fields=(
        "code",
        "parent_code",
        "name",
        "grp",
        "stage",
        "description",
        "applicability",
        "bundling_parents",
        "region_tags",
        "build_type_tags",
        "benchmark_key",
        "sort_order",
        "active",
        "version",
    ),
)
SYNONYM_SPEC = TableSpec(
    name="taxonomy_synonyms",
    table=TaxonomySynonym.__table__,
    key_fields=("cell_code", "phrase_norm"),
    write_fields=("cell_code", "phrase", "phrase_norm", "source", "confidence"),
)
EXPECTATION_SPEC = TableSpec(
    name="expectation_rules",
    table=ExpectationRule.__table__,
    key_fields=("rule_code",),
    write_fields=(
        "rule_code",
        "cell_code",
        "predicate",
        "severity",
        "rationale",
        "region_tags",
        "build_type_tags",
        "version",
    ),
)
BENCHMARK_SPEC = TableSpec(
    name="benchmarks",
    table=Benchmark.__table__,
    key_fields=(
        "benchmark_key",
        "state",
        "region",
        "build_type",
        "spec_level",
        "metric",
    ),
    write_fields=(
        "benchmark_key",
        "state",
        "region",
        "build_type",
        "spec_level",
        "metric",
        "p25",
        "p50",
        "p75",
        "unit",
        "source",
        "provenance",
        "confidence",
        "effective_date",
    ),
)
REPORT_LANGUAGE_SPEC = TableSpec(
    name="report_language",
    table=ReportLanguageEntry.__table__,
    key_fields=("key_path",),
    write_fields=("key_path", "value", "version"),
)


def read_seed_tables(data_dir: Path = DEFAULT_DATA_DIR) -> list[tuple[TableSpec, list[dict[str, Any]]]]:
    return [
        (TAXONOMY_SPEC, read_taxonomy(data_dir / "taxonomy.yaml")),
        (SYNONYM_SPEC, read_synonyms(data_dir / "synonyms.seed.csv")),
        (EXPECTATION_SPEC, read_expectations(data_dir / "expectations.yaml")),
        (BENCHMARK_SPEC, read_benchmarks(data_dir / "benchmarks.seed.csv")),
        (REPORT_LANGUAGE_SPEC, read_report_language(data_dir / "report_language.yaml")),
    ]


async def load_tender_seeds(
    store: SeedStore, data_dir: Path = DEFAULT_DATA_DIR
) -> SeedLoadResult:
    result = SeedLoadResult()
    for spec, rows in read_seed_tables(data_dir):
        result.tables[spec.name] = await store.upsert(spec, rows)
    return result


def read_taxonomy(path: Path) -> list[dict[str, Any]]:
    data = _read_yaml(path)
    defaults = data.get("meta", {}).get("defaults", {})
    version = int(data.get("meta", {}).get("version", 1))
    groups = data["groups"]
    concepts_path = path.with_name("concepts.yaml")
    concepts = read_concepts(concepts_path) if concepts_path.exists() else {}
    rows: list[dict[str, Any]] = []
    for sort_order, cell in enumerate(data["cells"], start=1):
        code = str(cell["code"])
        prefix = code[:2]
        if prefix not in groups:
            raise ValueError(f"taxonomy cell {code} has no group for prefix {prefix}")
        applicability = cell.get("applicability")
        if applicability is not None:
            try:
                validate_predicate(applicability, concepts=concepts)
            except PredicateValidationError as exc:
                raise ValueError(f"taxonomy cell {code} applicability is invalid: {exc}") from exc
        rows.append(
            {
                "code": code,
                "parent_code": cell.get("parent_code") or cell.get("parent"),
                "name": cell["name"],
                "grp": groups[prefix]["name"],
                "stage": cell["stage"],
                "description": cell.get("description"),
                "applicability": applicability,
                "bundling_parents": list(cell.get("bp", cell.get("bundling_parents", []))),
                "region_tags": list(
                    cell.get("rt", cell.get("region_tags", defaults.get("region_tags", [])))
                ),
                "build_type_tags": list(
                    cell.get(
                        "bt",
                        cell.get("build_type_tags", defaults.get("build_type_tags", [])),
                    )
                ),
                "benchmark_key": cell.get("bk", cell.get("benchmark_key")),
                "sort_order": sort_order,
                "active": bool(cell.get("active", defaults.get("active", True))),
                "version": version,
            }
        )
    return rows


def read_synonyms(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            phrase = row["phrase"].strip()
            source = row.get("source", "seed").strip() or "seed"
            rows.append(
                {
                    "cell_code": row["cell_code"].strip(),
                    "phrase": phrase,
                    "phrase_norm": normalize_phrase(phrase),
                    "source": SOURCE_ALIASES.get(source, source),
                    "confidence": None,
                }
            )
    return rows


def read_expectations(path: Path) -> list[dict[str, Any]]:
    data = _read_yaml(path)
    version = int(data.get("meta", {}).get("version", 1))
    concepts_path = path.with_name("concepts.yaml")
    concepts = read_concepts(concepts_path) if concepts_path.exists() else {}
    rows: list[dict[str, Any]] = []
    for rule in data["rules"]:
        try:
            validate_predicate(rule["predicate"], concepts=concepts)
        except PredicateValidationError as exc:
            raise ValueError(f"expectation rule {rule['rule']} predicate is invalid: {exc}") from exc
        rows.append(
            {
                "rule_code": rule["rule"],
                "cell_code": rule["cell"],
                "predicate": rule["predicate"],
                "severity": rule["severity"],
                "rationale": rule.get("rationale"),
                "region_tags": list(rule.get("region_tags", [])),
                "build_type_tags": list(rule.get("build_type_tags", [])),
                "version": version,
            }
        )
    return rows


def read_concepts(path: Path) -> dict[str, tuple[str, ...]]:
    data = _read_yaml(path)
    raw = data.get("concepts", {})
    if not isinstance(raw, Mapping):
        raise ValueError(f"{path} concepts must be a mapping")
    concepts: dict[str, tuple[str, ...]] = {}
    for key, phrases in raw.items():
        if not isinstance(phrases, list) or not phrases:
            raise ValueError(f"concept {key} must contain at least one phrase")
        concepts[str(key)] = tuple(str(phrase) for phrase in phrases)
    return concepts


def read_benchmarks(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            rows.append(
                {
                    "benchmark_key": row["benchmark_key"],
                    "state": row["state"],
                    "region": row["region"],
                    "build_type": row["build_type"],
                    "spec_level": row["spec_level"],
                    "metric": row["metric"],
                    "p25": _decimal_or_none(row["p25"]),
                    "p50": _decimal_or_none(row["p50"]),
                    "p75": _decimal_or_none(row["p75"]),
                    "unit": row["unit"] or None,
                    "source": row["source"],
                    "provenance": row["provenance"] or None,
                    "confidence": row["confidence"],
                    "effective_date": _date_or_none(row["effective_date"]),
                }
            )
    return rows


def read_report_language(path: Path) -> list[dict[str, Any]]:
    data = _read_yaml(path)
    version = int(data.get("meta", {}).get("version", 1))
    return [
        {"key_path": key_path, "value": value, "version": version}
        for key_path, value in _flatten("", data)
    ]


def normalize_phrase(phrase: str) -> str:
    return re.sub(r"\s+", " ", phrase.strip().casefold())


def _flatten(prefix: str, value: Any) -> Iterable[tuple[str, Any]]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            yield from _flatten(next_prefix, child)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _flatten(f"{prefix}.{index:04d}", child)
    else:
        yield prefix, value


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        data = yaml.safe_load(file)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def _decimal_or_none(value: str) -> Decimal | None:
    return Decimal(value) if value else None


def _date_or_none(value: str) -> date | None:
    return date.fromisoformat(value) if value else None


def _assert_unique_keys(spec: TableSpec, rows: Sequence[dict[str, Any]]) -> None:
    seen: set[tuple[Any, ...]] = set()
    for row in rows:
        key = _row_key(row, spec.key_fields)
        if key in seen:
            joined = ", ".join(str(part) for part in key)
            raise ValueError(f"duplicate {spec.name} seed key: {joined}")
        seen.add(key)


def _row_key(row: Mapping[str, Any], fields: Sequence[str]) -> tuple[Any, ...]:
    return tuple(row[field] for field in fields)


def _comparable(row: Mapping[str, Any], fields: Sequence[str]) -> dict[str, Any]:
    return {field: row[field] for field in fields}


def _format_result(result: SeedLoadResult) -> str:
    lines = ["Tender seed load complete:"]
    for table, counts in result.tables.items():
        lines.append(
            f"- {table}: {counts.inserted} inserted, {counts.updated} updated, "
            f"{counts.unchanged} unchanged"
        )
    lines.append(f"Total: {result.changed} changed / {result.total} rows")
    return "\n".join(lines)


async def _run(data_dir: Path) -> SeedLoadResult:
    from app.database.session import get_session_factory

    factory = get_session_factory()
    async with factory() as session:
        result = await load_tender_seeds(DatabaseSeedStore(session), data_dir)
        await session.commit()
        return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Load TCM seed knowledge into Postgres.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory containing data/tender seed files.",
    )
    args = parser.parse_args(argv)
    result = asyncio.run(_run(args.data_dir))
    print(_format_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
