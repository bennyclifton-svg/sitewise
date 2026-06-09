import re

_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")

_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "could",
    "did",
    "do",
    "does",
    "for",
    "from",
    "give",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "of",
    "on",
    "or",
    "please",
    "show",
    "summarise",
    "summarize",
    "tell",
    "that",
    "the",
    "their",
    "there",
    "this",
    "to",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
    "would",
    "you",
}


def lexical_query_text(query: str, *, max_terms: int = 12) -> str:
    tokens: list[str] = []
    seen: set[str] = set()

    for match in _TOKEN_RE.finditer(query):
        raw = match.group(0)
        token = raw.lower().strip("_-")
        if not token:
            continue
        if token in _STOPWORDS:
            continue
        if len(token) < 3 and not token.isdigit():
            continue
        if token in seen:
            continue
        seen.add(token)
        tokens.append(token)
        if len(tokens) >= max_terms:
            break

    if not tokens:
        return query.strip()
    return " ".join(tokens)
