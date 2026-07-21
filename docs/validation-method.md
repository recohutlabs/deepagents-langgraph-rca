# Validation Method

The validation method checks whether conclusions move with evidence.

Reference case:

- Evidence includes a blocked or denied access path for a task.
- The agent may identify an access/dependency cause if cited evidence supports it.

Removed-evidence case:

- Decisive access evidence is removed.
- The agent should lower confidence or return insufficient evidence.

Reversed-evidence case:

- Access evidence is changed to approval/availability.
- The agent should reject access denial as the cause.

Blind renamed case:

- Names and identifiers change.
- The agent should follow the evidence pattern rather than known labels.

Tests avoid checking exact language because live model prose varies. They check tool contracts, safety boundaries, fixture shape, and deterministic evidence differences.
