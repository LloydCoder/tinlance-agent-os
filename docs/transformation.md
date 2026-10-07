# P1 Transformation in Agent OS

Agent OS owns the operational lifecycle of a Transformation: workspace/task context, agent identity reference, execution state and outcome versioning.

Agent OS does **not** authorize the Transformation. Consequential authority remains in Tinlance Agent Platform.

A state transition creates a new immutable version rather than mutating the historical record.
