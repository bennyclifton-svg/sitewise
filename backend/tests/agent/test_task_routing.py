from app.agent.task_routing import (
    TASK_CLASS_MODELS,
    route_ai_task,
    task_route_telemetry,
)


def test_structured_operations_do_not_route_to_a_model() -> None:
    route = route_ai_task("delete this row", has_structured_operation=True)
    assert route.task_class == "DETERMINISTIC"
    assert route.retrieval == "none"
    assert route.path == "application"
    assert route.model is None


def test_deterministic_without_supplied_ops_uses_application_fast_path() -> None:
    route = route_ai_task("delete the hydraulic consultant row")
    assert route.task_class == "DETERMINISTIC"
    assert route.path == "application"
    assert route.retrieval == "none"
    assert route.model == TASK_CLASS_MODELS["DETERMINISTIC"]


def test_small_semantic_addition_uses_fast_path_without_retrieval() -> None:
    route = route_ai_task("Add a suitable kitchen mixer")
    assert route.task_class == "FAST_SEMANTIC"
    assert route.path == "fast_semantic"
    assert route.retrieval == "none"
    assert route.model == TASK_CLASS_MODELS["FAST_SEMANTIC"]


def test_conflict_uses_targeted_reasoning_and_narrative_is_separate() -> None:
    reasoning = route_ai_task("Reconcile conflicting hydraulic requirements")
    assert reasoning.task_class == "REASONING"
    assert reasoning.path == "reasoning"
    assert reasoning.retrieval == "targeted"
    assert reasoning.model == TASK_CLASS_MODELS["REASONING"]

    narrative = route_ai_task("Write the Design Management section")
    assert narrative.task_class == "NARRATIVE"
    assert narrative.path == "narrative"
    assert narrative.retrieval == "targeted"
    assert narrative.model == TASK_CLASS_MODELS["NARRATIVE"]


def test_task_route_telemetry_records_class_path_model_and_usage() -> None:
    route = route_ai_task("Add a suitable kitchen mixer")
    payload = task_route_telemetry(
        route,
        latency_ms=42,
        usage={"input_tokens": 10, "output_tokens": 4},
    )
    assert payload["task_class"] == "FAST_SEMANTIC"
    assert payload["path"] == "fast_semantic"
    assert payload["retrieval"] == "none"
    assert payload["model"] == TASK_CLASS_MODELS["FAST_SEMANTIC"]
    assert payload["latency_ms"] == 42
    assert payload["usage"] == {"input_tokens": 10, "output_tokens": 4}
    assert "reason" in payload
