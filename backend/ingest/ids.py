import uuid

DOC_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
CHUNK_NAMESPACE = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")


def document_id(
    relative_path: str,
    *,
    project_id: uuid.UUID | None = None,
) -> uuid.UUID:
    identity = f"project:{project_id}:{relative_path}" if project_id else relative_path
    return uuid.uuid5(DOC_NAMESPACE, identity)


def chunk_id(document_id: uuid.UUID, chunk_index: int) -> uuid.UUID:
    return uuid.uuid5(CHUNK_NAMESPACE, f"{document_id}:{chunk_index}")
