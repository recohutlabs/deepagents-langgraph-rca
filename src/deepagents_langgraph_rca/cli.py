from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .app import (
    apply_channel_decision,
    build_app,
    build_investigation_message,
    invoke_app,
    summarize_event,
)
from .config import load_config
from .sources import DataSources


def _print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, sort_keys=True, default=str))


def run_investigation(args: argparse.Namespace) -> int:
    config = load_config(require_model=True)
    sources = DataSources(config, fixture=args.fixture)
    agent = build_app(config=config, sources=sources)
    message = build_investigation_message(
        as_of=args.as_of,
        task_id=args.task_id,
        fixture=args.fixture,
        force_all_specialists=args.force_all_specialists,
    )
    result = invoke_app(agent, [message], thread_id=args.run_id)
    _print_json(result)
    return 0


def run_counterfactual_suite(args: argparse.Namespace) -> int:
    fixtures = [
        ("reference", None),
        ("removed-access", "counterfactual/removed-access"),
        ("reversed-access", "counterfactual/reversed-access"),
        ("renamed-case", "blind/renamed-case"),
    ]
    config = load_config(require_model=True)
    results = []
    for label, fixture in fixtures:
        sources = DataSources(config, fixture=fixture)
        agent = build_app(config=config, sources=sources)
        message = build_investigation_message(as_of=args.as_of, task_id=args.task_id, fixture=fixture)
        result = invoke_app(agent, [message], thread_id=f"{args.run_id}-{label}")
        results.append({"fixture": label, "result": result})
    _print_json({"as_of": args.as_of, "results": results})
    return 0


def preview_channel_update(args: argparse.Namespace) -> int:
    result = apply_channel_decision(
        run_id=args.run_id,
        decision=args.decision,
        proposed_message=args.message,
        edited_message=args.edited_message,
        channel=args.channel,
    )
    _print_json(result)
    return 0


def check_public_repository(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    from scripts.check_public_repository import run_checks

    issues = run_checks(root)
    _print_json({"root": str(root), "issues": issues, "ok": not issues})
    return 1 if issues else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="deepagents-langgraph-rca")
    subparsers = parser.add_subparsers(dest="command", required=True)

    investigate = subparsers.add_parser("investigate")
    investigate.add_argument("--as-of", required=True)
    investigate.add_argument("--task-id", default="")
    investigate.add_argument("--fixture", default="")
    investigate.add_argument("--run-id", default="manual-investigation")
    investigate.add_argument("--force-all-specialists", action="store_true")
    investigate.set_defaults(func=run_investigation)

    suite = subparsers.add_parser("counterfactual-suite")
    suite.add_argument("--as-of", required=True)
    suite.add_argument("--task-id", default="")
    suite.add_argument("--run-id", default="counterfactual-suite")
    suite.set_defaults(func=run_counterfactual_suite)

    channel = subparsers.add_parser("channel-decision")
    channel.add_argument("--run-id", required=True)
    channel.add_argument("--decision", choices=["approve", "edit", "reject"], required=True)
    channel.add_argument("--message", required=True)
    channel.add_argument("--edited-message", default="")
    channel.add_argument("--channel", default="")
    channel.set_defaults(func=preview_channel_update)

    safety = subparsers.add_parser("check-public-repository")
    safety.add_argument("--root", default=".")
    safety.set_defaults(func=check_public_repository)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
