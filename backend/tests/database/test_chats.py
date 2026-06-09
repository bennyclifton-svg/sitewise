from app.database.chats import title_from_message


def test_title_from_message_short_text() -> None:
    assert title_from_message("Hello world") == "Hello world"


def test_title_from_message_collapses_whitespace() -> None:
    assert title_from_message("  Hello   world  ") == "Hello world"


def test_title_from_message_truncates_long_text() -> None:
    text = "a" * 80
    title = title_from_message(text)
    assert len(title) == 60
    assert title.endswith("…")
