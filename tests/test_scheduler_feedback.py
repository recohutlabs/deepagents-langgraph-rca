import json
import shutil

from deepagents_langgraph_rca.app import run_workspace_dir
from deepagents_langgraph_rca.feedback import record_feedback
from deepagents_langgraph_rca.scheduler import run_scheduled_investigation


class FakeApp:
    def __init__(self):
        self.calls = []

    def invoke(self, payload, config):
        self.calls.append({"payload": payload, "config": config})
        return {"ok": True}


def test_scheduler_adapter_invokes_supplied_app_and_records_metadata():
    app = FakeApp()
    run_id = "scheduled-smoke"
    shutil.rmtree(run_workspace_dir(run_id), ignore_errors=True)

    result = run_scheduled_investigation(
        as_of="2026-07-17",
        fixture="reference",
        task_id="TASK-1",
        thread_id=run_id,
        app=app,
    )
    metadata = json.loads((run_workspace_dir(run_id) / "scheduler_metadata.json").read_text())

    assert result["run_id"] == run_id
    assert metadata["trigger"] == "scheduler_adapter"
    assert app.calls[0]["config"]["configurable"]["thread_id"] == run_id
    assert "as_of=2026-07-17" in app.calls[0]["payload"]["messages"][0].content
    shutil.rmtree(run_workspace_dir(run_id), ignore_errors=True)


def test_feedback_record_is_persisted_without_skill_update():
    run_id = "feedback-smoke"
    shutil.rmtree(run_workspace_dir(run_id), ignore_errors=True)

    record = record_feedback(
        run_id=run_id,
        review_decision="partially_correct",
        unsupported_claims=["Claim lacked a citation."],
        missed_evidence=["A policy clause was not checked."],
        suggested_skill_change="Require stronger citation review.",
        approved_for_skill_update=False,
    )
    stored = json.loads((run_workspace_dir(run_id) / "feedback_record.json").read_text())

    assert record.approved_for_skill_update is False
    assert stored["suggested_skill_change"] == "Require stronger citation review."
    assert stored["approved_for_skill_update"] is False
    shutil.rmtree(run_workspace_dir(run_id), ignore_errors=True)
