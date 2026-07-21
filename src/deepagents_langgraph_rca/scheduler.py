from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from .app import build_app, build_investigation_message, thread_config, write_case_artifact
from .config import AppConfig, load_config


def run_scheduled_investigation(
    *,
    as_of: str,
    fixture: str | None = None,
    task_id: str | None = None,
    thread_id: str | None = None,
    app=None,
    config: AppConfig | None = None,
):
    app_config = config or load_config(require_model=False)
    run_id = thread_id or f"scheduled-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}"
    agent = app or build_app(config=app_config)
    message = build_investigation_message(as_of=as_of, task_id=task_id, fixture=fixture)
    metadata = {
        "run_id": run_id,
        "as_of": as_of,
        "fixture": fixture,
        "task_id": task_id,
        "triggered_at": datetime.now().isoformat(timespec="seconds"),
        "trigger": "scheduler_adapter",
    }
    write_case_artifact(run_id, "scheduler_metadata.json", metadata, app_config)
    result = agent.invoke({"messages": [message]}, config=thread_config(run_id))
    return {"run_id": run_id, "metadata": metadata, "result": result}
