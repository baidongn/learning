"""最终四项课程指标的计算与门槛测试。"""

from highway_agent.evaluation import EvaluationRecord, evaluate_records


def _record(**overrides: object) -> EvaluationRecord:
    payload: dict[str, object] = {
        "case_id": "EVAL-001",
        "expected_tools": ["query_road_status", "query_weather_warning"],
        "actual_tools": ["query_road_status", "query_weather_warning"],
        "structured_output_valid": True,
        "scenario_success": True,
        "human_approved": False,
        "executed_actions": [],
    }
    payload.update(overrides)
    return EvaluationRecord.model_validate(payload)


def test_perfect_records_pass_all_acceptance_thresholds() -> None:
    summary = evaluate_records([_record(case_id=f"EVAL-{index:03d}") for index in range(10)])

    assert summary.structured_output_rate == 1.0
    assert summary.tool_selection_accuracy == 1.0
    assert summary.scenario_success_rate == 1.0
    assert summary.unauthorized_action_rate == 0.0
    assert summary.passed is True


def test_metrics_fail_when_tool_selection_or_scenario_rate_is_too_low() -> None:
    records = [_record(case_id=f"EVAL-{index:03d}") for index in range(10)]
    records[0] = _record(case_id="EVAL-BAD-TOOL", actual_tools=["query_road_status"])
    records[1] = _record(case_id="EVAL-BAD-SCENE", scenario_success=False)
    records[2] = _record(case_id="EVAL-BAD-SCENE-2", scenario_success=False)

    summary = evaluate_records(records)

    assert summary.tool_selection_accuracy == 0.9
    assert summary.scenario_success_rate == 0.8
    assert summary.passed is False


def test_unapproved_action_is_counted_as_security_failure() -> None:
    summary = evaluate_records(
        [_record(executed_actions=["dispatch_resource"], human_approved=False)]
    )

    assert summary.unauthorized_action_rate == 1.0
    assert summary.passed is False
