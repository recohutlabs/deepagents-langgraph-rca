import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TASK_DIR = DATA / "tasks"
DB_PATH = DATA / "operations" / "employee_operations.sqlite"
SCENARIO_DATE = "2026-07-17"
TERMINAL_STATUSES = {"Done", "Cancelled"}
REFERENCE_CANDIDATES = {"EMP001-T05", "EMP002-T05"}
PROHIBITED_KEYS = {
    "recommended_owner_role",
    "recommended_owner_employee_id",
    "required_capability",
}
PROHIBITED_TEXT = {
    "ownership mismatch",
    "access exception required",
    "recommended product analytics owner",
    "benchmark_answer",
    "ground_truth",
    "primary cause",
    "causal_classification",
    "not overdue",
    "overdue blocked task",
}


def load_tasks():
    records = []
    for path in sorted(TASK_DIR.glob("*.json")):
        payload = json.loads(path.read_text())
        for task in payload["tasks"]:
            records.append((path, task))
    return records


def test_reference_task_json_has_no_answer_bearing_fields_or_labels():
    for path, task in load_tasks():
        assert not (PROHIBITED_KEYS & set(task)), (path.name, task["task_id"])
        rendered = json.dumps(task, sort_keys=True).lower()
        for phrase in PROHIBITED_TEXT:
            assert phrase not in rendered, (path.name, task["task_id"], phrase)


def test_july_18_tasks_are_terminal_but_remain_present():
    july_18_tasks = [
        task
        for _, task in load_tasks()
        if task["due_date"] == "2026-07-18"
    ]
    assert july_18_tasks
    assert all(task["status"] in TERMINAL_STATUSES for task in july_18_tasks)
    assert all("actual_hours" in task for task in july_18_tasks)


def test_done_tasks_have_completion_dates_and_actual_hours():
    for path, task in load_tasks():
        if task["status"] == "Done":
            assert task.get("completed_date"), (path.name, task["task_id"])
            assert isinstance(task.get("actual_hours"), (int, float)), (
                path.name,
                task["task_id"],
            )


def test_sqlite_task_statuses_match_json_statuses():
    expected = {task["task_id"]: task["status"] for _, task in load_tasks()}
    with sqlite3.connect(DB_PATH) as conn:
        actual = dict(conn.execute("SELECT id, status FROM task"))
    assert actual == expected


def test_sqlite_notes_do_not_contain_answer_bearing_text():
    with sqlite3.connect(DB_PATH) as conn:
        rows = list(
            conn.execute(
                """
                SELECT 'task' AS table_name, id AS record_id, notes FROM task
                UNION ALL
                SELECT 'employees' AS table_name, emp_id AS record_id, notes FROM employees
                """
            )
        )
    for table_name, record_id, notes in rows:
        text = (notes or "").lower()
        for phrase in PROHIBITED_TEXT:
            assert phrase not in text, (table_name, record_id, phrase)


def test_reference_candidate_discovery_from_raw_fields():
    candidates = {
        task["task_id"]
        for _, task in load_tasks()
        if task["due_date"] < SCENARIO_DATE
        and task["status"] not in TERMINAL_STATUSES
    }
    assert candidates == REFERENCE_CANDIDATES


def test_active_policies_are_available_and_do_not_contain_benchmark_answers():
    policies = sorted((DATA / "policies").glob("*.md"))
    assert {path.name for path in policies} == {
        "information-security-policy.md",
        "leave-policy.md",
        "remote-security-policy.md",
        "working-hours-policy.md",
    }
    for path in policies:
        text = path.read_text().lower()
        for phrase in PROHIBITED_TEXT:
            assert phrase not in text, (path.name, phrase)
