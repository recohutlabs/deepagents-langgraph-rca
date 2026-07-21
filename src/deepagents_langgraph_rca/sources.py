from __future__ import annotations

import json
import sqlite3
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterator

from .config import AppConfig, ConfigError, load_config
from .schemas import EvidenceReference, ObjectiveMetric


TERMINAL_STATUSES = {"Done", "Cancelled"}


class SourceNotFoundError(LookupError):
    """Raised when requested source evidence is missing."""


@dataclass(frozen=True)
class SourceRecord:
    data: dict[str, Any]
    evidence: list[EvidenceReference]

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.data,
            "evidence": [item.model_dump() for item in self.evidence],
        }


class DataSources:
    def __init__(
        self,
        config: AppConfig | None = None,
        *,
        data_dir: Path | None = None,
        fixture: str | None = None,
    ) -> None:
        self.config = config or load_config(require_model=False)
        self.data_dir = self._resolve_data_dir(data_dir, fixture)
        self.task_dir = self.data_dir / "tasks"
        self.contracts_dir = self.data_dir / "contracts"
        self.policies_dir = self.data_dir / "policies"
        self.db_path = self.data_dir / "operations" / "employee_operations.sqlite"

    def _resolve_data_dir(self, data_dir: Path | None, fixture: str | None) -> Path:
        if data_dir is not None:
            return data_dir.resolve()
        if fixture in (None, "", "reference"):
            return self.config.paths.data_dir
        return (self.config.paths.root / "data" / "fixtures" / fixture).resolve()

    @contextmanager
    def connect_sqlite(self) -> Iterator[sqlite3.Connection]:
        if not self.db_path.exists():
            raise SourceNotFoundError(f"SQLite database not found: {self.db_path}")
        uri = f"file:{self.db_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def evidence(self, source_type: str, source_location: str | Path, record_id: str | None = None) -> EvidenceReference:
        return EvidenceReference(
            source_type=source_type,
            source_location=self._display_path(source_location),
            record_id=record_id,
        )

    def _display_path(self, path: str | Path) -> str:
        value = Path(path) if not isinstance(path, Path) else path
        if not value.is_absolute():
            return str(value)
        try:
            return str(value.relative_to(self.config.paths.root))
        except ValueError:
            return str(value)

    def _task_files(self) -> list[Path]:
        if not self.task_dir.exists():
            raise SourceNotFoundError(f"Task directory not found: {self.task_dir}")
        return sorted(self.task_dir.glob("*.json"))

    def _load_task_records(self) -> list[SourceRecord]:
        records: list[SourceRecord] = []
        for path in self._task_files():
            payload = json.loads(path.read_text())
            for task in payload.get("tasks", []):
                task_id = task["task_id"]
                data = {
                    **task,
                    "employee_id": payload.get("employee_id"),
                    "employee_name": payload.get("employee_name"),
                    "role": payload.get("role"),
                    "manager": payload.get("manager"),
                    "week_start": payload.get("week_start"),
                    "standard_weekly_hours": payload.get("standard_weekly_hours"),
                }
                if payload.get("effective_capacity_note"):
                    data["effective_capacity_note"] = payload["effective_capacity_note"]
                records.append(
                    SourceRecord(
                        data=data,
                        evidence=[self.evidence("task_json", path, task_id)],
                    )
                )
        return records

    def list_tasks(
        self,
        *,
        employee_id: str | None = None,
        status: str | None = None,
        due_before: str | None = None,
        due_after: str | None = None,
    ) -> list[dict[str, Any]]:
        rows = self._load_task_records()
        result: list[dict[str, Any]] = []
        for record in rows:
            task = record.data
            if employee_id and task.get("employee_id") != employee_id:
                continue
            if status and task.get("status") != status:
                continue
            if due_before and task.get("due_date", "") >= due_before:
                continue
            if due_after and task.get("due_date", "") <= due_after:
                continue
            result.append(record.to_dict())
        return result

    def get_task(self, task_id: str) -> dict[str, Any]:
        for record in self._load_task_records():
            if record.data["task_id"] == task_id:
                sqlite_row = self._get_sqlite_task(task_id)
                data = record.to_dict()
                if sqlite_row is not None:
                    data["sqlite_task"] = sqlite_row.to_dict()
                return data
        raise SourceNotFoundError(f"Task not found: {task_id}")

    def list_employee_tasks(self, employee_id: str) -> list[dict[str, Any]]:
        tasks = self.list_tasks(employee_id=employee_id)
        if not tasks:
            raise SourceNotFoundError(f"No tasks found for employee: {employee_id}")
        return tasks

    def _get_sqlite_task(self, task_id: str) -> SourceRecord | None:
        with self.connect_sqlite() as conn:
            row = conn.execute(
                "SELECT id, emp_id, name, status, notes FROM task WHERE id = ?",
                (task_id,),
            ).fetchone()
        if row is None:
            return None
        return SourceRecord(
            data=dict(row),
            evidence=[self.evidence("sqlite", "data/operations/employee_operations.sqlite:task", task_id)],
        )

    def get_employee(self, employee_id: str) -> dict[str, Any]:
        with self.connect_sqlite() as conn:
            row = conn.execute(
                """
                SELECT emp_id, full_name, role, manager, office_location,
                       agreement_file, start_date, remote_access, notes
                FROM employees
                WHERE emp_id = ?
                """,
                (employee_id,),
            ).fetchone()
        if row is None:
            raise SourceNotFoundError(f"Employee not found: {employee_id}")
        return SourceRecord(
            data=dict(row),
            evidence=[self.evidence("sqlite", "data/operations/employee_operations.sqlite:employees", employee_id)],
        ).to_dict()

    def _date_range_query(
        self,
        table: str,
        employee_column: str,
        date_column: str,
        employee_id: str,
        start_date: str | None,
        end_date: str | None,
    ) -> list[sqlite3.Row]:
        clauses = [f"{employee_column} = ?"]
        params: list[Any] = [employee_id]
        if start_date:
            clauses.append(f"{date_column} >= ?")
            params.append(start_date)
        if end_date:
            clauses.append(f"{date_column} <= ?")
            params.append(end_date)
        query = f"SELECT * FROM {table} WHERE {' AND '.join(clauses)} ORDER BY {date_column}"
        with self.connect_sqlite() as conn:
            return list(conn.execute(query, params))

    def get_attendance(
        self,
        employee_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        rows = self._date_range_query(
            "attendance_records", "employee_id", "work_date", employee_id, start_date, end_date
        )
        return [
            SourceRecord(
                data=dict(row),
                evidence=[
                    self.evidence(
                        "sqlite",
                        "data/operations/employee_operations.sqlite:attendance_records",
                        str(row["id"]),
                    )
                ],
            ).to_dict()
            for row in rows
        ]

    def get_leave(
        self,
        employee_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        rows = self._date_range_query(
            "leave_records", "emp_id", "start_date", employee_id, start_date, end_date
        )
        return [
            SourceRecord(
                data=dict(row),
                evidence=[
                    self.evidence(
                        "sqlite",
                        "data/operations/employee_operations.sqlite:leave_records",
                        str(row["leave_id"]),
                    )
                ],
            ).to_dict()
            for row in rows
        ]

    def get_remote_access(
        self,
        employee_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        rows = self._date_range_query(
            "remote_access", "emp_id", "event_time", employee_id, start_date, end_date
        )
        return [
            SourceRecord(
                data=dict(row),
                evidence=[
                    self.evidence(
                        "sqlite",
                        "data/operations/employee_operations.sqlite:remote_access",
                        str(row["event_id"]),
                    )
                ],
            ).to_dict()
            for row in rows
        ]

    def get_access_requests(
        self,
        *,
        employee_id: str | None = None,
        task_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if employee_id:
            clauses.append("emp_id = ?")
            params.append(employee_id)
        if task_id:
            clauses.append("task_id = ?")
            params.append(task_id)
        if start_date:
            clauses.append("requested_at >= ?")
            params.append(start_date)
        if end_date:
            clauses.append("requested_at <= ?")
            params.append(end_date)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self.connect_sqlite() as conn:
            rows = list(
                conn.execute(
                    f"SELECT * FROM access_request {where} ORDER BY requested_at, id",
                    params,
                )
            )
        return [
            SourceRecord(
                data=dict(row),
                evidence=[
                    self.evidence(
                        "sqlite",
                        "data/operations/employee_operations.sqlite:access_request",
                        row["id"],
                    )
                ],
            ).to_dict()
            for row in rows
        ]

    def read_contract(self, employee_id: str) -> dict[str, Any]:
        employee = self.get_employee(employee_id)
        filename = employee["agreement_file"]
        path = self.contracts_dir / filename
        if not path.exists():
            raise SourceNotFoundError(f"Contract not found for {employee_id}: {filename}")
        return SourceRecord(
            data={"employee_id": employee_id, "filename": filename, "text": path.read_text()},
            evidence=[self.evidence("contract", path, filename)],
        ).to_dict()

    def list_policies(self) -> list[dict[str, Any]]:
        if not self.policies_dir.exists():
            raise SourceNotFoundError(f"Policy directory not found: {self.policies_dir}")
        return [
            SourceRecord(
                data={"filename": path.name},
                evidence=[self.evidence("policy", path, path.name)],
            ).to_dict()
            for path in sorted(self.policies_dir.glob("*.md"))
        ]

    def read_policy(self, filename: str) -> dict[str, Any]:
        path = (self.policies_dir / filename).resolve()
        if path.parent != self.policies_dir.resolve() or not path.exists():
            raise SourceNotFoundError(f"Policy not found: {filename}")
        return SourceRecord(
            data={"filename": path.name, "text": path.read_text()},
            evidence=[self.evidence("policy", path, path.name)],
        ).to_dict()

    def calculate_days_overdue(self, task_id: str, as_of: str) -> ObjectiveMetric:
        task = self.get_task(task_id)
        due_date = date.fromisoformat(task["due_date"])
        as_of_date = date.fromisoformat(as_of)
        value = max((as_of_date - due_date).days, 0)
        return ObjectiveMetric(
            metric="days_overdue",
            value=value,
            inputs={"task_id": task_id, "due_date": task["due_date"], "as_of": as_of},
            evidence=[EvidenceReference.model_validate(item) for item in task["evidence"]],
            calculated_at=datetime.now().isoformat(timespec="seconds"),
        )

    def calculate_date_overlap(self, employee_id: str, start_date: str, end_date: str) -> ObjectiveMetric:
        leave_rows = self.get_leave(employee_id)
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        overlap_days = 0
        refs: list[EvidenceReference] = [
            self.evidence("sqlite", "data/operations/employee_operations.sqlite:leave_records", employee_id)
        ]
        for row in leave_rows:
            leave_start = date.fromisoformat(row["start_date"])
            leave_end = date.fromisoformat(row["end_date"])
            latest_start = max(start, leave_start)
            earliest_end = min(end, leave_end)
            if latest_start <= earliest_end:
                overlap_days += (earliest_end - latest_start).days + 1
                refs.extend(EvidenceReference.model_validate(item) for item in row["evidence"])
        return ObjectiveMetric(
            metric="leave_overlap_days",
            value=overlap_days,
            inputs={"employee_id": employee_id, "start_date": start_date, "end_date": end_date},
            evidence=refs,
            calculated_at=datetime.now().isoformat(timespec="seconds"),
        )

    def calculate_task_counts(self, employee_id: str) -> ObjectiveMetric:
        tasks = self.list_employee_tasks(employee_id)
        counts = Counter(task["status"] for task in tasks)
        refs = [EvidenceReference.model_validate(ref) for task in tasks for ref in task["evidence"]]
        return ObjectiveMetric(
            metric="task_counts_by_status",
            value=json.dumps(dict(sorted(counts.items())), sort_keys=True),
            inputs={"employee_id": employee_id, "task_ids": [task["task_id"] for task in tasks]},
            evidence=refs,
            calculated_at=datetime.now().isoformat(timespec="seconds"),
        )

    def calculate_recorded_hours(self, employee_id: str) -> ObjectiveMetric:
        tasks = self.list_employee_tasks(employee_id)
        attendance = self.get_attendance(employee_id)
        task_hours = sum(float(task.get("actual_hours") or 0) for task in tasks)
        attendance_hours = sum(float(row.get("recorded_hours") or 0) for row in attendance)
        refs = [EvidenceReference.model_validate(ref) for task in tasks for ref in task["evidence"]]
        refs.extend(EvidenceReference.model_validate(ref) for row in attendance for ref in row["evidence"])
        return ObjectiveMetric(
            metric="recorded_hours",
            value=json.dumps(
                {"task_actual_hours": task_hours, "attendance_recorded_hours": attendance_hours},
                sort_keys=True,
            ),
            inputs={"employee_id": employee_id},
            evidence=refs,
            calculated_at=datetime.now().isoformat(timespec="seconds"),
        )

    def calculate_approval_presence(self, task_id: str) -> ObjectiveMetric:
        requests = self.get_access_requests(task_id=task_id)
        statuses = [request["status"] for request in requests]
        refs = [
            EvidenceReference.model_validate(ref)
            for request in requests
            for ref in request["evidence"]
        ] or [self.evidence("sqlite", "data/operations/employee_operations.sqlite:access_request", task_id)]
        return ObjectiveMetric(
            metric="approval_presence",
            value=any(status.lower() == "approved" for status in statuses),
            inputs={"task_id": task_id, "request_statuses": statuses},
            evidence=refs,
            calculated_at=datetime.now().isoformat(timespec="seconds"),
        )

    def summarize_access_status(self, employee_id: str, task_id: str | None = None) -> ObjectiveMetric:
        requests = self.get_access_requests(employee_id=employee_id, task_id=task_id)
        events = self.get_remote_access(employee_id)
        refs = [
            EvidenceReference.model_validate(ref)
            for row in [*requests, *events]
            for ref in row["evidence"]
        ] or [self.evidence("sqlite", "data/operations/employee_operations.sqlite:remote_access", employee_id)]
        return ObjectiveMetric(
            metric="access_status_summary",
            value=json.dumps(
                {
                    "request_statuses": [request["status"] for request in requests],
                    "event_reasons": [event["reason"] for event in events],
                },
                sort_keys=True,
            ),
            inputs={"employee_id": employee_id, "task_id": task_id},
            evidence=refs,
            calculated_at=datetime.now().isoformat(timespec="seconds"),
        )

    def calculate_vpn_compliance_status(self, employee_id: str) -> ObjectiveMetric:
        events = self.get_remote_access(employee_id)
        required_events = [event for event in events if event["vpn_required"]]
        value = all(bool(event["vpn_used"]) for event in required_events)
        refs = [
            EvidenceReference.model_validate(ref)
            for event in events
            for ref in event["evidence"]
        ] or [self.evidence("sqlite", "data/operations/employee_operations.sqlite:remote_access", employee_id)]
        return ObjectiveMetric(
            metric="vpn_compliance_status",
            value=value,
            inputs={
                "employee_id": employee_id,
                "required_event_ids": [event["event_id"] for event in required_events],
            },
            evidence=refs,
            calculated_at=datetime.now().isoformat(timespec="seconds"),
        )

    def summarize_task_state_history(self, task_id: str) -> ObjectiveMetric:
        task = self.get_task(task_id)
        refs = [EvidenceReference.model_validate(ref) for ref in task["evidence"]]
        sqlite_refs = task.get("sqlite_task", {}).get("evidence", [])
        refs.extend(EvidenceReference.model_validate(ref) for ref in sqlite_refs)
        return ObjectiveMetric(
            metric="task_state_history",
            value=json.dumps(
                {
                    "json_status": task["status"],
                    "sqlite_status": task.get("sqlite_task", {}).get("status"),
                    "due_date": task.get("due_date"),
                    "completed_date": task.get("completed_date"),
                },
                sort_keys=True,
            ),
            inputs={"task_id": task_id},
            evidence=refs,
            calculated_at=datetime.now().isoformat(timespec="seconds"),
        )
