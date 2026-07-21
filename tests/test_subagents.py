from deepagents_langgraph_rca.config import load_config
from deepagents_langgraph_rca.prompts import (
    SUBAGENT_NAMES,
    build_dynamic_delegation_guidance,
    build_subagents,
    skill_dir,
    skill_runtime_path,
)
from deepagents_langgraph_rca.schemas import SpecialistPacket
from deepagents_langgraph_rca.tools import build_tools


BANNED_PROMPT_TEXT = {
    "aarav",
    "maya",
    "kabir",
    "emp001",
    "emp002",
    "emp003",
    "ownership mismatch",
    "access exception required",
    "recommended owner",
}


def test_exactly_five_custom_subagents_are_registered():
    subagents = build_subagents(build_tools(), load_config(require_model=False))

    assert [subagent["name"] for subagent in subagents] == list(SUBAGENT_NAMES)
    assert len({subagent["name"] for subagent in subagents}) == 5


def test_each_subagent_has_required_shape_and_skill_path():
    config = load_config(require_model=False)
    subagents = build_subagents(build_tools(), config)

    for subagent in subagents:
        assert subagent["description"]
        assert subagent["system_prompt"]
        assert subagent["tools"]
        assert subagent["skills"] == [skill_runtime_path()]
        assert subagent["response_format"] is SpecialistPacket
    assert skill_dir(config).exists()


def test_subagents_have_distinct_controlled_tool_sets():
    subagents = build_subagents(build_tools(), load_config(require_model=False))
    tool_sets = {
        subagent["name"]: {tool.name for tool in subagent["tools"]}
        for subagent in subagents
    }

    assert "read_contract" in tool_sets["contract-policy-analyst"]
    assert "get_access_requests" in tool_sets["dependency-access-analyst"]
    assert "calculate_recorded_hours" in tool_sets["workload-priority-analyst"]
    assert "summarize_task_state_history" in tool_sets["task-timeline-analyst"]
    assert "evidence-privacy-reviewer" in tool_sets
    assert len({tuple(sorted(value)) for value in tool_sets.values()}) == 5


def test_custom_subagents_cannot_call_channel_publishing_tool():
    subagents = build_subagents(build_tools(), load_config(require_model=False))

    for subagent in subagents:
        tool_names = {tool.name for tool in subagent["tools"]}
        assert "send_channel_update" not in tool_names
        assert "send_slack_update" not in tool_names


def test_prompts_contain_no_reference_fixture_identifiers_or_expected_answers():
    subagents = build_subagents(build_tools(), load_config(require_model=False))
    rendered = "\n".join(subagent["system_prompt"].lower() for subagent in subagents)

    for phrase in BANNED_PROMPT_TEXT:
        assert phrase not in rendered, phrase


def test_prompts_require_bounded_missing_evidence_handling():
    subagents = build_subagents(build_tools(), load_config(require_model=False))
    rendered = "\n".join(subagent["system_prompt"].lower() for subagent in subagents)

    assert "do not invent task ids" in rendered
    assert "record missing evidence as an unknown" in rendered


def test_dynamic_delegation_guidance_requires_reviewer_not_all_specialists():
    guidance = build_dynamic_delegation_guidance().lower()

    assert "choose evidence specialists based on the case evidence needs" in guidance
    assert "reviewer is mandatory" in guidance
    assert "all five registered subagents must be exercised" in guidance
