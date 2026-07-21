# Architecture

Companion article:

[The Architecture Around the Agent Matters More Than the Prompt](https://recohut-sparsh.medium.com/the-architecture-around-the-agent-matters-more-than-the-prompt-0ae1cf8bc51a)

This PoC separates four responsibilities:

| Layer | Responsibility |
| --- | --- |
| Model | Planning, interpretation, hypothesis formation, and explanation |
| Deep Agents | Skills, tool registry, subagents, virtual filesystem, interrupts, structured response |
| LangGraph | Runtime state, threads, checkpoints, streaming, and pause/resume |
| Application | Evidence adapters, policies, scheduler, Slack boundary, validation, tests |

The coordinator does not receive raw filesystem access to evidence. It asks controlled tools for facts. Specialists receive smaller tool sets and return bounded evidence packets. The reviewer is mandatory before final synthesis.

The architecture is intentionally not a hardcoded classifier. Tools retrieve facts and calculate objective metrics. The model decides which evidence matters and which conclusion is supported.
