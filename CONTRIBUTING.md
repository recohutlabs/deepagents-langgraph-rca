# Contributing

This repository is a public proof of concept, not a production HR decision system.

Before opening a change:

- keep synthetic data synthetic;
- do not add secrets, tokens, workspace paths, or private run artifacts;
- keep source evidence behind controlled tools;
- keep tests runnable without model or Slack credentials;
- document any claim that expands what the PoC proves.

Run:

```bash
pip install -e ".[dev]"
pytest
python scripts/check_public_repository.py
```
