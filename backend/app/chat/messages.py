from typing import Any


def extract_text_from_ui_message(message: dict[str, Any]) -> str | None:
    parts = message.get("parts")
    if isinstance(parts, list):
        texts: list[str] = []
        for part in parts:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "text" and isinstance(part.get("text"), str):
                texts.append(part["text"])
        if texts:
            return "".join(texts)

    content = message.get("content")
    if isinstance(content, str):
        return content

    return None


def extract_last_user_message(messages: list[dict[str, Any]]) -> str | None:
    for message in reversed(messages):
        if message.get("role") != "user":
            continue
        text = extract_text_from_ui_message(message)
        if text and text.strip():
            return text.strip()
    return None
