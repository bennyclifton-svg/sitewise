import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from ingest.drawing_parse import parse_drawing_filename
from ingest.metadata import infer_project_context
from ingest.title_block import TitleBlockFields
from ingest.types import (
    Classification,
    ClassificationBasis,
    DocumentClass,
    DocumentSubject,
    IngestMode,
    ManifestEntry,
)

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

_CONTENT_SAMPLE_CHARS = 4000
_FILENAME_MARGIN = 2

_STRUCTURAL_EXTENSIONS: dict[str, DocumentClass] = {
    ".dwg": "drawing",
    ".dxf": "drawing",
    ".eml": "correspondence",
    ".msg": "correspondence",
    ".jpg": "photo",
    ".jpeg": "photo",
    ".png": "photo",
    ".heic": "photo",
}

_FILENAME_SIGNALS: list[tuple[re.Pattern[str], DocumentClass, int]] = [
    # strong
    (re.compile(r"\bcost plan\b", re.I), "commercial", 5),
    (re.compile(r"\bpayment plan\b", re.I), "commercial", 5),
    (re.compile(r"\btax invoice\b|\binvoice\b", re.I), "commercial", 5),
    (re.compile(r"\bvariation\b|\bVO[- ]?\d+\b", re.I), "commercial", 5),
    (re.compile(r"\bfee proposal\b", re.I), "commercial", 5),
    (re.compile(r"\bprogress claim\b", re.I), "commercial", 5),
    (re.compile(r"\btender\b|\bRFT\b|\bEOI\b", re.I), "commercial", 4),
    (re.compile(r"\bspecification\b", re.I), "specification", 5),
    (re.compile(r"\bcertificate\b|\bconsent\b|\bdetermination\b", re.I), "certificate", 5),
    (re.compile(r"\bcontract\b|\bagreement\b|\bdeed\b", re.I), "contract", 5),
    (re.compile(r"\bLEP\b|\bDCP\b|\bSEPP\b", re.I), "statutory_instrument", 5),
    # drawing structure beats prose words
    (re.compile(r"^M\d{2,3}\b", re.I), "drawing", 5),
    (re.compile(r"\b[A-Z]{1,2}-?\d{3}\b"), "drawing", 5),  # A-101, S203
    (re.compile(r"\b(floor|site|roof|landscape) plan\b", re.I), "drawing", 4),
    (re.compile(r"\belevation\b|\bsection\b|\bdetail\b", re.I), "drawing", 4),
    (re.compile(r"\brev [A-Z]\b", re.I), "drawing", 3),
    # medium
    (re.compile(r"\breport\b|\bassessment\b|\bstatement\b", re.I), "report", 3),
    (re.compile(r"\bregister\b|\bschedule\b|\bmatrix\b", re.I), "schedule", 3),
    (re.compile(r"\bletter\b|\bnotice\b|\bRFI\b|\bminutes\b", re.I), "correspondence", 3),
    (re.compile(r"\bprogramme\b|\bgantt\b|\blookahead\b", re.I), "schedule", 4),
    # weak — must never decide alone
    (re.compile(r"\bplan\b", re.I), "drawing", 1),
    (re.compile(r"\bcost\b|\bbudget\b|\bestimate\b", re.I), "commercial", 2),
]

_SUBJECT_SIGNALS: list[tuple[re.Pattern[str], DocumentSubject, int]] = [
    (re.compile(r"\bheritage\b", re.I), "heritage", 5),
    (re.compile(r"\bstructural\b", re.I), "structural", 5),
    (re.compile(r"\bhydraulic\b", re.I), "hydraulic", 5),
    (re.compile(r"\bgeotechnical\b|\bgeotech\b", re.I), "geotechnical", 5),
    (re.compile(r"\bacoustic\b", re.I), "acoustic", 5),
    (re.compile(r"\bsustainab", re.I), "sustainability", 5),
    (re.compile(r"\bdefect", re.I), "defects", 5),
    (re.compile(r"\bmechanical\b|\belectrical\b|\bservices\b", re.I), "services", 4),
    (re.compile(r"\bfire\b", re.I), "fire", 4),
    (re.compile(r"\bsurvey\b", re.I), "survey", 4),
    (re.compile(r"\binvoice\b|\bcost\b|\bbudget\b|\bpayment\b", re.I), "cost", 4),
    (re.compile(r"\bprogramme\b|\bgantt\b|\blookahead\b", re.I), "programme", 4),
    (re.compile(r"\bvariation\b|\bEOT\b|\bcontract admin", re.I), "contract_admin", 4),
    (re.compile(r"\bplanning\b|\bcouncil\b|\bdetermination\b|\bconsent\b", re.I), "planning", 4),
    (re.compile(r"\baccess\b|\bDDA\b", re.I), "access", 4),
]

_PLANNING_INSTRUMENT_EXCLUDE_RE = re.compile(
    r"\b(assessment|report|statement|review)\b",
    re.IGNORECASE,
)

_CONTENT_MARKERS: list[
    tuple[re.Pattern[str], DocumentClass, DocumentSubject, dict[str, str], float]
] = [
    (re.compile(r"\bTAX INVOICE\b", re.I), "commercial", "cost",
     {"commercial_type": "invoice"}, 0.95),
    (re.compile(r"\bHERITAGE IMPACT STATEMENT\b", re.I), "report", "heritage", {}, 0.95),
    (re.compile(r"\bBUSINESS PLAN\b", re.I), "report", "none", {}, 0.85),
    (re.compile(r"\bCONDITIONS OF CONSENT\b|\bNOTICE OF DETERMINATION\b", re.I),
     "certificate", "planning", {}, 0.95),
    (re.compile(r"\bREQUEST FOR TENDER\b", re.I), "commercial", "none",
     {"procurement_stage": "rft"}, 0.90),
    (re.compile(r"\bTENDER SUBMISSION\b|\blump sum tender price\b", re.I), "commercial", "none",
     {"procurement_stage": "submission"}, 0.90),
    (re.compile(r"\bELEMENTAL COST PLAN\b|\bCOST PLAN\b", re.I), "commercial", "cost",
     {"commercial_type": "cost_plan"}, 0.90),
    (re.compile(r"\bVARIATION\b.{0,80}\$", re.I | re.S), "commercial", "contract_admin",
     {"commercial_type": "variation"}, 0.85),
    (re.compile(r"\bGEOTECHNICAL INVESTIGATION\b", re.I), "report", "geotechnical", {}, 0.90),
    (re.compile(r"^\s*Dear\b.*\bYours (sincerely|faithfully)\b", re.I | re.S | re.M),
     "correspondence", "none", {}, 0.85),
]


@dataclass(frozen=True, slots=True)
class FilenameScore:
    winner: DocumentClass | None
    subject: DocumentSubject
    scores: dict[str, int] = field(default_factory=dict)
    margin: int = 0
    winner_score: int = 0


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


def _pick_winner(scores: dict[str, int]) -> tuple[str | None, int, int]:
    if not scores:
        return None, 0, 0
    ranked = sorted(scores.values(), reverse=True)
    winner_score = ranked[0]
    runner_up = ranked[1] if len(ranked) > 1 else 0
    margin = winner_score - runner_up
    if margin < _FILENAME_MARGIN:
        return None, winner_score, margin
    winner = max(scores, key=scores.get)  # type: ignore[arg-type]
    return winner, winner_score, margin


def score_filename(filename: str) -> FilenameScore:
    scores: dict[str, int] = {}
    for pattern, document_class, points in _FILENAME_SIGNALS:
        if not pattern.search(filename):
            continue
        if (
            document_class == "statutory_instrument"
            and _PLANNING_INSTRUMENT_EXCLUDE_RE.search(filename)
        ):
            continue
        scores[document_class] = scores.get(document_class, 0) + points

    identity = parse_drawing_filename(filename)
    if identity.drawing_number:
        scores["drawing"] = scores.get("drawing", 0) + 5

    winner, winner_score, margin = _pick_winner(scores)
    return FilenameScore(
        winner=winner,  # type: ignore[arg-type]
        subject=_score_subject(filename),
        scores=scores,
        margin=margin,
        winner_score=winner_score,
    )


def _score_subject(text: str) -> DocumentSubject:
    scores: dict[str, int] = {}
    for pattern, subject, points in _SUBJECT_SIGNALS:
        if pattern.search(text):
            scores[subject] = scores.get(subject, 0) + points
    winner, _, _ = _pick_winner(scores)
    if winner is None:
        return "none"
    return winner  # type: ignore[return-value]


def _filename_confidence(winner_score: int, margin: int) -> float:
    if winner_score >= 5 and margin >= 4:
        return 0.90
    if winner_score >= 4:
        return 0.80
    return 0.65


def _structural_class(
    *,
    extension: str,
    filename: str,
    title_block: TitleBlockFields | None,
) -> DocumentClass | None:
    mapped = _STRUCTURAL_EXTENSIONS.get(extension)
    if mapped is not None:
        return mapped
    if title_block is not None and title_block.document_number:
        return "drawing"
    identity = parse_drawing_filename(filename)
    if identity.drawing_number and extension in {".pdf", ".md", ".dwg", ".dxf"}:
        return "drawing"
    if re.match(r"^M\d{2,3}\b", filename, re.I) and extension in {".pdf", ".md"}:
        return "drawing"
    return None


def _content_match(
    extracted_text: str,
) -> tuple[DocumentClass, DocumentSubject, dict[str, str], float] | None:
    sample = extracted_text[:_CONTENT_SAMPLE_CHARS]
    for pattern, document_class, subject, extra, confidence in _CONTENT_MARKERS:
        if pattern.search(sample):
            return document_class, subject, extra, confidence
    return None


def _user_override(_entry: ManifestEntry) -> Classification | None:
    """Cascade Stage A fallback. Callers pass an already-resolved override."""
    return None


def _classification(
    document_class: DocumentClass,
    *,
    basis: ClassificationBasis,
    confidence: float,
    metadata: dict[str, str],
    subject: DocumentSubject,
    extracted_text: str | None = None,
) -> Classification:
    merged = dict(metadata)
    document_subject = subject
    if extracted_text:
        content = _content_match(extracted_text)
        if content is not None:
            _, content_subject, extra, _ = content
            for key, value in extra.items():
                merged.setdefault(key, value)
            if document_subject == "none" and content_subject != "none":
                document_subject = content_subject
    merged["confidence"] = f"{confidence:.2f}"
    merged["basis"] = basis
    merged["subject"] = document_subject
    return Classification(
        document_class=document_class,
        ingest_mode=_ingest_mode_for_class(document_class),
        document_metadata=merged,
        document_subject=document_subject,
        confidence=confidence,
        basis=basis,
    )


def classify_entry(
    entry: ManifestEntry,
    extracted_text: str | None = None,
    title_block: TitleBlockFields | None = None,
    *,
    override: Classification | None = None,
) -> Classification:
    resolved = override if override is not None else _user_override(entry)
    if resolved is not None:
        return resolved

    context = infer_project_context(entry.relative_path)
    metadata = parse_procurement_stage(entry.relative_path)
    extension = entry.extension.lower()
    filename = entry.filename
    scored = score_filename(filename)
    subject = scored.subject

    identity = parse_drawing_filename(filename)
    if identity.drawing_number:
        metadata.setdefault("drawing_number", identity.drawing_number)
        metadata.setdefault("format", extension.lstrip(".") or "pdf")
    if identity.revision:
        metadata.setdefault("revision", identity.revision)
    if identity.title:
        metadata.setdefault("title", identity.title)

    structural = _structural_class(
        extension=extension, filename=filename, title_block=title_block
    )
    if structural is not None:
        return _classification(
            structural,
            basis="structural",
            confidence=0.95,
            metadata=metadata,
            subject=subject,
            extracted_text=extracted_text,
        )

    if context.source_type == "doctrine":
        document_class, metadata = canonicalize_document_class("doctrine", metadata)
        return _classification(
            document_class,
            basis="structural",
            confidence=0.95,
            metadata=metadata,
            subject=subject,
            extracted_text=extracted_text,
        )
    if context.source_type == "reference":
        document_class, metadata = canonicalize_document_class("reference_guide", metadata)
        return _classification(
            document_class,
            basis="structural",
            confidence=0.95,
            metadata=metadata,
            subject=subject,
            extracted_text=extracted_text,
        )

    if metadata.get("procurement_stage"):
        return _classification(
            "commercial",
            basis="filename",
            confidence=0.85,
            metadata=metadata,
            subject=subject,
            extracted_text=extracted_text,
        )

    if scored.winner is not None:
        return _classification(
            scored.winner,
            basis="filename",
            confidence=_filename_confidence(scored.winner_score, scored.margin),
            metadata=metadata,
            subject=subject,
            extracted_text=extracted_text,
        )

    content = _content_match(extracted_text) if extracted_text else None
    if content is not None:
        document_class, content_subject, extra, confidence = content
        metadata.update(extra)
        return _classification(
            document_class,
            basis="content",
            confidence=confidence,
            metadata=metadata,
            subject=content_subject,
        )

    return _classification(
        "unknown",
        basis="default",
        confidence=0.0,
        metadata=metadata,
        subject=subject,
    )
