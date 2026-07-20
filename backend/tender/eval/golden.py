from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MANIFEST_PATH = REPO_ROOT / "data" / "tender" / "golden" / "manifest.yaml"

GoldenSource = Literal["real", "synthetic"]
GoldenDifficulty = Literal["easy", "medium", "hard"]

SOURCE_VALUES = {"real", "synthetic"}
DIFFICULTY_VALUES = {"easy", "medium", "hard"}


@dataclass(frozen=True)
class GoldenMapping:
    cell: str
    fraction: float = 1.0


@dataclass(frozen=True)
class GoldenLineItem:
    description_raw: str
    page: int
    qty: float | None = None
    unit: str | None = None
    amount_cents: int | None = None
    item_status: str | None = None
    allowance_cents: int | None = None
    role: str | None = None
    parent: str | None = None
    gst_basis: str | None = None
    counted: bool | None = None
    duplicate_of: str | None = None
    is_rollup: bool | None = None
    suspect_format: bool | None = None
    mappings: tuple[GoldenMapping, ...] = ()


@dataclass(frozen=True)
class GoldenCellStatus:
    cell: str
    status: str
    amount_cents: int | None = None


@dataclass(frozen=True)
class GoldenQuote:
    stated_total_cents: int | None = None
    stated_basis: str | None = None
    expected_residual_cents: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GoldenAnnotation:
    line_items: tuple[GoldenLineItem, ...] = ()
    cell_status: tuple[GoldenCellStatus, ...] = ()
    quote: GoldenQuote | None = None


@dataclass(frozen=True)
class GoldenDocument:
    id: str
    source: GoldenSource
    difficulty: GoldenDifficulty
    storage_path: str | None
    doc_meta: dict[str, Any]
    annotation: GoldenAnnotation = field(default_factory=GoldenAnnotation)


@dataclass(frozen=True)
class GoldenManifest:
    version: int
    targets: dict[str, Any]
    documents: tuple[GoldenDocument, ...]


def load_manifest(path: Path = DEFAULT_MANIFEST_PATH) -> GoldenManifest:
    data = _read_yaml(path)
    meta = _mapping(data.get("meta", {}), "meta")
    documents = data.get("documents", [])
    if documents is None:
        documents = []
    if not isinstance(documents, list):
        raise ValueError("golden manifest documents must be a list")

    base_dir = path.parent
    return GoldenManifest(
        version=int(meta.get("version", 1)),
        targets=dict(_mapping(meta.get("targets", {}), "meta.targets")),
        documents=tuple(_parse_document(raw, base_dir) for raw in documents),
    )


def _parse_document(raw: Any, base_dir: Path) -> GoldenDocument:
    document = _mapping(raw, "document entry")
    document_id = str(document["id"])
    source = _enum_value(document.get("source"), SOURCE_VALUES, "source")
    difficulty = _enum_value(document.get("difficulty"), DIFFICULTY_VALUES, "difficulty")
    doc_meta = dict(_mapping(document.get("doc_meta", {}), f"{document_id}.doc_meta"))
    for key in ("doc_type", "state", "build_type", "anonymised"):
        if key in document:
            doc_meta[key] = document[key]

    return GoldenDocument(
        id=document_id,
        source=source,  # type: ignore[arg-type]
        difficulty=difficulty,  # type: ignore[arg-type]
        storage_path=_optional_str(document.get("storage_path", document.get("path"))),
        doc_meta=doc_meta,
        annotation=_load_annotation(document, base_dir, document_id),
    )


def _load_annotation(
    document: Mapping[str, Any], base_dir: Path, document_id: str
) -> GoldenAnnotation:
    if "ground_truth" in document:
        return _parse_annotation({"ground_truth": document["ground_truth"]}, document_id)

    annotation_path = document.get("annotation_path", document.get("annotation"))
    if annotation_path is None:
        default_path = base_dir / "annotations" / f"{document_id}.yaml"
        if default_path.exists():
            annotation_path = default_path.relative_to(base_dir).as_posix()

    if annotation_path is None:
        raise ValueError(f"golden document {document_id} is missing an annotation path")

    path = base_dir / str(annotation_path)
    return _parse_annotation(_read_yaml(path), document_id)


def _parse_annotation(data: Mapping[str, Any], document_id: str) -> GoldenAnnotation:
    truth = _mapping(data.get("ground_truth", {}), f"{document_id}.ground_truth")
    line_items = truth.get("line_items", [])
    cell_status = truth.get("cell_status", [])
    if not isinstance(line_items, list):
        raise ValueError(f"{document_id}.ground_truth.line_items must be a list")
    if not isinstance(cell_status, list):
        raise ValueError(f"{document_id}.ground_truth.cell_status must be a list")
    quote_raw = truth.get("quote")
    quote = _parse_quote(quote_raw, document_id) if quote_raw is not None else None
    return GoldenAnnotation(
        line_items=tuple(_parse_line_item(item, document_id) for item in line_items),
        cell_status=tuple(_parse_cell_status(item, document_id) for item in cell_status),
        quote=quote,
    )


def _parse_quote(raw: Any, document_id: str) -> GoldenQuote:
    item = _mapping(raw, f"{document_id}.quote")
    known = {"stated_total_cents", "stated_basis", "expected_residual_cents"}
    extra = {key: value for key, value in item.items() if key not in known}
    return GoldenQuote(
        stated_total_cents=_optional_int(item.get("stated_total_cents")),
        stated_basis=_optional_str(item.get("stated_basis")),
        expected_residual_cents=_optional_int(item.get("expected_residual_cents")),
        extra=extra,
    )


def _parse_line_item(raw: Any, document_id: str) -> GoldenLineItem:
    item = _mapping(raw, f"{document_id}.line_item")
    mappings = item.get("mappings", [])
    if not isinstance(mappings, list):
        raise ValueError(f"{document_id}.line_item.mappings must be a list")
    return GoldenLineItem(
        description_raw=str(item["description_raw"]),
        page=int(item.get("page", item.get("page_no"))),
        qty=_optional_float(item.get("qty")),
        unit=_optional_str(item.get("unit")),
        amount_cents=_optional_int(item.get("amount_cents")),
        item_status=_optional_str(item.get("item_status")),
        allowance_cents=_optional_int(item.get("allowance_cents")),
        role=_optional_str(item.get("role")),
        parent=_optional_str(item.get("parent")),
        gst_basis=_optional_str(item.get("gst_basis")),
        counted=_optional_bool(item.get("counted")),
        duplicate_of=_optional_str(item.get("duplicate_of")),
        is_rollup=_optional_bool(item.get("is_rollup")),
        suspect_format=_optional_bool(item.get("suspect_format")),
        mappings=tuple(_parse_mapping(mapping, document_id) for mapping in mappings),
    )


def _parse_mapping(raw: Any, document_id: str) -> GoldenMapping:
    mapping = _mapping(raw, f"{document_id}.mapping")
    return GoldenMapping(
        cell=str(mapping.get("cell", mapping.get("cell_code"))),
        fraction=float(mapping.get("fraction", mapping.get("allocation_fraction", 1.0))),
    )


def _parse_cell_status(raw: Any, document_id: str) -> GoldenCellStatus:
    item = _mapping(raw, f"{document_id}.cell_status")
    return GoldenCellStatus(
        cell=str(item.get("cell", item.get("cell_code"))),
        status=str(item["status"]),
        amount_cents=_optional_int(item.get("amount_cents")),
    )


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return value


def _enum_value(value: Any, allowed: set[str], label: str) -> str:
    candidate = str(value)
    if candidate not in allowed:
        allowed_values = ", ".join(sorted(allowed))
        raise ValueError(f"{label} must be one of: {allowed_values}")
    return candidate


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


def _optional_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
    return bool(value)


def _read_yaml(path: Path) -> Mapping[str, Any]:
    with path.open(encoding="utf-8") as file:
        data = yaml.safe_load(file)
    if data is None:
        return {}
    if not isinstance(data, Mapping):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data

