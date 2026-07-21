import json

import pytest
from pydantic import ValidationError

from deepagents_langgraph_rca.schemas import (
    CandidateFinding,
    EvidenceObservation,
    EvidenceReference,
    FeedbackRecord,
    ObjectiveMetric,
    PrimaryCause,
    RCAReport,
    RejectedCause,
    SpecialistPacket,
    Unknown,
)


def evidence(record_id: str = "record-1") -> EvidenceReference:
    return EvidenceReference(
        source_type="task_json",
        source_location="data/tasks/example.json",
        record_id=record_id,
    )


def test_schema_accepts_supported_report_and_round_trips_json():
    ref = evidence()
    packet = SpecialistPacket(
        specialist_name="task-timeline-analyst",
        case_id="case-1",
        observations=[
            EvidenceObservation(observation="A task has a recorded due date.", evidence=[ref])
        ],
        objective_metrics=[
            ObjectiveMetric(
                metric="days_overdue",
                value=1,
                inputs={"due_date": "2026-07-16", "as_of": "2026-07-17"},
                evidence=[ref],
            )
        ],
        candidate_findings=[
            CandidateFinding(
                finding="The timeline requires more investigation.",
                supporting_evidence=[ref],
                confidence=0.4,
            )
        ],
    )
    report = RCAReport(
        case_id="case-1",
        as_of="2026-07-17",
        primary_cause=PrimaryCause(
            status="identified",
            statement="A supported operational issue was found.",
            supporting_evidence=[ref],
            confidence=0.7,
        ),
        contributing_factors=[],
        rejected_causes=[
            RejectedCause(
                hypothesis="A tested hypothesis",
                reason="Available evidence did not support it.",
                supporting_evidence=[ref],
            )
        ],
        unknowns=[Unknown(question="Missing question", reason="Source is unavailable.")],
        recommended_next_action="Review the cited evidence.",
        specialist_packets=[packet],
    )

    loaded = RCAReport.model_validate(json.loads(report.model_dump_json()))
    assert loaded == report


def test_identified_primary_cause_requires_evidence():
    with pytest.raises(ValidationError, match="supporting evidence"):
        PrimaryCause(
            status="identified",
            statement="A claim without support.",
            confidence=0.8,
        )


def test_insufficient_evidence_primary_cause_is_allowed_without_citation():
    cause = PrimaryCause(
        status="insufficient_evidence",
        statement="Available evidence is not enough to identify one cause.",
        confidence=0,
    )
    assert cause.supporting_evidence == []


def test_malformed_confidence_values_are_rejected():
    with pytest.raises(ValidationError):
        CandidateFinding(
            finding="Unsupported confidence value.",
            supporting_evidence=[evidence()],
            confidence=1.5,
        )


def test_objective_metric_requires_source_inputs():
    with pytest.raises(ValidationError):
        ObjectiveMetric(metric="days_overdue", value=1, inputs={}, evidence=[evidence()])


def test_not_relevant_packet_requires_reason():
    with pytest.raises(ValidationError, match="not_relevant_reason"):
        SpecialistPacket(
            specialist_name="dependency-access-analyst",
            case_id="case-1",
            not_relevant=True,
        )


def test_feedback_record_does_not_require_skill_update_approval():
    record = FeedbackRecord(
        run_id="run-1",
        review_decision="partially_correct",
        unsupported_claims=["Claim needs stronger citation."],
        missed_evidence=[],
        suggested_skill_change="",
        approved_for_skill_update=False,
    )
    assert record.suggested_skill_change is None
    assert record.approved_for_skill_update is False
