# Public Boundaries

This repository is a public architecture PoC.

It is not:

- a production HR system;
- legal or employment advice;
- a disciplinary decision system;
- a privacy-complete deployment;
- proof that a model is independently verified;
- proof of production durability without persistent deployment storage.

Synthetic data exists only to exercise the architecture. The case study is not a real workplace record.

The PoC uses one coordinator, four evidence specialists, and one reviewer. The reviewer is a model role with a different contract, not an independent deterministic verifier.

SQLite checkpointing demonstrates local persistence. Production use needs managed storage, authentication, monitoring, retention policy, tenant isolation, and formal evaluation.
