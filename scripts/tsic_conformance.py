#!/usr/bin/env python3
"""Fail-closed verification of Agent OS compatibility with the canonical TSIC contract."""

from __future__ import annotations

import json
from urllib.request import Request, urlopen

TSIC_REVISION = "ae53c58afd78b48b1f0b95640ca0db698018cd7d"
RAW_ROOT = f"https://raw.githubusercontent.com/LloydCoder/tinlance-system-integration/{TSIC_REVISION}"
REQUIRED = {
    "identity-context",
    "agent-registration",
    "event-envelope",
    "delivery-semantics",
    "trace-context",
    "agent-interoperability-gate",
    "economic-attribution",
}


def fetch_json(path: str) -> dict:
    request = Request(
        f"{RAW_ROOT}/{path}",
        headers={"Accept": "application/json", "User-Agent": "tinlance-agent-os-ci"},
    )
    with urlopen(request, timeout=15) as response:
        if response.status != 200:
            raise RuntimeError(f"TSIC contract fetch failed for {path}: HTTP {response.status}")
        return json.load(response)


def main() -> None:
    manifest = fetch_json("manifests/ecosystem.json")
    adapter = fetch_json("integrations/agent-os/adapter.json")
    registry = fetch_json("catalog/contracts/registry.json")

    os_entry = next(item for item in manifest["systems"] if item["id"] == "agent-os")
    if os_entry["repository"] != "LloydCoder/tinlance-agent-os":
        raise AssertionError("TSIC Agent OS repository mapping is stale")
    if os_entry.get("governance_role") != "operating_environment_authority":
        raise AssertionError("TSIC Agent OS governance role is incorrect")

    if adapter["source_system"] != "tsic" or adapter["target_system"] != "agent-os":
        raise AssertionError("invalid TSIC Agent OS adapter endpoints")
    bindings = {item["tsic_contract"] for item in adapter["contract_bindings"]}
    if bindings != REQUIRED:
        raise AssertionError(
            f"TSIC Agent OS binding drift: expected {sorted(REQUIRED)}, got {sorted(bindings)}"
        )

    registered = {item["id"] for item in registry["contracts"]}
    if not registered >= REQUIRED:
        raise AssertionError("TSIC registry is missing an Agent OS contract")

    authority = adapter["authority"]
    if authority["integration_contracts"] != "tsic":
        raise AssertionError("TSIC must remain integration-contract authority")
    if authority["workspace_lifecycle_orchestration"] != "agent-os":
        raise AssertionError("Agent OS lifecycle authority drift")
    if authority["execution_authority"] != "agent-platform":
        raise AssertionError("Platform execution authority drift")

    invariants = set(adapter["invariants"])
    required_invariants = {
        "os_never_grants_execution_authority",
        "os_never_replaces_platform_authorization",
        "workspace_tenant_context_is_immutable",
        "trace_context_is_preserved",
        "retries_are_idempotency_aware",
        "platform_remains_consequential_authority",
    }
    if invariants != required_invariants:
        raise AssertionError("TSIC Agent OS invariant drift")

    print("PASS TSIC Agent OS conformance:", f"revision={TSIC_REVISION} contracts={len(bindings)}")


if __name__ == "__main__":
    main()
