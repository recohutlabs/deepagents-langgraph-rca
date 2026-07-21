from __future__ import annotations

import argparse
import re
from pathlib import Path


SECRET_PATTERNS = [
    re.compile(r"xox[baprs]-\\d{6,}-\\d{6,}-[A-Za-z0-9-]{10,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
]

TEXT_SUFFIXES = {
    ".env",
    ".example",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}


def _is_text(path: Path) -> bool:
    return path.suffix in TEXT_SUFFIXES or path.name in {".gitignore", "LICENSE"}


def run_checks(root: Path) -> list[str]:
    issues: list[str] = []
    for path in sorted(root.rglob("*")):
        if ".git" in path.parts or path.is_dir():
            continue
        rel = path.relative_to(root)
        if path.name == ".env":
            issues.append(f"private env file must not be committed: {rel}")
        if "storage" in path.parts or "legacy" in path.parts:
            issues.append(f"private implementation artifact must not be public: {rel}")
        if not _is_text(path):
            continue
        text = path.read_text(errors="ignore")
        if ("/" + "Users/") in text:
            issues.append(f"absolute local path found in {rel}")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                issues.append(f"possible secret pattern found in {rel}")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    issues = run_checks(Path(args.root).resolve())
    if issues:
        print("Public repository checks failed:")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("Public repository checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
