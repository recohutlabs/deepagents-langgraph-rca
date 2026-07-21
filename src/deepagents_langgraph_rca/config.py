from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from langchain_openai import ChatOpenAI


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PLACEHOLDER_KEYS = {
    "",
    "replace_with_your_model_key",
    "your-model-api-key",
}


class ConfigError(ValueError):
    """Raised when required runtime configuration is missing or invalid."""


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    data_dir: Path
    task_dir: Path
    contracts_dir: Path
    policies_dir: Path
    operations_db: Path
    workspace_root: Path
    env_path: Path


@dataclass(frozen=True)
class ModelSettings:
    model: str
    base_url: str
    api_key: str
    temperature: float
    timeout_seconds: float
    max_retries: int
    max_completion_tokens: int
    thinking: str


@dataclass(frozen=True)
class ChannelSettings:
    channel: str
    bot_token: str
    post_message_url: str

    def require_publish_config(self) -> None:
        if not self.bot_token.strip():
            raise ConfigError("SLACK_BOT_TOKEN is required only when publishing is attempted.")


@dataclass(frozen=True)
class CheckpointSettings:
    backend: str
    sqlite_path: Path


@dataclass(frozen=True)
class AppConfig:
    paths: ProjectPaths
    model: ModelSettings
    channel: ChannelSettings
    checkpoints: CheckpointSettings

    def nonsecret_summary(self) -> dict[str, Any]:
        return {
            "root": str(self.paths.root),
            "data_dir": str(self.paths.data_dir),
            "workspace_root": str(self.paths.workspace_root),
            "model": self.model.model,
            "base_url": self.model.base_url,
            "temperature": self.model.temperature,
            "timeout_seconds": self.model.timeout_seconds,
            "max_retries": self.model.max_retries,
            "max_completion_tokens": self.model.max_completion_tokens,
            "thinking": self.model.thinking,
            "channel": self.channel.channel,
            "channel_configured": bool(self.channel.bot_token.strip()),
            "checkpointer_backend": self.checkpoints.backend,
            "checkpointer_sqlite_path": str(self.checkpoints.sqlite_path),
        }


def _as_project_path(*parts: str) -> Path:
    path = (PROJECT_ROOT / Path(*parts)).resolve()
    root = PROJECT_ROOT.resolve()
    if path == root or root in path.parents:
        if "legacy" not in path.relative_to(root).parts:
            return path
    raise ConfigError(f"Configured path must stay inside active project and outside legacy: {path}")


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _float_env(name: str, default: str) -> float:
    value = _env(name, default)
    try:
        return float(value)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number; got {value!r}.") from exc


def _int_env(name: str, default: str) -> int:
    value = _env(name, default)
    try:
        return int(value)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer; got {value!r}.") from exc


def load_config(env_path: Path | None = None, *, require_model: bool = True) -> AppConfig:
    env_file = env_path or _as_project_path(".env")
    file_values = dotenv_values(env_file) if env_file.exists() else {}

    def env(name: str, default: str = "") -> str:
        value = file_values.get(name)
        if value is not None:
            return str(value).strip()
        return os.getenv(name, default).strip()

    def float_env(name: str, default: str) -> float:
        value = env(name, default)
        try:
            return float(value)
        except ValueError as exc:
            raise ConfigError(f"{name} must be a number; got {value!r}.") from exc

    def int_env(name: str, default: str) -> int:
        value = env(name, default)
        try:
            return int(value)
        except ValueError as exc:
            raise ConfigError(f"{name} must be an integer; got {value!r}.") from exc

    api_key = env("MODEL_API_KEY")
    if require_model and api_key in PLACEHOLDER_KEYS:
        raise ConfigError("Set MODEL_API_KEY before constructing a live model.")

    paths = ProjectPaths(
        root=PROJECT_ROOT.resolve(),
        data_dir=_as_project_path("data"),
        task_dir=_as_project_path("data", "tasks"),
        contracts_dir=_as_project_path("data", "contracts"),
        policies_dir=_as_project_path("data", "policies"),
        operations_db=_as_project_path("data", "operations", "employee_operations.sqlite"),
        workspace_root=_as_project_path("runs"),
        env_path=env_file.resolve(),
    )
    model = ModelSettings(
        model=env("MODEL_NAME", "gpt-4.1-mini"),
        base_url=env("MODEL_BASE_URL", "https://api.openai.com/v1"),
        api_key=api_key,
        temperature=float_env("MODEL_TEMPERATURE", "0"),
        timeout_seconds=float_env("MODEL_TIMEOUT_SECONDS", "120"),
        max_retries=int_env("MODEL_MAX_RETRIES", "2"),
        max_completion_tokens=int_env("MODEL_MAX_COMPLETION_TOKENS", "2048"),
        thinking=env("MODEL_THINKING", "disabled"),
    )
    channel = ChannelSettings(
        channel=env("SLACK_CHANNEL", "#task-rca-demo"),
        bot_token=env("SLACK_BOT_TOKEN"),
        post_message_url=env("SLACK_POST_MESSAGE_URL", "https://slack.com/api/chat.postMessage"),
    )
    checkpoint_backend = env("CHECKPOINTER_BACKEND", "memory").lower()
    if checkpoint_backend not in {"memory", "sqlite"}:
        raise ConfigError("CHECKPOINTER_BACKEND must be memory or sqlite.")
    checkpoints = CheckpointSettings(
        backend=checkpoint_backend,
        sqlite_path=_as_project_path("runs", "checkpoints.sqlite"),
    )
    return AppConfig(paths=paths, model=model, channel=channel, checkpoints=checkpoints)


def build_model(config: AppConfig | None = None) -> ChatOpenAI:
    app_config = config or load_config(require_model=True)
    settings = app_config.model
    if settings.api_key in PLACEHOLDER_KEYS:
        raise ConfigError("Set MODEL_API_KEY before constructing a live model.")
    kwargs: dict[str, Any] = {
        "model": settings.model,
        "api_key": settings.api_key,
        "base_url": settings.base_url,
        "temperature": settings.temperature,
        "timeout": settings.timeout_seconds,
        "max_retries": settings.max_retries,
        "max_completion_tokens": settings.max_completion_tokens,
    }
    if settings.thinking and settings.thinking.lower() != "disabled":
        kwargs["extra_body"] = {"thinking": {"type": settings.thinking}}
    return ChatOpenAI(**kwargs)
