import re

# Postgres text columns reject NUL bytes; PDFs sometimes yield control noise.
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def sanitize_text(text: str) -> str:
    return _CONTROL_CHAR_RE.sub("", text)
