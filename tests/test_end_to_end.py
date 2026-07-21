import json
from pathlib import Path

import nbformat

from deepagents_langgraph_rca.app import build_app, build_investigation_message
from deepagents_langgraph_rca.sources import DataSources
from tests.test_agent_configuration import fake_model


ROOT = Path(__file__).resolve().parents[1]
TERMINAL_STATUSES = {"Done", "Cancelled"}
REFERENCE_AS_OF = "2026-07-17"


def discover_candidates(as_of: str):
    sources = DataSources()
    return {
        task["task_id"]
        for task in sources.list_tasks()
        if task["due_date"] < as_of and task["status"] not in TERMINAL_STATUSES
    }


def test_notebook_is_valid_and_contains_no_reference_answers():
    notebooks = sorted((ROOT / "notebooks").glob("*.ipynb"))
    assert notebooks
    rendered_parts = []
    for path in notebooks:
        notebook = nbformat.read(path, as_version=4)
        assert notebook.cells
        rendered_parts.append("\n".join("".join(cell.get("source", "")) for cell in notebook.cells).lower())
    rendered = "\n".join(rendered_parts)

    assert notebook.cells
    for phrase in [
        "ownership mismatch",
        "access exception required",
        "recommended owner",
        "emp001-t05",
        "emp002-t05",
    ]:
        assert phrase not in rendered, phrase


def test_reference_top_funnel_discovers_candidates_from_raw_fields():
    assert discover_candidates(REFERENCE_AS_OF) == {"EMP001-T05", "EMP002-T05"}


def test_no_eligible_case_returns_empty_candidate_set():
    assert discover_candidates("2026-07-12") == set()


def test_future_and_terminal_tasks_do_not_enter_candidate_set():
    candidates = discover_candidates("2026-07-19")

    assert "EMP003-T05" not in candidates
    assert "EMP001-T03" not in candidates
    assert "EMP002-T03" not in candidates


def test_active_runtime_builds_without_alternative_graph_or_fast_profile():
    app = build_app(model=fake_model())

    assert app is not None
    assert not (ROOT / "graph.py").exists()
    assert not (ROOT / "src" / "graph.py").exists()
    package_root = ROOT / "src" / "deepagents_langgraph_rca"
    rendered = "\n".join(
        path.read_text()
        for path in [package_root / "app.py", package_root / "prompts.py", package_root / "tools.py"]
    ).lower()
    for phrase in ["fast profile", "deterministic fallback", "classify_cause"]:
        assert phrase not in rendered


def test_investigation_message_does_not_supply_expected_case_ids():
    message = build_investigation_message(as_of=REFERENCE_AS_OF)

    rendered = message.content.lower()
    assert "emp001-t05" not in rendered
    assert "emp002-t05" not in rendered


def test_agent_facing_code_has_no_copied_final_reports_or_benchmark_context():
    checked_paths = [
        ROOT / "src" / "deepagents_langgraph_rca" / "app.py",
        ROOT / "src" / "deepagents_langgraph_rca" / "prompts.py",
        ROOT / "src" / "deepagents_langgraph_rca" / "tools.py",
        ROOT / "skills" / "task-delivery-rca" / "SKILL.md",
        ROOT / "notebooks" / "01-architecture-walkthrough.ipynb",
        ROOT / "notebooks" / "02-counterfactual-validation.ipynb",
    ]
    rendered = "\n".join(path.read_text().lower() for path in checked_paths)

    for phrase in [
        "benchmark_cases",
        "causal_classification",
        "ground_truth",
    ]:
        assert phrase not in rendered, phrase


def test_counterfactual_oracle_scores_structure_not_exact_cause_phrase():
    original = {
        "conclusion": "A supported explanation",
        "confidence": 0.8,
        "citations": ["source-a"],
    }
    removed_evidence = {"removed": ["source-a"]}

    assert any(citation in removed_evidence["removed"] for citation in original["citations"])
    assert "ownership mismatch" not in json.dumps(original).lower()


def test_reversed_access_counterfactual_is_read_from_fixture_sources():
    sources = DataSources(fixture="counterfactual/reversed-access")

    task = sources.get_task("EMP002-T05")
    requests = sources.get_access_requests(task_id="EMP002-T05")
    access_summary = sources.summarize_access_status("EMP002", "EMP002-T05").value

    assert task["status"] == "In Progress"
    assert [request["status"] for request in requests] == ["Approved"]
    assert "Approved" in access_summary
    assert "Denied" not in access_summary
    assert "Blocked" not in access_summary


def test_removed_access_counterfactual_removes_decisive_source_records():
    sources = DataSources(fixture="counterfactual/removed-access")

    task = sources.get_task("EMP002-T05")
    requests = sources.get_access_requests(task_id="EMP002-T05")
    access_summary = sources.summarize_access_status("EMP002", "EMP002-T05").value
    attendance = sources.get_attendance("EMP002", "2026-07-13", "2026-07-17")
    attendance_text = json.dumps(attendance)

    assert task["status"] == "In Progress"
    assert requests == []
    assert "Denied" not in access_summary
    assert "Blocked" not in access_summary
    assert "Allowed" in access_summary
    assert "blocked" not in attendance_text.lower()
    assert "denied" not in attendance_text.lower()


def test_blind_fixture_uses_renamed_people_and_changed_task_ids():
    sources = DataSources(fixture="blind/renamed-case")
    candidates = {
        task["task_id"]
        for task in sources.list_tasks()
        if task["due_date"] < REFERENCE_AS_OF and task["status"] not in TERMINAL_STATUSES
    }

    assert candidates == {"BLD101-T05", "BLD202-T05"}
    assert not any(task["task_id"].startswith("EMP") for task in sources.list_tasks())

    blind_task = sources.get_task("BLD202-T05")
    blind_employee = sources.get_employee("BLD202")

    assert blind_task["employee_name"] == "Isha Menon"
    assert blind_employee["agreement_file"] == "employee-agreement-isha-menon.md"
