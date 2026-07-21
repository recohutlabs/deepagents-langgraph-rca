from __future__ import annotations

from pathlib import Path
from typing import Iterable

from deepagents import FilesystemPermission
from deepagents.middleware.subagents import SubAgent
from langchain_core.tools import BaseTool

from .config import AppConfig, load_config
from .schemas import SpecialistPacket
from .tools import build_tools


SUBAGENT_NAMES = (
    "task-timeline-analyst",
    "workload-priority-analyst",
    "dependency-access-analyst",
    "contract-policy-analyst",
    "evidence-privacy-reviewer",
)


def skill_dir(config: AppConfig | None = None) -> Path:
    app_config = config or load_config(require_model=False)
    return app_config.paths.root / "skills" / "task-delivery-rca"


def skill_runtime_path() -> str:
    return "/skills/task-delivery-rca"


def _tool_map(tools: Iterable[BaseTool]) -> dict[str, BaseTool]:
    return {item.name: item for item in tools}


def _select(tools: dict[str, BaseTool], names: list[str]) -> list[BaseTool]:
    return [tools[name] for name in names]


def _packet_instruction(name: str) -> str:
    return f"""
Return a structured SpecialistPacket.

Set specialist_name to "{name}".
Set case_id to the case identifier supplied by the coordinator.
Use observations for source-backed facts, objective_metrics for calculations, candidate_findings for possible explanations, rejected_hypotheses for tested alternatives, and unknowns for missing or contradictory evidence.
If your specialty is not relevant, set not_relevant to true and explain why in not_relevant_reason.
Use a concise evidence pass: include at most two observations, two objective metrics, two candidate findings, two rejected hypotheses, and three unknowns. Keep each field to one short sentence and cite only the minimum source references needed.
Do not invent task IDs or employee IDs. Do not repeatedly retry missing records; record missing evidence as an unknown.
Do not decide the final RCA. Do not assign blame. Do not include claims without evidence references.
"""


TASK_TIMELINE_PROMPT = f"""
You are the task timeline analyst for task-delivery RCA.

Reconstruct chronology from task fields, attendance, leave, access events, and task-state metrics. Focus on dates, status, recorded work, observed events, missing periods, and contradictions. You may identify timeline-related candidate explanations, but you must not decide the final RCA.
{_packet_instruction("task-timeline-analyst")}
"""


WORKLOAD_PRIORITY_PROMPT = f"""
You are the workload priority analyst for task-delivery RCA.

Compare estimated work, actual work, concurrent tasks, recorded hours, attendance, leave, and priority signals. Objective arithmetic is allowed. Do not automatically classify a busy week as overload. Distinguish concurrent work from evidence that work displaced the investigated task.
{_packet_instruction("workload-priority-analyst")}
"""


DEPENDENCY_ACCESS_PROMPT = f"""
You are the dependency access analyst for task-delivery RCA.

Inspect task systems, access events, access requests, approvals, denials, VPN-use records, data availability, and possible alternatives. Distinguish an observed denial or blocked event from proof that it caused the delivery issue.
{_packet_instruction("dependency-access-analyst")}
"""


CONTRACT_POLICY_PROMPT = f"""
You are the contract policy analyst for task-delivery RCA.

Compare requested work with documented responsibilities, assignment exceptions, access restrictions, and policy clauses. Quote or paraphrase only short relevant clauses with references. Do not name a replacement owner unless directly supported and necessary for the process recommendation.
{_packet_instruction("contract-policy-analyst")}
"""


EVIDENCE_PRIVACY_REVIEWER_PROMPT = f"""
You are the evidence privacy reviewer for task-delivery RCA.

Review specialist packets and source citations before final synthesis. Accept, downgrade, reject, or leave unknown each proposed finding. Remove unsupported, overstated, private, speculative, blaming, disciplinary, motivational, or health-detail claims. Separate accepted findings, contributing factors, rejected hypotheses, and unknowns.
{_packet_instruction("evidence-privacy-reviewer")}
"""


def build_subagents(
    tools: list[BaseTool] | None = None,
    config: AppConfig | None = None,
    permissions: list[FilesystemPermission] | None = None,
) -> list[SubAgent]:
    app_config = config or load_config(require_model=False)
    registry = _tool_map(tools or build_tools())
    skill_path = skill_runtime_path()

    return [
        {
            "name": "task-timeline-analyst",
            "description": "Reconstructs task chronology from task records, attendance, leave, access events, and task-state metrics.",
            "system_prompt": TASK_TIMELINE_PROMPT,
            "tools": _select(
                registry,
                [
                    "get_task",
                    "get_attendance",
                    "get_leave",
                    "get_access_events",
                    "summarize_task_state_history",
                    "calculate_days_overdue",
                    "calculate_date_overlap",
                ],
            ),
            "skills": [skill_path],
            "response_format": SpecialistPacket,
            **({"permissions": permissions} if permissions is not None else {}),
        },
        {
            "name": "workload-priority-analyst",
            "description": "Assesses recorded workload, concurrent tasks, attendance, leave, and priority signals without deciding the final RCA.",
            "system_prompt": WORKLOAD_PRIORITY_PROMPT,
            "tools": _select(
                registry,
                [
                    "get_employee",
                    "list_employee_tasks",
                    "get_attendance",
                    "get_leave",
                    "calculate_task_counts",
                    "calculate_recorded_hours",
                    "calculate_date_overlap",
                ],
            ),
            "skills": [skill_path],
            "response_format": SpecialistPacket,
            **({"permissions": permissions} if permissions is not None else {}),
        },
        {
            "name": "dependency-access-analyst",
            "description": "Examines systems, access events, access requests, approvals, denials, and VPN-use records.",
            "system_prompt": DEPENDENCY_ACCESS_PROMPT,
            "tools": _select(
                registry,
                [
                    "get_task",
                    "get_employee",
                    "get_access_events",
                    "get_access_requests",
                    "calculate_approval_presence",
                    "summarize_access_status",
                    "calculate_vpn_compliance_status",
                ],
            ),
            "skills": [skill_path],
            "response_format": SpecialistPacket,
            **({"permissions": permissions} if permissions is not None else {}),
        },
        {
            "name": "contract-policy-analyst",
            "description": "Reviews contract and policy evidence related to responsibilities, assignment exceptions, and access restrictions.",
            "system_prompt": CONTRACT_POLICY_PROMPT,
            "tools": _select(
                registry,
                [
                    "get_task",
                    "get_employee",
                    "read_contract",
                    "list_policies",
                    "read_policy",
                ],
            ),
            "skills": [skill_path],
            "response_format": SpecialistPacket,
            **({"permissions": permissions} if permissions is not None else {}),
        },
        {
            "name": "evidence-privacy-reviewer",
            "description": "Checks specialist findings against cited evidence and removes unsupported, speculative, private, or blaming claims.",
            "system_prompt": EVIDENCE_PRIVACY_REVIEWER_PROMPT,
            "tools": _select(
                registry,
                [
                    "get_task",
                    "get_employee",
                    "get_access_events",
                    "get_access_requests",
                    "read_contract",
                    "list_policies",
                    "read_policy",
                ],
            ),
            "skills": [skill_path],
            "response_format": SpecialistPacket,
            **({"permissions": permissions} if permissions is not None else {}),
        },
    ]


def build_dynamic_delegation_guidance() -> str:
    return """
Create an investigation plan before delegating.
Choose evidence specialists based on the case evidence needs.
The evidence privacy reviewer is mandatory after specialist packets exist and before final synthesis.
Across architecture tests, all five registered subagents must be exercised.
"""
