from __future__ import annotations

from pathlib import Path

from scripts.check_public_repository import run_checks


ROOT = Path(__file__).resolve().parents[1]


def test_public_repository_contains_no_private_paths_or_secret_patterns():
    assert run_checks(ROOT) == []


def test_no_private_env_or_storage_history_is_present():
    assert not (ROOT / ".env").exists()
    assert not (ROOT / "legacy").exists()
    assert not (ROOT / "storage").exists()
    assert (ROOT / ".env.example").exists()
