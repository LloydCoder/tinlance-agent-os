from uuid import UUID

import pytest

from tinlance_agent_os import (
    Transformation,
    TransformationCapability,
    TransformationConstraints,
    TransformationContext,
    TransformationGovernance,
    TransformationMetric,
    TransformationOutcome,
    TransformationProvenance,
    TransformationReference,
)


def make_transformation() -> Transformation:
    return Transformation(
        transformation_id=UUID("2f6d7a8a-5a12-4f8b-9a3e-3c1c2f4d8e11"),
        version=1,
        tenant_ref="tenant:example",
        objective="Reduce reconciliation time",
        success_criteria=("Produce a reconciled report",),
        principal_ref="principal:human-001",
        agent_ref="agent:finance",
        agent_version="1.0.0",
        context=TransformationContext(
            "workspace:finance",
            "task:001",
            ("source:ledger",),
        ),
        requested_capabilities=(
            TransformationCapability("capability:finance.reconcile", "reconcile ledger"),
        ),
        governance=TransformationGovernance(("policy:finance",), "high", ("approval:001",)),
        idempotency_key="transformation-2f6d7a8a-v1",
        provenance=TransformationProvenance(
            "tadl:p1",
            "2026-10-07T06:02:01Z",
            ("source:request-001",),
        ),
        constraints=TransformationConstraints(
            budget_ref="budget:task-001",
            data_classification="confidential",
            resource_refs=("resource:ledger",),
        ),
        business_metric="reconciliation_cycle_hours",
    )


def test_transformation_round_trips_canonical_fields_and_versions_execution() -> None:
    item = make_transformation()
    completed = item.with_execution(
        "succeeded",
        run_ref="run:001",
        outcome=TransformationOutcome(
            "achieved",
            True,
            metrics=(TransformationMetric("cycle_hours", 2, "hours"),),
            business_effect_refs=("effect:reduced-close-time",),
        ),
        outputs=(TransformationReference("artifact:report", "report"),),
        evidence=(TransformationReference("evidence:run", "execution"),),
        started_at="2026-10-07T06:00:00Z",
        completed_at="2026-10-07T06:02:00Z",
    )
    payload = completed.as_payload()
    assert completed.version == 2
    assert item.execution_state == "planned"
    assert payload["schema_version"] == "transformation/v1"
    assert {
        "schema_version", "transformation_id", "version", "tenant_ref", "intent", "actor",
        "context", "requested_capabilities", "constraints", "governance", "execution",
        "outputs", "evidence", "outcome", "provenance",
    }.issubset(payload)
    assert payload["intent"]["success_criteria"] == ["Produce a reconciled report"]
    assert payload["constraints"]["data_classification"] == "confidential"
    assert payload["governance"]["approval_refs"] == ["approval:001"]
    assert payload["execution"]["idempotency_key"].endswith("-v2")
    assert payload["outputs"][0]["ref"] == "artifact:report"
    assert payload["evidence"][0]["ref"] == "evidence:run"
    assert payload["provenance"]["declared_by"] == "tadl:p1"
    assert completed.content_digest() == completed.content_digest()


def test_achieved_outcome_requires_consistent_status_and_flag() -> None:
    with pytest.raises(ValueError):
        TransformationOutcome("achieved", False)
    with pytest.raises(ValueError):
        TransformationOutcome("partially_achieved", True)


def test_provenance_requires_timezone_aware_recorded_at() -> None:
    with pytest.raises(ValueError):
        TransformationProvenance("tadl:p1", "2026-10-07T06:02:01")
