# Evidence

The evidence is synthetic and intentionally small enough to audit.

Sources:

- `data/tasks/*.json`: task records and task-level fields;
- `data/operations/employee_operations.sqlite`: employees, attendance, leave, access events, access requests, and task status mirror;
- `data/contracts/*.md`: synthetic employee agreements;
- `data/policies/*.md`: synthetic workplace and security policies;
- `data/fixtures/*`: altered evidence worlds for validation.

The model cannot browse these paths directly. Source tools expose bounded records and attach evidence references.

The current validation target is not exact prose. The target is evidence-sensitive behavior: when decisive access evidence is removed or reversed, the conclusion should weaken or change.
