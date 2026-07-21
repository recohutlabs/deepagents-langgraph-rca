from __future__ import annotations

from deepagents.middleware.filesystem import _check_fs_permission

from deepagents_langgraph_rca.app import build_filesystem_permissions


def test_agent_cannot_directly_read_authoritative_or_private_paths():
    rules = build_filesystem_permissions()

    assert _check_fs_permission(rules, "read", "/data/tasks/employee.json") == "deny"
    assert _check_fs_permission(rules, "read", "/docs/evidence.md") == "deny"
    assert _check_fs_permission(rules, "read", "/tests/test_sources.py") == "deny"
    assert _check_fs_permission(rules, "read", "/.env") == "deny"


def test_agent_can_read_skills_and_write_only_run_workspace():
    rules = build_filesystem_permissions()

    assert _check_fs_permission(rules, "read", "/skills/task-delivery-rca/SKILL.md") == "allow"
    assert _check_fs_permission(rules, "write", "/skills/task-delivery-rca/SKILL.md") == "deny"
    assert _check_fs_permission(rules, "write", "/runs/demo/plan.json") == "allow"
    assert _check_fs_permission(rules, "write", "/README.md") == "deny"
