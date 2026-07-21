import json
from dataclasses import replace

from deepagents_langgraph_rca.config import build_model, load_config
from deepagents_langgraph_rca.sources import DataSources
from deepagents_langgraph_rca.tools import build_tools


EXPECTED_TOOL_NAMES = {
    "list_tasks",
    "get_task",
    "list_employee_tasks",
    "get_employee",
    "get_attendance",
    "get_leave",
    "get_access_events",
    "get_access_requests",
    "read_contract",
    "list_policies",
    "read_policy",
    "calculate_days_overdue",
    "calculate_date_overlap",
    "calculate_task_counts",
    "calculate_recorded_hours",
    "calculate_approval_presence",
    "summarize_access_status",
    "calculate_vpn_compliance_status",
    "summarize_task_state_history",
}
PROHIBITED_TOOL_NAMES = {
    "scan_overdue_tasks",
    "check_role_scope",
    "find_access_barriers",
    "classify_cause",
}


def registry():
    tools = build_tools(DataSources(load_config(require_model=False)))
    return {tool.name: tool for tool in tools}


def parse_tool_output(value: str):
    return json.loads(value)


def test_registry_contains_expected_retrieval_and_metric_tools_only():
    tools = registry()

    assert set(tools) == EXPECTED_TOOL_NAMES
    assert not (set(tools) & PROHIBITED_TOOL_NAMES)


def test_list_tasks_returns_bounded_json_with_provenance():
    result = parse_tool_output(registry()["list_tasks"].invoke({"employee_id": "EMP002"}))

    assert result["row_count"] == 5
    assert result["truncated"] is False
    assert result["items"][0]["evidence"]


def test_get_access_requests_returns_raw_status_not_cause():
    result = parse_tool_output(
        registry()["get_access_requests"].invoke({"task_id": "EMP002-T05"})
    )

    rendered = json.dumps(result).lower()
    assert "denied" in rendered
    assert "primary cause" not in rendered
    assert "access exception required" not in rendered


def test_metric_tool_returns_inputs_and_evidence():
    result = parse_tool_output(
        registry()["calculate_days_overdue"].invoke(
            {"task_id": "EMP001-T05", "as_of": "2026-07-17"}
        )
    )

    assert result["metric"] == "days_overdue"
    assert result["value"] == 1
    assert result["inputs"] == {
        "task_id": "EMP001-T05",
        "due_date": "2026-07-16",
        "as_of": "2026-07-17",
    }
    assert result["evidence"]


def test_missing_source_tool_result_is_json_error_not_graph_exception():
    result = parse_tool_output(registry()["get_task"].invoke({"task_id": "missing"}))

    assert result["error"] == "SourceNotFoundError"
    assert "Task not found" in result["message"]


def test_tool_descriptions_do_not_suggest_causal_conclusions():
    rendered = " ".join(tool.description.lower() for tool in registry().values())

    assert "primary cause" not in rendered
    assert "recommended owner" not in rendered
    assert "role mismatch" not in rendered
    assert "access barrier" not in rendered


def test_tools_can_be_bound_to_configured_chat_model_without_network_call():
    config = load_config(require_model=False)
    model = build_model(replace(config, model=replace(config.model, api_key="test-key")))
    bound = model.bind_tools(list(registry().values()))
    assert bound is not None
