from langchain_openai import ChatOpenAI
from langgraph.graph.state import CompiledStateGraph

from deepagents_langgraph_rca.app import (
    COORDINATOR_SYSTEM_PROMPT,
    build_app,
    build_investigation_message,
    default_as_of_date,
    thread_config,
)
from deepagents_langgraph_rca.config import load_config
from deepagents_langgraph_rca.prompts import SUBAGENT_NAMES, build_subagents
from deepagents_langgraph_rca.schemas import RCAReport
from deepagents_langgraph_rca.tools import build_tools


def fake_model():
    config = load_config(require_model=False)
    return ChatOpenAI(
        model=config.model.model,
        api_key="test-key",
        base_url=config.model.base_url,
        temperature=0,
    )


def test_build_app_returns_one_compiled_langgraph_runtime():
    app = build_app(model=fake_model())

    assert isinstance(app, CompiledStateGraph)


def test_registered_subagents_are_exactly_the_required_five():
    subagents = build_subagents(build_tools(), load_config(require_model=False))

    assert [item["name"] for item in subagents] == list(SUBAGENT_NAMES)
    assert len(subagents) == 5


def test_coordinator_prompt_requires_dynamic_delegation_and_reviewer_order():
    prompt = COORDINATOR_SYSTEM_PROMPT.lower()

    assert "if the user omits as_of" in prompt
    assert default_as_of_date() in prompt
    assert "choose evidence specialists dynamically" in prompt
    assert "run the evidence privacy reviewer after specialist packets exist" in prompt
    assert "produce final synthesis only after reviewer output" in prompt
    assert "do not invent adjacent task ids" in prompt
    assert "insufficient evidence rather than continuing to search indefinitely" in prompt
    assert "all four evidence specialists" not in prompt


def test_investigation_message_accepts_as_of_and_optional_task_id():
    message = build_investigation_message(as_of="2026-07-17", task_id="TASK-1")

    assert "as_of=2026-07-17" in message.content
    assert "task_id=TASK-1" in message.content


def test_investigation_message_defaults_missing_as_of_to_system_date():
    message = build_investigation_message()

    assert f"as_of={default_as_of_date()}" in message.content


def test_architecture_coverage_message_can_force_all_specialists_only_when_requested():
    normal = build_investigation_message(as_of="2026-07-17")
    coverage = build_investigation_message(as_of="2026-07-17", force_all_specialists=True)

    assert "Delegate only to specialists" in normal.content
    assert "deliberately invoke all four evidence specialists" in coverage.content


def test_thread_config_uses_stable_thread_id():
    assert thread_config("run-1") == {"configurable": {"thread_id": "run-1"}}


def test_default_response_format_is_rca_report():
    assert RCAReport.__name__ in repr(RCAReport)
