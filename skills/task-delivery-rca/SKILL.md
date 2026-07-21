# Task Delivery RCA Skill

Use this skill to investigate why a task missed, may miss, or appears at risk of missing its expected delivery state. The goal is an evidence-led root-cause analysis that is useful for process repair, not employee blame.

## Operating Rule

Separate facts from interpretation.

- A fact is a source-backed record, document clause, event, task field, or objective metric.
- An observation restates one or more facts without adding motive or cause.
- An inference explains what the facts may indicate and must name its limits.
- A conclusion is accepted only after evidence review confirms it is supported.

Objective calculations are allowed when they only compute values from source inputs, such as days past due, leave overlap, task counts, recorded hours, approval presence, access status, VPN-use status, and task-state history. These calculations are evidence inputs, not RCA conclusions.

## Top-Funnel Eligibility

When asked to find candidate tasks, use the supplied `as_of` date and retrieve task records from tools.

Treat `Done` and `Cancelled` as terminal statuses. A task is a candidate only when its due date is before the `as_of` date and its status is not terminal. If no task qualifies, report that no eligible candidates were found. Do not invent a candidate.

Do not assume any fixed number of candidates. Do not rely on employee names, task IDs, fixture names, or known case counts.

## Investigation Plan

Before final synthesis, write a short investigation plan that states which evidence is needed and which specialists should be used.

Use evidence specialists dynamically:

- Use the task timeline analyst when dates, state changes, work sequence, missing periods, or event order matter.
- Use the workload priority analyst when concurrent tasks, recorded hours, leave, capacity, or priority conflicts may matter.
- Use the dependency access analyst when systems, approvals, requests, blocked events, data freshness, or alternate access routes may matter.
- Use the contract policy analyst when role scope, assignment authority, documented restrictions, or policy clauses may matter.
- Always use the evidence privacy reviewer before final synthesis.

It is acceptable for an evidence specialist to return `not relevant` when it explains why with available evidence or a clear lack of evidence.

## Evidence Filter

For every candidate explanation, apply this funnel:

1. Top-funnel inputs: task records, employee records, attendance, leave, access activity, access requests, contracts, policies, and objective metrics.
2. Evidence filter: remove unsupported claims, private speculation, employee blame, stale evidence, duplicate evidence, and statements that overreach the cited source.
3. RCA outputs: primary cause or insufficient evidence, contributing factors, rejected causes, and unknowns.

## Primary Cause

A primary cause is the best-supported process or operational explanation for the delivery issue. It must cite evidence and explain why it is stronger than other tested explanations.

Use `insufficient_evidence` when the available record cannot support one primary cause. This is a valid result.

Do not turn a single fact directly into a predetermined cause. A blocked event, missing approval, busy week, task title, role name, or document clause can support an inference only when the surrounding evidence connects it to task delivery.

## Contributing Factors

A contributing factor is supported evidence that plausibly worsened, delayed, constrained, or complicated delivery but is not strong enough to be the main explanation.

Contributing factors require citations and limits. Do not include generic background facts unless they affected the task.

## Rejected Causes

A rejected cause is a hypothesis that was considered and not supported. Include:

- the hypothesis
- the reason it was rejected or downgraded
- the evidence used to reject it

Rejected causes are valuable because they show that the analysis tested alternatives.

## Unknowns

Record unknowns when evidence is missing, contradictory, private, or outside the allowed source surface. Do not fill unknowns with assumptions.

Examples of useful unknowns:

- missing approval trail
- missing task-state history
- unclear assignment exception
- unavailable source system record

## Privacy And Tone

Use process-focused, non-blaming language. Do not speculate about:

- motivation
- attitude
- intent
- health details
- discipline
- performance character
- personal circumstances beyond what policy-relevant records explicitly state

When medical, accommodation, leave, or personal information appears in evidence, mention only the minimum operational rule needed for the analysis.

## Citation Requirements

Every accepted causal claim must cite at least one source reference. Prefer direct operational records and policy or contract text over summaries.

If a claim cannot be tied to evidence, downgrade it to an unknown or reject it.

## Final Output Shape

The final report must include:

- case identity
- `as_of` date
- primary cause or insufficient evidence
- contributing factors
- rejected causes
- unknowns
- recommended next action
- evidence references

The recommended next action should repair the process or unblock delivery. It should not assign blame.
