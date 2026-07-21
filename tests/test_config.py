from pathlib import Path

import pytest

from deepagents_langgraph_rca.config import ConfigError, load_config


def write_env(path: Path, **overrides: str) -> Path:
    values = {
        "MODEL_NAME": "gpt-4.1-mini",
        "MODEL_BASE_URL": "https://api.openai.com/v1",
        "MODEL_API_KEY": "test-key",
        "MODEL_TEMPERATURE": "0",
        "MODEL_TIMEOUT_SECONDS": "120",
        "MODEL_MAX_RETRIES": "2",
        "MODEL_MAX_COMPLETION_TOKENS": "2048",
        "MODEL_THINKING": "disabled",
        "SLACK_CHANNEL": "#task-rca-demo",
        "SLACK_BOT_TOKEN": "",
        "SLACK_POST_MESSAGE_URL": "https://slack.com/api/chat.postMessage",
    }
    values.update(overrides)
    path.write_text("\n".join(f"{key}={value}" for key, value in values.items()))
    return path


def test_load_config_validates_paths_and_redacts_summary(tmp_path):
    config = load_config(write_env(tmp_path / ".env"), require_model=True)

    assert config.paths.root.name == "deepagents-langgraph-rca"
    assert config.paths.workspace_root.name == "runs"
    assert "legacy" not in config.paths.data_dir.relative_to(config.paths.root).parts
    assert config.model.model == "gpt-4.1-mini"
    assert config.model.temperature == 0
    summary = config.nonsecret_summary()
    assert "api_key" not in summary
    assert "test-key" not in repr(summary)


def test_missing_model_key_fails_clearly(tmp_path):
    env_path = write_env(tmp_path / ".env", MODEL_API_KEY="replace_with_your_model_key")

    with pytest.raises(ConfigError, match="Set MODEL_API_KEY"):
        load_config(env_path, require_model=True)


def test_malformed_numeric_values_fail_clearly(tmp_path):
    env_path = write_env(tmp_path / ".env", MODEL_TIMEOUT_SECONDS="soon")

    with pytest.raises(ConfigError, match="MODEL_TIMEOUT_SECONDS"):
        load_config(env_path, require_model=True)


def test_slack_config_is_required_only_for_publish(tmp_path):
    config = load_config(write_env(tmp_path / ".env"), require_model=True)

    with pytest.raises(ConfigError, match="SLACK_BOT_TOKEN"):
        config.channel.require_publish_config()


def test_invalid_checkpoint_backend_is_rejected(tmp_path):
    env_path = write_env(tmp_path / ".env", CHECKPOINTER_BACKEND="other")

    with pytest.raises(ConfigError, match="CHECKPOINTER_BACKEND"):
        load_config(env_path, require_model=True)
