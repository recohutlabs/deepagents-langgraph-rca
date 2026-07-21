import json
import shutil

from deepagents.middleware.filesystem import _check_fs_permission

from deepagents_langgraph_rca.app import (
    build_app,
    build_filesystem_backend,
    build_filesystem_permissions,
    ensure_run_workspace,
    run_workspace_dir,
    write_case_artifact,
)
from deepagents_langgraph_rca.config import load_config
from tests.test_agent_configuration import fake_model


def test_permission_rules_allow_and_deny_expected_paths():
    rules = build_filesystem_permissions()

    assert _check_fs_permission(rules, "read", "/.env") == "deny"
    assert _check_fs_permission(rules, "read", "/legacy/main.ipynb") == "deny"
    assert _check_fs_permission(rules, "read", "/data/tasks/example.json") == "deny"
    assert _check_fs_permission(rules, "read", "/tests/test_data_integrity.py") == "deny"
    assert _check_fs_permission(rules, "read", "/skills/task-delivery-rca/SKILL.md") == "allow"
    assert _check_fs_permission(rules, "write", "/skills/task-delivery-rca/SKILL.md") == "deny"
    assert _check_fs_permission(rules, "write", "/runs/run-1/plan.json") == "allow"
    assert _check_fs_permission(rules, "read", "/random.txt") == "deny"


def test_backend_can_read_and_write_allowed_workspace_path():
    backend = build_filesystem_backend(load_config(require_model=False))
    shutil.rmtree(run_workspace_dir("backend-smoke"), ignore_errors=True)
    result = backend.write("/runs/backend-smoke/plan.json", '{"ok": true}')
    assert not result.error

    read = backend.read("/runs/backend-smoke/plan.json")
    assert '"ok": true' in read.file_data["content"]
    shutil.rmtree(run_workspace_dir("backend-smoke"), ignore_errors=True)


def test_case_artifact_helpers_write_expected_files():
    run_id = "artifact-smoke"
    expected = {
        "plan.json",
        "timeline.json",
        "workload.json",
        "dependency_access.json",
        "contract_policy.json",
        "evidence_review.json",
        "final_rca.json",
        "final_rca.md",
        "channel_message.md",
        "approval_record.json",
        "feedback_record.json",
    }

    directory = ensure_run_workspace(run_id)
    for filename in expected:
        content = "# ok" if filename.endswith(".md") else {"ok": True, "file": filename}
        write_case_artifact(run_id, filename, content)

    assert {path.name for path in directory.iterdir()} == expected
    assert json.loads((directory / "plan.json").read_text())["ok"] is True
    shutil.rmtree(directory, ignore_errors=True)


def test_artifact_helpers_reject_path_traversal():
    try:
        write_case_artifact("../bad", "plan.json", {})
    except ValueError as exc:
        assert "run_id" in str(exc)
    else:
        raise AssertionError("Expected run_id path traversal rejection")

    try:
        write_case_artifact("good", "../plan.json", {})
    except ValueError as exc:
        assert "artifact filename" in str(exc)
    else:
        raise AssertionError("Expected artifact filename path traversal rejection")
    shutil.rmtree(run_workspace_dir("good"), ignore_errors=True)


def test_build_app_attaches_filesystem_backend_and_permissions():
    app = build_app(model=fake_model())

    assert app is not None
    assert build_filesystem_permissions()
