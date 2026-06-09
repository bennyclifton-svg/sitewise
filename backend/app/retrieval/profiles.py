from enum import StrEnum


class RetrievalProfile(StrEnum):
    INVENTORY = "inventory"
    REGISTER = "register"
    WHOLE_DOCUMENT = "whole_document"
    CHUNKED_VECTOR = "chunked_vector"


def derive_document_profile(
    *,
    document_class: str | None,
    ingest_mode: str | None,
) -> RetrievalProfile:
    if document_class == "drawing" and ingest_mode == "register_only":
        return RetrievalProfile.REGISTER
    if document_class in {"doctrine", "reference_guide"}:
        return RetrievalProfile.WHOLE_DOCUMENT
    if document_class == "report":
        return RetrievalProfile.CHUNKED_VECTOR
    return RetrievalProfile.CHUNKED_VECTOR
