from app.agent.task_routing import route_ai_task


def test_structured_operations_do_not_route_to_a_model() -> None:
    route = route_ai_task("delete this row", has_structured_operation=True)
    assert route.task_class == "DETERMINISTIC"
    assert route.retrieval == "none"


def test_small_semantic_addition_uses_fast_path_without_retrieval() -> None:
    route = route_ai_task("Add a suitable kitchen mixer")
    assert route.task_class == "FAST_SEMANTIC"
    assert route.retrieval == "none"


def test_conflict_uses_targeted_reasoning_and_narrative_is_separate() -> None:
    assert (
        route_ai_task("Reconcile conflicting hydraulic requirements").task_class
        == "REASONING"
    )
    assert (
        route_ai_task("Write the Design Management section").task_class == "NARRATIVE"
    )
