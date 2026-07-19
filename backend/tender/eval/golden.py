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
SUPPORTED_STATES = {"NSW", "VIC", "QLD"}
SUPPORTED_BUILD_TYPES = {"new_build", "renovation", "addition"}
ADVERSARIAL_CASES = {
    "ocr_noise",
    "duplicate",
    "addendum",
    "missing_scope",
    "conflicting_totals",
    "allowances",
    "alternates",
    "gst",
    "exclusions",
}


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
    mappings: tuple[GoldenMapping, ...] = ()


@dataclass(frozen=True)
class GoldenCellStatus:
    cell: str
    status: str
    amount_cents: int | None = None


@dataclass(frozen=True)
class GoldenAnnotation:
    line_items: tuple[GoldenLineItem, ...] = ()
    cell_status: tuple[GoldenCellStatus, ...] = ()


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
    access_review: dict[str, Any] = field(default_factory=dict)
    redaction_review: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CorpusValidationReport:
    errors: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return not self.errors


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
        access_review=dict(
            _mapping(meta.get("access_review", {}), "meta.access_review")
        ),
        redaction_review=dict(
            _mapping(meta.get("redaction_review", {}), "meta.redaction_review")
        ),
    )


def validate_release_corpus(manifest: GoldenManifest) -> CorpusValidationReport:
    errors: list[str] = []
    real = [document for document in manifest.documents if document.source == "real"]
    synthetic = [
        document for document in manifest.documents if document.source == "synthetic"
    ]
    real_min = int(manifest.targets.get("real_documents_min", 30))
    synthetic_min = int(manifest.targets.get("synthetic_documents_min", 20))
    if len(real) < real_min:
        errors.append(f"requires at least {real_min} real documents; found {len(real)}")
    if len(synthetic) < synthetic_min:
        errors.append(
            f"requires at least {synthetic_min} synthetic adversarial documents; "
            f"found {len(synthetic)}"
        )
    if manifest.documents and len(synthetic) / len(manifest.documents) > 0.5:
        errors.append("synthetic documents exceed 50% of the release corpus")

    identifiers = [document.id for document in manifest.documents]
    if len(identifiers) != len(set(identifiers)):
        errors.append("golden document IDs must be unique")

    for document in manifest.documents:
        if document.source == "real":
            if document.doc_meta.get("anonymised") is not True:
                errors.append(f"real document {document.id} is not anonymised")
            if not _approved(document.doc_meta.get("consent")):
                errors.append(
                    f"real document {document.id} has no approved consent record"
                )
            if not document.storage_path or not document.storage_path.startswith(
                "protected://"
            ):
                errors.append(
                    f"real document {document.id} has no protected storage_path"
                )
        if not document.doc_meta.get("provenance"):
            errors.append(f"document {document.id} has no provenance record")
        if not document.doc_meta.get("retention"):
            errors.append(f"document {document.id} has no retention record")

    states = {str(document.doc_meta.get("state")) for document in real}
    missing_states = SUPPORTED_STATES - states
    if missing_states:
        errors.append(
            f"real corpus is missing states: {', '.join(sorted(missing_states))}"
        )
    build_types = {str(document.doc_meta.get("build_type")) for document in real}
    missing_build_types = SUPPORTED_BUILD_TYPES - build_types
    if missing_build_types:
        errors.append(
            "real corpus is missing build types: "
            + ", ".join(sorted(missing_build_types))
        )
    difficulties = {document.difficulty for document in manifest.documents}
    if difficulties != DIFFICULTY_VALUES:
        errors.append("corpus must cover easy, medium, and hard difficulty levels")
    formats = {
        str(document.doc_meta.get("format"))
        for document in manifest.documents
        if document.doc_meta.get("format")
    }
    if len(formats) < 2:
        errors.append("corpus must cover at least two document formats")

    adversarial = {
        str(tag)
        for document in synthetic
        for tag in document.doc_meta.get("adversarial_tags", [])
    }
    missing_adversarial = ADVERSARIAL_CASES - adversarial
    if missing_adversarial:
        errors.append(
            "synthetic corpus is missing adversarial cases: "
            + ", ".join(sorted(missing_adversarial))
        )

    line_items = [
        item
        for document in manifest.documents
        for item in document.annotation.line_items
    ]
    statuses = {
        _release_silence_status(status.status)
        for document in manifest.documents
        for status in document.annotation.cell_status
    }
    if not any(item.amount_cents is not None for item in line_items):
        errors.append("corpus has no amount exact-match ground truth")
    if not any(item.item_status for item in line_items):
        errors.append("corpus has no line-item status ground truth")
    if not any(item.mappings for item in line_items):
        errors.append("corpus has no mapping ground truth")
    silence_classes = {"excluded", "bundled", "ps_covered", "not_required", "ambiguous"}
    missing_silence = silence_classes - statuses
    if missing_silence:
        errors.append(
            "corpus is missing silence classes: " + ", ".join(sorted(missing_silence))
        )
    if not _approved(manifest.access_review):
        errors.append("corpus access review is not approved")
    if not _approved(manifest.redaction_review):
        errors.append("corpus redaction review is not approved")
    return CorpusValidationReport(errors=tuple(errors))


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
    return GoldenAnnotation(
        line_items=tuple(_parse_line_item(item, document_id) for item in line_items),
        cell_status=tuple(_parse_cell_status(item, document_id) for item in cell_status),
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


def _read_yaml(path: Path) -> Mapping[str, Any]:
    with path.open(encoding="utf-8") as file:
        data = yaml.safe_load(file)
    if data is None:
        return {}
    if not isinstance(data, Mapping):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def _approved(value: Any) -> bool:
    if value is True or value == "approved":
        return True
    return isinstance(value, Mapping) and value.get("status") == "approved"


def _release_silence_status(value: str) -> str:
    return {
        "excluded_explicit": "excluded",
        "silent_ambiguous": "ambiguous",
        "ps": "ps_covered",
    }.get(value, value)
