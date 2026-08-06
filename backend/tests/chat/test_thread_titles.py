from types import SimpleNamespace

from app.chat import thread_titles
from tests.conftest import run_async


class _Responses:
    def __init__(
        self, *, output_text: str = "", error: Exception | None = None
    ) -> None:
        self.output_text = output_text
        self.error = error

    async def create(self, **kwargs):
        if self.error is not None:
            raise self.error
        return SimpleNamespace(output_text=self.output_text)


def test_generate_thread_title_derives_and_cleans_topic(monkeypatch) -> None:
    responses = _Responses(output_text='Title: "Structural Tender Review."')
    monkeypatch.setattr(
        thread_titles,
        "get_thread_title_client",
        lambda: SimpleNamespace(responses=responses),
    )

    title = run_async(
        thread_titles.generate_thread_title(
            "Can you compare the quotes and identify the structural tender risks?",
            "The comparison found three material qualifications in the structural scope.",
        )
    )

    assert title == "Structural Tender Review"


def test_generate_thread_title_falls_back_to_first_prompt(monkeypatch) -> None:
    monkeypatch.setattr(
        thread_titles,
        "get_thread_title_client",
        lambda: SimpleNamespace(responses=_Responses(error=RuntimeError("offline"))),
    )

    title = run_async(
        thread_titles.generate_thread_title(
            "  Compare   the tender quotes  ",
            "Three quotes were reviewed.",
        )
    )

    assert title == "Compare the tender quotes"


def test_normalise_generated_title_rejects_generic_names() -> None:
    assert (
        thread_titles.normalise_generated_title(
            "Untitled chat",
            fallback="Structural Tender Review",
        )
        == "Structural Tender Review"
    )
