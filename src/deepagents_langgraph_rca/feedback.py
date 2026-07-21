from __future__ import annotations

from .app import write_case_artifact
from .config import AppConfig, load_config
from .schemas import FeedbackRecord


def record_feedback(
    *,
    run_id: str,
    review_decision: str,
    unsupported_claims: list[str] | None = None,
    missed_evidence: list[str] | None = None,
    suggested_skill_change: str | None = None,
    approved_for_skill_update: bool = False,
    config: AppConfig | None = None,
) -> FeedbackRecord:
    app_config = config or load_config(require_model=False)
    record = FeedbackRecord(
        run_id=run_id,
        review_decision=review_decision,
        unsupported_claims=unsupported_claims or [],
        missed_evidence=missed_evidence or [],
        suggested_skill_change=suggested_skill_change,
        approved_for_skill_update=approved_for_skill_update,
    )
    write_case_artifact(run_id, "feedback_record.json", record.model_dump(), app_config)
    return record
