from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from datetime import date
from pathlib import Path
from typing import Any

import requests
from deepagents import FilesystemPermission, create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_core.tools import BaseTool, tool
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage

from .checkpoints import build_checkpointer
from .config import AppConfig, build_model, load_config
from .prompts import build_dynamic_delegation_guidance, build_subagents, skill_runtime_path
from .schemas import RCAReport
from .sources import DataSources
from .tools import build_tools


def default_as_of_date() -> str:
    """Return the system-date default used when a user omits as_of."""
    return date.today().isoformat()


COORDINATOR_SYSTEM_PROMPT = f"""
You are the RCA coordinator for a task-delivery investigation.

Use the task-delivery RCA skill as the evidence and privacy filter. Work from source tools and objective metrics. Do not use legacy reports, benchmark answers, copied conclusions, hidden case rules, or fixed task counts.

Input handling:
- If the user provides an explicit as_of date, use it.
- If the user omits as_of, default as_of to the current system date: {default_as_of_date()}.
- The user may provide one task_id for a controlled single-case investigation.
- If no task_id is supplied, retrieve task records and identify candidates from raw due dates, task statuses, and optional objective date metrics.
- Treat Done and Cancelled as terminal task statuses.

Execution flow:
1. Retrieve relevant raw facts with tools.
2. Write a visible investigation plan.
3. Choose evidence specialists dynamically based on the evidence needed.
4. Delegate to relevant evidence specialists.
5. Run the evidence privacy reviewer after specialist packets exist.
6. Produce final synthesis only after reviewer output.

Bounded execution:
- For a selected task_id, use that exact task_id. Do not invent adjacent task IDs.
- Prefer one concise investigation round: gather the task and employee records, use objective metrics when useful, delegate to the most relevant evidence specialists, run the reviewer, then synthesize.
- Do not repeatedly retry missing records. If a tool returns an error or evidence is unavailable, record the gap as an unknown and continue.
- If the evidence is too weak for one primary cause, return insufficient evidence rather than continuing to search indefinitely.
- Keep the final answer compact enough to fit the structured RCA schema.

{build_dynamic_delegation_guidance()}

Final synthesis:
- Return primary cause or insufficient evidence.
- Return contributing factors, rejected causes, unknowns, and recommended next action.
- Every accepted causal claim must cite evidence.
- Use process-focused language and avoid employee blame.
"""


def build_investigation_message(
    *,
    as_of: str | None = None,
    task_id: str | None = None,
    fixture: str | None = None,
    force_all_specialists: bool = False,
) -> HumanMessage:
    effective_as_of = as_of or default_as_of_date()
    scope = (
        f"Investigate task_id={task_id}."
        if task_id
        else "Discover candidate tasks from raw task records before choosing a case."
    )
    fixture_text = f"Use configured fixture={fixture}." if fixture else "Use the configured data sources."
    coverage_text = (
        "For this architecture-coverage run, deliberately invoke all four evidence specialists before the reviewer."
        if force_all_specialists
        else "Delegate only to specialists that the investigation plan says are relevant, then run the reviewer."
    )
    return HumanMessage(
        content=(
            f"as_of={effective_as_of}\n"
            f"{fixture_text}\n"
            f"{scope}\n"
            f"{coverage_text}\n"
            "Use tools for evidence. Do not assume expected cases or expected causes."
        )
    )


def build_app(
    *,
    config: AppConfig | None = None,
    model: BaseChatModel | None = None,
    sources: DataSources | None = None,
    checkpointer: Any | None = None,
    backend: Any | None = None,
    permissions: list[FilesystemPermission] | None = None,
    response_format: Any = RCAReport,
    debug: bool = False,
):
    app_config = config or load_config(require_model=False)
    app_sources = sources or DataSources(app_config)
    retrieval_tools = build_tools(app_sources)
    fs_permissions = permissions if permissions is not None else build_filesystem_permissions()
    subagents = build_subagents(retrieval_tools, app_config, permissions=fs_permissions)
    tools = [*retrieval_tools, *build_channel_tools(app_config)]
    app_model = model or build_model(load_config(require_model=True))
    saver = checkpointer if checkpointer is not None else build_checkpointer(app_config)
    fs_backend = backend if backend is not None else build_filesystem_backend(app_config)

    return create_deep_agent(
        model=app_model,
        tools=tools,
        system_prompt=COORDINATOR_SYSTEM_PROMPT,
        subagents=subagents,
        skills=[skill_runtime_path()],
        backend=fs_backend,
        permissions=fs_permissions,
        interrupt_on=build_interrupt_on(),
        checkpointer=saver,
        response_format=response_format,
        debug=debug,
    )


def thread_config(thread_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread_id}}


def invoke_app(app: Any, messages: Iterable[HumanMessage], *, thread_id: str) -> Any:
    return app.invoke({"messages": list(messages)}, config=thread_config(thread_id))


def stream_app_events(app: Any, messages: Iterable[HumanMessage], *, thread_id: str) -> Iterator[dict[str, Any]]:
    yield from app.stream(
        {"messages": list(messages)},
        config=thread_config(thread_id),
        stream_mode="updates",
    )


def summarize_event(event: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {"keys": sorted(event)}
    rendered = repr(event)
    for marker in ("tool", "task", "interrupt", "structured_response"):
        if marker in rendered:
            summary[marker] = True
    return summary


def build_filesystem_backend(config: AppConfig | None = None) -> FilesystemBackend:
    app_config = config or load_config(require_model=False)
    app_config.paths.workspace_root.mkdir(parents=True, exist_ok=True)
    return FilesystemBackend(root_dir=app_config.paths.root, virtual_mode=True)


def build_filesystem_permissions() -> list[FilesystemPermission]:
    return [
        FilesystemPermission(operations=["read", "write"], paths=["/.env"], mode="deny"),
        FilesystemPermission(operations=["read", "write"], paths=["/legacy/**"], mode="deny"),
        FilesystemPermission(operations=["read", "write"], paths=["/data/**"], mode="deny"),
        FilesystemPermission(operations=["read", "write"], paths=["/docs/**"], mode="deny"),
        FilesystemPermission(operations=["read", "write"], paths=["/tests/**"], mode="deny"),
        FilesystemPermission(operations=["read"], paths=["/skills/**"], mode="allow"),
        FilesystemPermission(operations=["write"], paths=["/skills/**"], mode="deny"),
        FilesystemPermission(operations=["read", "write"], paths=["/runs/**"], mode="allow"),
        FilesystemPermission(operations=["read", "write"], paths=["/**"], mode="deny"),
    ]


def build_interrupt_on() -> dict[str, bool]:
    return {"send_channel_update": True}


def build_channel_tools(config: AppConfig | None = None) -> list[BaseTool]:
    app_config = config or load_config(require_model=False)

    @tool
    def send_channel_update(run_id: str, channel: str, message: str) -> str:
        """Send an approved RCA update through Slack chat.postMessage."""
        app_config.channel.require_publish_config()
        publish_path = run_workspace_dir(run_id, app_config) / "publish_result.json"
        if publish_path.exists():
            return json.dumps(
                {
                    "status": "duplicate_prevented",
                    "sent": False,
                    "run_id": run_id,
                    "channel": channel,
                },
                indent=2,
                sort_keys=True,
            )
        payload = {"channel": channel or app_config.channel.channel, "text": message}
        response = requests.post(
            app_config.channel.post_message_url,
            json=payload,
            headers={
                "Authorization": f"Bearer {app_config.channel.bot_token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            timeout=20,
        )
        response_payload = response.json()
        if not response_payload.get("ok"):
            error = response_payload.get("error", "unknown_error")
            raise RuntimeError(f"Slack chat.postMessage failed: {error}")
        result = {
            "status": "sent",
            "sent": True,
            "run_id": run_id,
            "channel": payload["channel"],
            "http_status": response.status_code,
            "slack_ok": response_payload["ok"],
            "slack_channel": response_payload.get("channel"),
            "slack_ts": response_payload.get("ts"),
        }
        write_case_artifact(run_id, "publish_result.json", result, app_config)
        return json.dumps(result, indent=2, sort_keys=True)

    return [send_channel_update]


def apply_channel_decision(
    *,
    run_id: str,
    decision: str,
    proposed_message: str,
    channel: str | None = None,
    edited_message: str | None = None,
    config: AppConfig | None = None,
) -> dict[str, Any]:
    app_config = config or load_config(require_model=False)
    normalized = decision.strip().lower()
    if normalized not in {"approve", "edit", "reject"}:
        raise ValueError("decision must be approve, edit, or reject")
    message = edited_message if normalized == "edit" else proposed_message
    record = {
        "run_id": run_id,
        "decision": normalized,
        "channel": channel or app_config.channel.channel,
        "proposed_message": proposed_message,
        "final_message": message if normalized != "reject" else None,
    }
    write_case_artifact(run_id, "approval_record.json", record, app_config)
    if normalized == "reject":
        return {"status": "rejected", "sent": False, "approval": record}
    tool_result = build_channel_tools(app_config)[0].invoke(
        {
            "run_id": run_id,
            "channel": channel or app_config.channel.channel,
            "message": message or "",
        }
    )
    return {"status": "approved" if normalized == "approve" else "edited", "publish": json.loads(tool_result)}


def run_workspace_dir(run_id: str, config: AppConfig | None = None) -> Path:
    if "/" in run_id or ".." in run_id:
        raise ValueError("run_id must be a simple directory name")
    app_config = config or load_config(require_model=False)
    return app_config.paths.workspace_root / run_id


def ensure_run_workspace(run_id: str, config: AppConfig | None = None) -> Path:
    path = run_workspace_dir(run_id, config)
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_case_artifact(
    run_id: str,
    filename: str,
    content: str | dict[str, Any] | list[Any],
    config: AppConfig | None = None,
) -> Path:
    if "/" in filename or filename.startswith("."):
        raise ValueError("artifact filename must be a simple visible file name")
    directory = ensure_run_workspace(run_id, config)
    path = directory / filename
    if isinstance(content, str):
        rendered = content
    else:
        rendered = json.dumps(content, indent=2, sort_keys=True)
    path.write_text(rendered)
    return path
