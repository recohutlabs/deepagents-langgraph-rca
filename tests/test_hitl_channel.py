import json
import os
import shutil
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from deepagents_langgraph_rca.app import (
    apply_channel_decision,
    build_channel_tools,
    build_interrupt_on,
    run_workspace_dir,
)
from deepagents_langgraph_rca.config import load_config


def config_with_bot_token(token: str = "xoxb-test-token"):
    config = load_config(require_model=False)
    return replace(
        config,
        channel=replace(
            config.channel,
            bot_token=token,
            post_message_url="https://slack.test/api/chat.postMessage",
        ),
    )


def test_interrupt_on_protects_channel_tool():
    assert build_interrupt_on() == {"send_channel_update": True}


def test_missing_channel_config_fails_only_at_publish_time():
    tool = build_channel_tools(config_with_bot_token(token=""))[0]

    with pytest.raises(Exception, match="SLACK_BOT_TOKEN"):
        tool.invoke({"run_id": "missing-channel", "channel": "#demo", "message": "hello"})


def test_approved_publish_sends_exact_message_once(monkeypatch):
    calls = []

    class Response:
        status_code = 200

        def json(self):
            return {"ok": True, "channel": "C123", "ts": "123.456"}

    def fake_post(url, json, headers, timeout):
        calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        return Response()

    monkeypatch.setattr("deepagents_langgraph_rca.app.requests.post", fake_post)
    run_id = "channel-approve-smoke"
    shutil.rmtree(run_workspace_dir(run_id), ignore_errors=True)
    config = config_with_bot_token()

    result = apply_channel_decision(
        run_id=run_id,
        decision="approve",
        proposed_message="approved text",
        config=config,
    )
    duplicate = apply_channel_decision(
        run_id=run_id,
        decision="approve",
        proposed_message="approved text",
        config=config,
    )

    assert calls == [
        {
            "url": "https://slack.test/api/chat.postMessage",
            "json": {"channel": "#task-rca-demo", "text": "approved text"},
            "headers": {
                "Authorization": "Bearer xoxb-test-token",
                "Content-Type": "application/json; charset=utf-8",
            },
            "timeout": 20,
        }
    ]
    assert result["publish"]["sent"] is True
    assert result["publish"]["slack_ok"] is True
    assert "xoxb-test-token" not in json.dumps(result)
    assert duplicate["publish"]["status"] == "duplicate_prevented"
    shutil.rmtree(run_workspace_dir(run_id), ignore_errors=True)


def test_edit_publish_sends_edited_message(monkeypatch):
    calls = []

    class Response:
        status_code = 200

        def json(self):
            return {"ok": True, "channel": "C123", "ts": "123.456"}

    monkeypatch.setattr(
        "deepagents_langgraph_rca.app.requests.post",
        lambda url, json, headers, timeout: calls.append(json) or Response(),
    )
    run_id = "channel-edit-smoke"
    shutil.rmtree(run_workspace_dir(run_id), ignore_errors=True)

    apply_channel_decision(
        run_id=run_id,
        decision="edit",
        proposed_message="original",
        edited_message="edited",
        config=config_with_bot_token(),
    )

    assert calls == [{"channel": "#task-rca-demo", "text": "edited"}]
    shutil.rmtree(run_workspace_dir(run_id), ignore_errors=True)


def test_reject_records_approval_without_http(monkeypatch):
    calls = []
    monkeypatch.setattr("deepagents_langgraph_rca.app.requests.post", lambda *args, **kwargs: calls.append(args))
    run_id = "channel-reject-smoke"
    shutil.rmtree(run_workspace_dir(run_id), ignore_errors=True)

    result = apply_channel_decision(
        run_id=run_id,
        decision="reject",
        proposed_message="do not send",
        config=config_with_bot_token(),
    )
    record = json.loads((run_workspace_dir(run_id) / "approval_record.json").read_text())

    assert result["sent"] is False
    assert record["decision"] == "reject"
    assert calls == []
    shutil.rmtree(run_workspace_dir(run_id), ignore_errors=True)


def test_slack_api_failure_does_not_persist_success(monkeypatch):
    class Response:
        status_code = 200

        def json(self):
            return {"ok": False, "error": "channel_not_found"}

    monkeypatch.setattr("deepagents_langgraph_rca.app.requests.post", lambda *args, **kwargs: Response())
    run_id = "channel-failure-smoke"
    shutil.rmtree(run_workspace_dir(run_id), ignore_errors=True)

    with pytest.raises(RuntimeError, match="channel_not_found"):
        apply_channel_decision(
            run_id=run_id,
            decision="approve",
            proposed_message="approved text",
            config=config_with_bot_token(),
        )

    assert not (run_workspace_dir(run_id) / "publish_result.json").exists()
    shutil.rmtree(run_workspace_dir(run_id), ignore_errors=True)


def test_real_slack_publish_final_acceptance():
    if os.getenv("RUN_REAL_SLACK_TEST") != "1":
        pytest.skip("Set RUN_REAL_SLACK_TEST=1 to perform the controlled real Slack publish.")

    config = load_config(require_model=False)
    config.channel.require_publish_config()
    assert config.channel.channel == "#task-rca-demo"

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"part12-real-slack-publish-{stamp}"
    shutil.rmtree(run_workspace_dir(run_id), ignore_errors=True)

    result = apply_channel_decision(
        run_id=run_id,
        decision="approve",
        proposed_message=(
            "Deep Agents + LangGraph RCA POC final acceptance smoke: "
            f"controlled human-approved publish for run {run_id}."
        ),
        config=config,
    )
    publish_path = run_workspace_dir(run_id) / "publish_result.json"
    persisted = json.loads(publish_path.read_text())
    rendered_result = json.dumps(result)
    rendered_persisted = json.dumps(persisted)

    assert result["publish"]["sent"] is True
    assert result["publish"]["slack_ok"] is True
    assert result["publish"]["channel"] == "#task-rca-demo"
    assert persisted["slack_ts"]
    assert config.channel.bot_token not in rendered_result
    assert config.channel.bot_token not in rendered_persisted
