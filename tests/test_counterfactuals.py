from __future__ import annotations

import json

from deepagents_langgraph_rca.sources import DataSources


def test_counterfactual_fixture_names_are_public_hyphenated_paths():
    assert DataSources(fixture="counterfactual/removed-access").get_task("EMP002-T05")
    assert DataSources(fixture="counterfactual/reversed-access").get_task("EMP002-T05")
    assert DataSources(fixture="blind/renamed-case").get_task("BLD202-T05")


def test_removed_and_reversed_access_worlds_change_evidence():
    reference = DataSources()
    removed = DataSources(fixture="counterfactual/removed-access")
    reversed_access = DataSources(fixture="counterfactual/reversed-access")

    reference_requests = reference.get_access_requests(task_id="EMP002-T05")
    removed_requests = removed.get_access_requests(task_id="EMP002-T05")
    reversed_requests = reversed_access.get_access_requests(task_id="EMP002-T05")

    assert [item["status"] for item in reference_requests] == ["Denied"]
    assert removed_requests == []
    assert [item["status"] for item in reversed_requests] == ["Approved"]


def test_blind_fixture_removes_original_identifiers_from_task_records():
    blind = DataSources(fixture="blind/renamed-case")
    rendered = json.dumps(blind.list_tasks()).lower()

    assert "emp002-t05" not in rendered
    assert "maya" not in rendered
    assert "bld202-t05" in rendered
