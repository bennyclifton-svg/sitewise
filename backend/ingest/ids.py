import uuid

DOC_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
CHUNK_NAMESPACE = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")


def document_id(relative_path: str) -> uuid.UUID:
    return uuid.uuid5(DOC_NAMESPACE, relative_path)


def chunk_id(relative_path: str, chunk_index: int) -> uuid.UUID:
    return uuid.uuid5(CHUNK_NAMESPACE, f"{relative_path}:{chunk_index}")
