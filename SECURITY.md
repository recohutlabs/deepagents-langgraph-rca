# Security

Do not put real employee, customer, access-control, Slack, or model-provider secrets in this repository.

The PoC denies agent filesystem access to `.env`, source data, tests, docs, and expected outputs. Evidence is exposed through bounded tools instead. Slack publishing is optional and guarded by a human review boundary.

Report security concerns through the maintainers of the copied public repository.
