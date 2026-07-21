# Fixture Policy

The active RCA runtime must work from whichever fixture root is configured. Runtime code, prompts, tools, and agent-facing instructions must not know whether a fixture is reference, counterfactual, or blind.

## Fixture A: Reference

The reference fixture uses the curated active task JSON, contracts, policies, and SQLite operational database. It is intended for manual inspection and regression tests. Tests may assert expected reference candidates, but those assertions must not be passed into model prompts or tool outputs.

## Fixture B: Counterfactual

Counterfactual fixtures are derived from the reference fixture by changing one decisive fact at a time, such as removing a contract clause or reversing an access decision. Evaluation should check whether the model stops citing removed evidence, lowers unsupported confidence, changes the conclusion, or reports insufficient evidence.

## Fixture C: Blind

Blind fixtures should rename employees, change IDs, shift dates, vary candidate counts, and include at least one new pattern. They are used to prove that the runtime does not depend on the reference people, task IDs, or exact cause phrases.
