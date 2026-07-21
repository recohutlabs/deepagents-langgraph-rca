import sqlite3

import pytest

from deepagents_langgraph_rca.schemas import ObjectiveMetric
from deepagents_langgraph_rca.sources import DataSources, SourceNotFoundError


def test_sqlite_connection_is_read_only():
    sources = DataSources()

    with sources.connect_sqlite() as conn:
        with pytest.raises(sqlite3.OperationalError):
            conn.execute(
                "UPDATE task SET status = ? WHERE id = ?",
                ("Done", "EMP001-T05"),
            )


def test_task_retrieval_returns_neutral_data_with_provenance():
    task = DataSources().get_task("EMP002-T05")

    assert task["task_id"] == "EMP002-T05"
    assert task["status"] == "Blocked"
    assert task["evidence"][0]["source_type"] == "task_json"
    rendered = str(task).lower()
    assert "primary cause" not in rendered
    assert "access exception required" not in rendered


def test_access_request_retrieval_does_not_label_cause():
    requests = DataSources().get_access_requests(task_id="EMP002-T05")

    assert [request["id"] for request in requests] == ["AR-001"]
    rendered = str(requests).lower()
    assert "denied" in rendered
    assert "primary cause" not in rendered


def test_contract_read_returns_source_text_without_adapter_conclusion():
    contract = DataSources().read_contract("EMP001")

    assert contract["filename"] == "employee-agreement-aarav-mehta.md"
    assert "Position and Responsibilities" in contract["text"]
    rendered = str(contract).lower()
    assert "recommended owner" not in rendered
    assert "ownership mismatch" not in rendered


def test_policy_listing_and_reading():
    sources = DataSources()
    policies = sources.list_policies()

    assert {policy["filename"] for policy in policies} == {
        "information-security-policy.md",
        "leave-policy.md",
        "remote-security-policy.md",
        "working-hours-policy.md",
    }
    remote_policy = sources.read_policy("remote-security-policy.md")
    assert "Access to production servers and databases" in remote_policy["text"]


def test_objective_calculations_include_inputs_and_evidence():
    sources = DataSources()
    metrics = [
        sources.calculate_days_overdue("EMP001-T05", "2026-07-17"),
        sources.calculate_date_overlap("EMP002", "2026-07-13", "2026-07-17"),
        sources.calculate_task_counts("EMP002"),
        sources.calculate_recorded_hours("EMP001"),
        sources.calculate_approval_presence("EMP002-T05"),
        sources.summarize_access_status("EMP002", "EMP002-T05"),
        sources.calculate_vpn_compliance_status("EMP002"),
        sources.summarize_task_state_history("EMP001-T05"),
    ]

    assert all(isinstance(metric, ObjectiveMetric) for metric in metrics)
    assert all(metric.inputs for metric in metrics)
    assert all(metric.evidence for metric in metrics)
    assert metrics[0].value == 1
    assert "primary" not in " ".join(metric.metric for metric in metrics)


def test_missing_records_fail_clearly():
    with pytest.raises(SourceNotFoundError):
        DataSources().get_employee("missing")
