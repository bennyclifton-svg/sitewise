import re
from pathlib import PurePosixPath

from ingest.drawing_parse import parse_drawing_filename
from ingest.metadata import infer_project_context
from ingest.types import Classification, DocumentClass, IngestMode, ManifestEntry

_PROCUREMENT_STAGE_RE = re.compile(
    r"^(\d{2})\s+"
    r"(TEP|EOI|RFT|ADDENDUM|SUBMISSION\s+(\d{2})|EVALUATION|TRR)\b",
    re.IGNORECASE,
)

_PROCUREMENT_STAGE_VARIANT_RE = re.compile(
    r"^(\d{2})\s+TENDER\s+(SUBMISSIONS?|EVALUATION|RECOMMENDATION)\b",
    re.IGNORECASE,
)

_SUBMIT_FILENAME_RE = re.compile(r"SUBMIT\s+(\d{2})\b", re.IGNORECASE)

_DRAWING_EXTENSIONS = {".dwg", ".dxf"}

_DRAWING_NAME_HINTS = (
    "site plan",
    "cc plan",
    "floor plan",
    "roof plan",
    "landscape",
    "elevation",
    "diagram",
    "drawing schedule",
    "overall plan",
    "cover sheet",
)

# Superseded by scored filename rules in Stage 4. Tactical fix only.
_NOT_A_DRAWING_PLAN = (
    "implementation plan", "management plan", "quality plan",
    "cost plan", "business plan", "payment plan", "staging plan",
    "specification plan", "traffic plan", "waste plan", "project plan",
    "safety plan", "test plan", "communication plan", "procurement plan",
)


def _looks_like_drawing(filename: str) -> bool:
    lowered = filename.lower()
    if re.search(r"^M\d{2,3}\b", filename, re.I):
        return True
    if parse_drawing_filename(filename).drawing_number:
        return True
    if any(hint in lowered for hint in _DRAWING_NAME_HINTS):
        return True
    if re.search(r"\bplan\b", lowered) and not any(
        skip in lowered for skip in _NOT_A_DRAWING_PLAN
    ):
        return True
    return False


def _path_parts(relative_path: str) -> list[str]:
    return [part for part in PurePosixPath(relative_path.replace("\\", "/")).parts if part]


def _metadata_from_stage_token(stage_token: str, tenderer_id: str | None = None) -> dict[str, str]:
    token = stage_token.upper()
    metadata: dict[str, str] = {}
    if token == "TEP":
        metadata["procurement_stage"] = "tep"
    elif token == "EOI":
        metadata["procurement_stage"] = "eoi"
    elif token == "RFT":
        metadata["procurement_stage"] = "rft"
    elif token == "ADDENDUM":
        metadata["procurement_stage"] = "addendum"
    elif token.startswith("SUBMISSION"):
        metadata["procurement_stage"] = "submission"
        if tenderer_id:
            metadata["tenderer_id"] = tenderer_id
    elif token == "EVALUATION":
        metadata["procurement_stage"] = "evaluation"
    elif token in {"TRR", "RECOMMENDATION"}:
        metadata["procurement_stage"] = "trr"
    return metadata


def parse_procurement_stage(relative_path: str) -> dict[str, str]:
    parts = _path_parts(relative_path)
    filename = parts[-1] if parts else ""

    for part in parts:
        match = _PROCUREMENT_STAGE_RE.match(part)
        if match:
            return _metadata_from_stage_token(match.group(2), match.group(3))

        variant = _PROCUREMENT_STAGE_VARIANT_RE.match(part)
        if not variant:
            continue
        stage_token = variant.group(2).upper()
        tenderer_id: str | None = None
        if stage_token.startswith("SUBMISSION"):
            submit_match = _SUBMIT_FILENAME_RE.search(filename)
            if submit_match:
                tenderer_id = submit_match.group(1)
        if stage_token == "RECOMMENDATION":
            stage_token = "TRR"
        return _metadata_from_stage_token(stage_token, tenderer_id)

    return {}


_PLANNING_INSTRUMENT_RE = re.compile(
    r"local environmental plan|\bdevelopment control plan\b|\blep\b|\bdcp\b",
    re.IGNORECASE,
)
_PLANNING_INSTRUMENT_EXCLUDE_RE = re.compile(
    r"\b(assessment|report|statement|review)\b",
    re.IGNORECASE,
)


def _looks_like_planning_instrument(filename: str) -> bool:
    if not _PLANNING_INSTRUMENT_RE.search(filename):
        return False
    return _PLANNING_INSTRUMENT_EXCLUDE_RE.search(filename) is None


def _filename_hints(filename: str) -> DocumentClass | None:
    lowered = filename.lower()
    if any(token in lowered for token in ("contract", "agreement", "deed", "fioa")):
        return "contract"
    if "spec" in lowered:
        return "specification"
    if any(token in lowered for token in ("claim", "variation", "eot", "notice", "letter")):
        return "correspondence"
    if any(token in lowered for token in ("report", "assessment", "review")):
        return "report"
    if any(token in lowered for token in ("certificate", "basix", "consent", "approval")):
        return "certificate"
    return None


def _ingest_mode_for_class(document_class: DocumentClass) -> IngestMode:
    if document_class == "drawing":
        return "register_only"
    return "full_text"


# Stage 8 migrates stored document_class values. Keep identical to TRACKER.md.
_LEGACY_TO_CANONICAL: dict[str, tuple[DocumentClass, dict[str, str]]] = {
    "tep":              ("commercial", {"procurement_stage": "tep"}),
    "eoi":              ("commercial", {"procurement_stage": "eoi"}),
    "rft":              ("commercial", {"procurement_stage": "rft"}),
    "addendum":         ("commercial", {"procurement_stage": "addendum"}),
    "tender_submission":("commercial", {"procurement_stage": "submission"}),
    "evaluation":       ("commercial", {"procurement_stage": "evaluation"}),
    "trr":              ("commercial", {"procurement_stage": "trr"}),
    "planning_instrument": ("statutory_instrument", {}),
    "doctrine":         ("report", {"reference_kind": "doctrine"}),        # OD-1
    "reference_guide":  ("report", {"reference_kind": "reference_guide"}), # OD-1
}


def canonicalize_document_class(
    raw_class: str, metadata: dict[str, str]
) -> tuple[DocumentClass, dict[str, str]]:
    mapped = _LEGACY_TO_CANONICAL.get(raw_class)
    if mapped is None:
        return raw_class, metadata  # type: ignore[return-value]
    canonical, extra = mapped
    if not extra:
        return canonical, metadata
    return canonical, {**metadata, **extra}


def classify_entry(entry: ManifestEntry) -> Classification:
    context = infer_project_context(entry.relative_path)
    extension = entry.extension.lower()
    filename = entry.filename
    metadata = parse_procurement_stage(entry.relative_path)

    raw_class: str = "unknown"

    if context.source_type == "doctrine":
        raw_class = "doctrine"
    elif context.source_type == "reference":
        raw_class = "reference_guide"
    elif metadata.get("procurement_stage") == "submission":
        raw_class = "tender_submission"
    elif metadata.get("procurement_stage") == "trr":
        raw_class = "trr"
    elif metadata.get("procurement_stage") == "evaluation":
        raw_class = "evaluation"
    elif metadata.get("procurement_stage") == "rft":
        raw_class = "rft"
    elif metadata.get("procurement_stage") == "addendum":
        raw_class = "addendum"
    elif metadata.get("procurement_stage") == "eoi":
        raw_class = "eoi"
    elif metadata.get("procurement_stage") == "tep":
        raw_class = "tep"
    elif extension in _DRAWING_EXTENSIONS or (
        extension in {".pdf", ".md"} and _looks_like_drawing(filename)
    ):
        raw_class = "drawing"
        metadata.setdefault("format", extension.lstrip(".") or "pdf")
        identity = parse_drawing_filename(filename)
        if identity.drawing_number:
            metadata.setdefault("drawing_number", identity.drawing_number)
        if identity.revision:
            metadata.setdefault("revision", identity.revision)
        if identity.title:
            metadata.setdefault("title", identity.title)
    elif _looks_like_planning_instrument(filename):
        raw_class = "planning_instrument"
    elif extension in {".xlsx", ".xls", ".csv"}:
        raw_class = "schedule"
    elif extension in {".msg", ".eml"}:
        raw_class = "correspondence"
    else:
        hinted = _filename_hints(filename)
        if hinted:
            raw_class = hinted

    document_class, metadata = canonicalize_document_class(raw_class, metadata)
    ingest_mode = _ingest_mode_for_class(document_class)
    return Classification(
        document_class=document_class,
        ingest_mode=ingest_mode,
        document_metadata=metadata,
        document_subject="none",           # Stage 4 fills this
        confidence=0.5 if document_class != "unknown" else 0.0,
        basis="filename" if document_class != "unknown" else "default",
    )
