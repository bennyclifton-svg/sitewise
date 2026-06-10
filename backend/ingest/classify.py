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


def _looks_like_drawing(filename: str) -> bool:
    lowered = filename.lower()
    if parse_drawing_filename(filename).drawing_number:
        return True
    if any(hint in lowered for hint in _DRAWING_NAME_HINTS):
        return True
    if re.search(r"\bplan\b", lowered) and not any(
        skip in lowered for skip in ("implementation plan", "management plan", "quality plan")
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


def classify_entry(entry: ManifestEntry) -> Classification:
    context = infer_project_context(entry.relative_path)
    extension = entry.extension.lower()
    filename = entry.filename
    metadata = parse_procurement_stage(entry.relative_path)

    document_class: DocumentClass = "unknown"

    if context.source_type == "doctrine":
        document_class = "doctrine"
    elif context.source_type == "reference":
        document_class = "reference_guide"
    elif metadata.get("procurement_stage") == "submission":
        document_class = "tender_submission"
    elif metadata.get("procurement_stage") == "trr":
        document_class = "trr"
    elif metadata.get("procurement_stage") == "evaluation":
        document_class = "evaluation"
    elif metadata.get("procurement_stage") == "rft":
        document_class = "rft"
    elif metadata.get("procurement_stage") == "addendum":
        document_class = "addendum"
    elif metadata.get("procurement_stage") == "eoi":
        document_class = "eoi"
    elif metadata.get("procurement_stage") == "tep":
        document_class = "tep"
    elif extension in _DRAWING_EXTENSIONS or (extension == ".pdf" and _looks_like_drawing(filename)):
        document_class = "drawing"
        metadata.setdefault("format", extension.lstrip(".") or "pdf")
        identity = parse_drawing_filename(filename)
        if identity.drawing_number:
            metadata.setdefault("drawing_number", identity.drawing_number)
        if identity.revision:
            metadata.setdefault("revision", identity.revision)
        if identity.title:
            metadata.setdefault("title", identity.title)
    elif extension in {".xlsx", ".xls", ".csv"}:
        document_class = "schedule"
    elif extension in {".msg", ".eml"}:
        document_class = "correspondence"
    else:
        hinted = _filename_hints(filename)
        if hinted:
            document_class = hinted

    ingest_mode = _ingest_mode_for_class(document_class)
    return Classification(
        document_class=document_class,
        ingest_mode=ingest_mode,
        document_metadata=metadata,
    )
