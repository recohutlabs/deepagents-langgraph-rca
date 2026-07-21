from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


Confidence = float
CauseStatus = Literal["identified", "insufficient_evidence"]
ReviewDecision = Literal["accepted", "downgraded", "rejected", "unknown"]


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class EvidenceReference(StrictBaseModel):
    source_type: str = Field(min_length=1)
    source_location: str = Field(min_length=1)
    record_id: str | None = None
    observed_at: str | None = None


class EvidenceObservation(StrictBaseModel):
    observation: str = Field(min_length=1)
    evidence: list[EvidenceReference] = Field(min_length=1)


class ObjectiveMetric(StrictBaseModel):
    metric: str = Field(min_length=1)
    value: int | float | str | bool
    inputs: dict[str, Any] = Field(min_length=1)
    evidence: list[EvidenceReference] = Field(min_length=1)
    calculated_at: str | None = None


class CandidateFinding(StrictBaseModel):
    finding: str = Field(min_length=1)
    supporting_evidence: list[EvidenceReference] = Field(min_length=1)
    confidence: Confidence = Field(ge=0, le=1)
    limitations: list[str] = Field(default_factory=list)


class RejectedCause(StrictBaseModel):
    hypothesis: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    supporting_evidence: list[EvidenceReference] = Field(min_length=1)


class Unknown(StrictBaseModel):
    question: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    needed_evidence: list[str] = Field(default_factory=list)


class SpecialistPacket(StrictBaseModel):
    specialist_name: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    observations: list[EvidenceObservation] = Field(default_factory=list)
    objective_metrics: list[ObjectiveMetric] = Field(default_factory=list)
    candidate_findings: list[CandidateFinding] = Field(default_factory=list)
    rejected_hypotheses: list[RejectedCause] = Field(default_factory=list)
    unknowns: list[Unknown] = Field(default_factory=list)
    not_relevant: bool = False
    not_relevant_reason: str | None = None

    @model_validator(mode="after")
    def require_reason_when_not_relevant(self) -> SpecialistPacket:
        if self.not_relevant and not self.not_relevant_reason:
            raise ValueError("not_relevant_reason is required when not_relevant is true")
        return self


class PrimaryCause(StrictBaseModel):
    status: CauseStatus
    statement: str = Field(min_length=1)
    supporting_evidence: list[EvidenceReference] = Field(default_factory=list)
    confidence: Confidence = Field(ge=0, le=1)
    limitations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_evidence_for_identified_cause(self) -> PrimaryCause:
        if self.status == "identified" and not self.supporting_evidence:
            raise ValueError("identified primary cause requires supporting evidence")
        return self


class ContributingFactor(StrictBaseModel):
    factor: str = Field(min_length=1)
    supporting_evidence: list[EvidenceReference] = Field(min_length=1)
    confidence: Confidence = Field(ge=0, le=1)
    limitations: list[str] = Field(default_factory=list)


class RCAReport(StrictBaseModel):
    case_id: str = Field(min_length=1)
    as_of: str = Field(min_length=1)
    primary_cause: PrimaryCause
    contributing_factors: list[ContributingFactor] = Field(default_factory=list)
    rejected_causes: list[RejectedCause] = Field(default_factory=list)
    unknowns: list[Unknown] = Field(default_factory=list)
    recommended_next_action: str = Field(min_length=1)
    specialist_packets: list[SpecialistPacket] = Field(default_factory=list)


class FeedbackRecord(StrictBaseModel):
    run_id: str = Field(min_length=1)
    review_decision: str = Field(min_length=1)
    unsupported_claims: list[str] = Field(default_factory=list)
    missed_evidence: list[str] = Field(default_factory=list)
    suggested_skill_change: str | None = None
    approved_for_skill_update: bool = False

    @field_validator("suggested_skill_change")
    @classmethod
    def blank_suggestion_to_none(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            return None
        return value
