import re

# Supabase Storage rejects keys outside this S3-safe set (see supabase/storage isValidKey).
_STORAGE_KEY_SAFE_CHAR = re.compile(r"[\w/!\.\*'() &\$@=;:+,?\-]")


def sanitize_storage_key(key: str) -> str:
    return "".join(
        char if _STORAGE_KEY_SAFE_CHAR.fullmatch(char) else "_"
        for char in key
    )
