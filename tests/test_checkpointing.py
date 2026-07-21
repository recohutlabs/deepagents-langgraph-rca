from __future__ import annotations

from dataclasses import replace

import pytest
from langgraph.checkpoint.memory import MemorySaver

from deepagents_langgraph_rca.checkpoints import build_checkpointer
from deepagents_langgraph_rca.config import load_config


def test_memory_checkpointer_is_default():
    config = load_config(require_model=False)

    assert config.checkpoints.backend == "memory"
    assert isinstance(build_checkpointer(config), MemorySaver)


def test_sqlite_checkpointer_can_be_requested():
    config = load_config(require_model=False)
    sqlite_config = replace(config, checkpoints=replace(config.checkpoints, backend="sqlite"))

    try:
        checkpointer = build_checkpointer(sqlite_config)
    except Exception as exc:
        if "optional dependency" in str(exc):
            pytest.skip(str(exc))
        raise

    assert checkpointer is not None
    assert sqlite_config.checkpoints.sqlite_path.parent.name == "runs"
