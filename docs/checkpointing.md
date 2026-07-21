# Checkpointing

LangGraph stores graph state through checkpointers.

`CHECKPOINTER_BACKEND=memory` is the default. It is simple and useful for tests, but the state is lost when the process exits.

`CHECKPOINTER_BACKEND=sqlite` stores checkpoints in `runs/checkpoints.sqlite`. This demonstrates local restart-safe persistence.

Neither setting is a complete production durability story. Production deployments usually need managed Postgres, clear thread identifiers, backups, retention policy, observability, and controlled resume handling.
