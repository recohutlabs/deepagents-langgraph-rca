# Demo Script

1. Show `README.md` and the architecture diagram.
2. Run `pytest` to prove the repo works without model or Slack credentials.
3. Configure `.env` with an OpenAI-compatible model endpoint.
4. Run one investigation:

   ```bash
   python scripts/run_investigation.py --as-of 2026-07-17 --task-id EMP002-T05 --run-id demo-emp002
   ```

5. Open `runs/demo-emp002` and inspect generated artifacts.
6. Run the counterfactual suite:

   ```bash
   python scripts/run_counterfactual_suite.py --as-of 2026-07-17 --task-id EMP002-T05 --run-id cf-demo
   ```

7. Explain that changed evidence should move the result.
8. Show Slack as an optional side-effect boundary, not a required part of RCA reasoning.
9. Switch `CHECKPOINTER_BACKEND=sqlite` and explain local restart-safe checkpoints.
