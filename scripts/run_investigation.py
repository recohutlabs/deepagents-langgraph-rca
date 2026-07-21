from __future__ import annotations

import sys

from deepagents_langgraph_rca.cli import main


if __name__ == "__main__":
    sys.argv.insert(1, "investigate")
    raise SystemExit(main())
