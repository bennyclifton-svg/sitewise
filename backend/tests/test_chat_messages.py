from app.chat.messages import extract_last_user_message, extract_text_from_ui_message


def test_extract_text_from_parts() -> None:
    message = {
        "role": "user",
        "parts": [{"type": "text", "text": "Hello "}, {"type": "text", "text": "world"}],
    }
    assert extract_text_from_ui_message(message) == "Hello world"


def test_extract_text_from_legacy_content() -> None:
    message = {"role": "user", "content": "Legacy message"}
    assert extract_text_from_ui_message(message) == "Legacy message"


def test_extract_last_user_message_skips_assistant() -> None:
    messages = [
        {"role": "user", "parts": [{"type": "text", "text": "First"}]},
        {"role": "assistant", "parts": [{"type": "text", "text": "Reply"}]},
        {"role": "user", "parts": [{"type": "text", "text": "Second"}]},
    ]
    assert extract_last_user_message(messages) == "Second"


def test_extract_last_user_message_empty() -> None:
    assert extract_last_user_message([]) is None
