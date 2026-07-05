from app.agent.pi_process import text_delta_from_pi_event


def test_text_delta_from_pi_event_returns_assistant_text_delta() -> None:
    line = (
        '{"type":"message_update","assistantMessageEvent":'
        '{"type":"text_delta","delta":"hello"}}'
    )
    assert text_delta_from_pi_event(line) == "hello"


def test_text_delta_from_pi_event_ignores_non_text_events() -> None:
    line = '{"type":"tool_execution_start","toolName":"clerk_search_documents"}'
    assert text_delta_from_pi_event(line) is None
