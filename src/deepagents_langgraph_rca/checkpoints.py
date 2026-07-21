from __future__ import annotations

import sqlite3
from typing import Any

from langgraph.checkpoint.memory import MemorySaver

from .config import AppConfig, ConfigError, load_config


def build_checkpointer(config: AppConfig | None = None) -> Any:
    """Build the configured LangGraph checkpointer."""
    app_config = config or load_config(require_model=False)
    backend = app_config.checkpoints.backend
    if backend == "memory":
        return MemorySaver()
    if backend == "sqlite":
        return build_sqlite_checkpointer(app_config)
    raise ConfigError("CHECKPOINTER_BACKEND must be memory or sqlite.")


def build_sqlite_checkpointer(config: AppConfig | None = None) -> Any:
    """Build a local SQLite checkpointer, when the optional package is installed."""
    app_config = config or load_config(require_model=False)
    app_config.checkpoints.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
    except ImportError as exc:
        raise ConfigError(
            "SQLite checkpointing requires the optional dependency group: "
            "pip install '.[sqlite]'"
        ) from exc

    connection = sqlite3.connect(app_config.checkpoints.sqlite_path, check_same_thread=False)
    return SqliteSaver(connection)
