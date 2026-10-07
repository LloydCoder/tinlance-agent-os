from uuid import UUID

import pytest

from tinlance_agent_os import Transformation, TransformationContext, TransformationOutcome


def test_transformation_versioned_execution() -> None:
    item = Transformation(
        transformation_id=UUID("2f6d7a8a-5a12-4f8b-9a3e-3c1c2f4d8e11"),
        version=1,
        tenant_ref="tenant:example",
        objective="Reduce reconciliation time",
        context=TransformationContext("workspace:finance", "task:001"),
        agent_ref="agent:finance",
        agent_version="1.0.0",
    )
    completed = item.with_execution(
        "succeeded",
        run_ref="run:001",
        outcome=TransformationOutcome("achieved", True),
    )
    assert completed.version == 2
    assert item.execution_state == "planned"
    assert completed.outcome is not None
    assert completed.outcome.achieved


def test_achieved_outcome_cannot_be_false() -> None:
    with pytest.raises(ValueError):
        TransformationOutcome("achieved", False)
