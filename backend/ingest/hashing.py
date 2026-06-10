import hashlib
from pathlib import Path


def bytes_content_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def file_content_hash(path: Path) -> str:
    return bytes_content_hash(path.read_bytes())
