from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import BaseTool, tool

from .sources import DataSources, SourceNotFoundError


def _json(data: Any) -> str:
    def default(value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return value.model_dump()
        if hasattr(value, "to_dict"):
            return value.to_dict()
        return str(value)

    return json.dumps(data, indent=2, sort_keys=True, default=default)


def _bounded(value: Any, *, limit: int = 20) -> Any:
    if isinstance(value, list):
        return {
            "items": value[:limit],
            "row_count": len(value),
            "truncated": len(value) > limit,
        }
    return value


def _safe_json(callback) -> str:
    try:
        return _json(callback())
    except SourceNotFoundError as exc:
        return _json({"error": "SourceNotFoundError", "message": str(exc)})


def build_tools(sources: DataSources | None = None) -> list[BaseTool]:
    source = sources or DataSources()

    @tool
    def list_tasks(
        employee_id: str = "",
        status: str = "",
        due_before: str = "",
        due_after: str = "",
    ) -> str:
        """List task records with optional neutral filters for employee, status, and due-date range."""
        return _safe_json(
            lambda: _bounded(
                source.list_tasks(
                    employee_id=employee_id or None,
                    status=status or None,
                    due_before=due_before or None,
                    due_after=due_after or None,
                )
            )
        )

    @tool
    def get_task(task_id: str) -> str:
        """Return one task record and its source references."""
        return _safe_json(lambda: source.get_task(task_id))

    @tool
    def list_employee_tasks(employee_id: str) -> str:
        """Return task records for one employee with source references."""
        return _safe_json(lambda: _bounded(source.list_employee_tasks(employee_id)))

    @tool
    def get_employee(employee_id: str) -> str:
        """Return one employee record with source references."""
        return _safe_json(lambda: source.get_employee(employee_id))

    @tool
    def get_attendance(employee_id: str, start_date: str = "", end_date: str = "") -> str:
        """Return attendance records for one employee and optional date range."""
        return _safe_json(
            lambda: _bounded(source.get_attendance(employee_id, start_date or None, end_date or None))
        )

    @tool
    def get_leave(employee_id: str, start_date: str = "", end_date: str = "") -> str:
        """Return leave records for one employee and optional date range."""
        return _safe_json(lambda: _bounded(source.get_leave(employee_id, start_date or None, end_date or None)))

    @tool
    def get_access_events(employee_id: str, start_date: str = "", end_date: str = "") -> str:
        """Return remote-access event records for one employee and optional date range."""
        return _safe_json(
            lambda: _bounded(source.get_remote_access(employee_id, start_date or None, end_date or None))
        )

    @tool
    def get_access_requests(
        employee_id: str = "",
        task_id: str = "",
        start_date: str = "",
        end_date: str = "",
    ) -> str:
        """Return access request records with optional employee, task, and date filters."""
        return _safe_json(
            lambda: _bounded(
                source.get_access_requests(
                    employee_id=employee_id or None,
                    task_id=task_id or None,
                    start_date=start_date or None,
                    end_date=end_date or None,
                )
            )
        )

    @tool
    def read_contract(employee_id: str) -> str:
        """Read the contract text for one employee by using the recorded agreement file."""
        return _safe_json(lambda: source.read_contract(employee_id))

    @tool
    def list_policies() -> str:
        """List available policy documents with source references."""
        return _safe_json(lambda: _bounded(source.list_policies()))

    @tool
    def read_policy(filename: str) -> str:
        """Read one policy document by filename."""
        return _safe_json(lambda: source.read_policy(filename))

    @tool
    def calculate_days_overdue(task_id: str, as_of: str) -> str:
        """Calculate days between a task due date and an as-of date, returning inputs and evidence."""
        return _safe_json(lambda: source.calculate_days_overdue(task_id, as_of))

    @tool
    def calculate_date_overlap(employee_id: str, start_date: str, end_date: str) -> str:
        """Calculate leave overlap days for an employee and date range, returning inputs and evidence."""
        return _safe_json(lambda: source.calculate_date_overlap(employee_id, start_date, end_date))

    @tool
    def calculate_task_counts(employee_id: str) -> str:
        """Calculate task counts by status for one employee, returning inputs and evidence."""
        return _safe_json(lambda: source.calculate_task_counts(employee_id))

    @tool
    def calculate_recorded_hours(employee_id: str) -> str:
        """Calculate recorded task and attendance hours for one employee, returning inputs and evidence."""
        return _safe_json(lambda: source.calculate_recorded_hours(employee_id))

    @tool
    def calculate_approval_presence(task_id: str) -> str:
        """Calculate whether any recorded access request for a task is approved, returning inputs and evidence."""
        return _safe_json(lambda: source.calculate_approval_presence(task_id))

    @tool
    def summarize_access_status(employee_id: str, task_id: str = "") -> str:
        """Summarize recorded access-request statuses and remote-access event reasons with evidence."""
        return _safe_json(lambda: source.summarize_access_status(employee_id, task_id or None))

    @tool
    def calculate_vpn_compliance_status(employee_id: str) -> str:
        """Calculate whether recorded VPN-required access events used VPN, returning inputs and evidence."""
        return _safe_json(lambda: source.calculate_vpn_compliance_status(employee_id))

    @tool
    def summarize_task_state_history(task_id: str) -> str:
        """Summarize recorded task status fields from available sources with evidence."""
        return _safe_json(lambda: source.summarize_task_state_history(task_id))

    return [
        list_tasks,
        get_task,
        list_employee_tasks,
        get_employee,
        get_attendance,
        get_leave,
        get_access_events,
        get_access_requests,
        read_contract,
        list_policies,
        read_policy,
        calculate_days_overdue,
        calculate_date_overlap,
        calculate_task_counts,
        calculate_recorded_hours,
        calculate_approval_presence,
        summarize_access_status,
        calculate_vpn_compliance_status,
        summarize_task_state_history,
    ]
