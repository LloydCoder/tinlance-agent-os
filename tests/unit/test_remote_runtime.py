from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tinlance_agent_os.domain import PlatformRunRef
from tinlance_agent_os.remote_runtime import (
    EndpointIdentity,
    EndpointState,
    FilesystemBinding,
    LocalProcessSupervisor,
    MCPRemoteTransport,
    NetworkPolicy,
    RemoteRuntime,
    RemoteTaskState,
    ResourceLimits,
)
from tinlance_agent_os.store import StateStore


class Authenticator:
    def verify(self, identity, workspace_id):
        return identity.attestation == f"{workspace_id}:{identity.fingerprint}"


class Platform:
    def __init__(self):
        self.created = []
        self.cancelled = []

    def create_run(self, *, task_id, agent_id, intent, idempotency_key=None):
        self.created.append((task_id, agent_id, intent, idempotency_key))
        return PlatformRunRef(f"run-{task_id}", task_id, "running")

    def cancel_run(self, *, run_id):
        self.cancelled.append(run_id)
        return PlatformRunRef(run_id, "task", "cancelled")


class MCPClient:
    def __init__(self):
        self.requests = []

    def request(self, *, method, name, arguments, metadata):
        self.requests.append((method, name, arguments, metadata))
        return {"accepted": True}


def seed(tmp_path: Path):
    store = StateStore(tmp_path / "state.db")
    store.upsert_workspace("ws-1", "owner", "2026-09-30T00:00:00+00:00")
    platform = Platform()
    runtime = RemoteRuntime(
        store,
        platform,
        Authenticator(),
        MCPRemoteTransport(MCPClient()),
        NetworkPolicy(allowed_hosts=frozenset({"8.8.8.8"})),
    )
    return store, platform, runtime


def identity(workspace="ws-1", fingerprint="fp-1"):
    return EndpointIdentity(
        "endpoint-1",
        fingerprint,
        f"{workspace}:{fingerprint}",
    )


def test_enrollment_authentication_heartbeat_and_reconnect(tmp_path: Path):
    store, _, runtime = seed(tmp_path)
    endpoint = runtime.enroll(
        workspace_id="ws-1",
        tenant_id="tenant-1",
        identity=identity(),
        address="https://8.8.8.8/mcp",
    )
    assert endpoint.state is EndpointState.ENROLLED
    healthy = runtime.heartbeat(identity())
    assert healthy.state is EndpointState.HEALTHY
    assert runtime.reconnect(identity()).state is EndpointState.HEALTHY
    assert runtime.route("ws-1")[0].identity.endpoint_id == "endpoint-1"
    assert store.query("SELECT COUNT(*) AS n FROM remote_endpoints")[0]["n"] == 1


def test_forged_endpoint_and_cross_workspace_enrollment_fail(tmp_path: Path):
    _, _, runtime = seed(tmp_path)
    with pytest.raises(PermissionError):
        runtime.enroll(
            workspace_id="ws-1",
            tenant_id="tenant-1",
            identity=EndpointIdentity("endpoint-1", "forged", "bad"),
            address="https://8.8.8.8/mcp",
        )
    with pytest.raises(PermissionError):
        runtime.enroll(
            workspace_id="ws-1",
            tenant_id="tenant-1",
            identity=identity("ws-2", "fp-2"),
            address="https://8.8.8.8/mcp",
        )


def test_network_policy_rejects_unapproved_endpoint(tmp_path: Path):
    _, _, runtime = seed(tmp_path)
    with pytest.raises(PermissionError, match="allowed"):
        runtime.enroll(
            workspace_id="ws-1",
            tenant_id="tenant-1",
            identity=identity(),
            address="https://evil.example/mcp",
        )


def test_assign_uses_platform_authority_and_stable_idempotency(tmp_path: Path):
    _, platform, runtime = seed(tmp_path)
    runtime.enroll(
        workspace_id="ws-1",
        tenant_id="tenant-1",
        identity=identity(),
        address="https://8.8.8.8/mcp",
    )
    runtime.heartbeat(identity())
    task = runtime.assign(
        endpoint_id="endpoint-1",
        task_id="task-1",
        workspace_id="ws-1",
        agent_id="agent-1",
        intent="run remote work",
        trace_id="tr_123",
    )
    assert task.state is RemoteTaskState.ASSIGNED
    assert platform.created == [("task-1", "agent-1", "run remote work", "remote:task-1")]


def test_cancel_propagates_to_remote_and_platform(tmp_path: Path):
    _, platform, runtime = seed(tmp_path)
    runtime.enroll(
        workspace_id="ws-1",
        tenant_id="tenant-1",
        identity=identity(),
        address="https://8.8.8.8/mcp",
    )
    runtime.heartbeat(identity())
    runtime.assign(
        endpoint_id="endpoint-1",
        task_id="task-1",
        workspace_id="ws-1",
        agent_id="agent-1",
        intent="run remote work",
        trace_id="tr_123",
    )
    task = runtime.cancel("task-1")
    assert task.state is RemoteTaskState.CANCELLED
    assert platform.cancelled == ["run-task-1"]


def test_drain_blocks_new_assignment(tmp_path: Path):
    _, _, runtime = seed(tmp_path)
    runtime.enroll(
        workspace_id="ws-1",
        tenant_id="tenant-1",
        identity=identity(),
        address="https://8.8.8.8/mcp",
    )
    runtime.heartbeat(identity())
    runtime.drain("endpoint-1")
    with pytest.raises(Exception, match="not healthy"):
        runtime.assign(
            endpoint_id="endpoint-1",
            task_id="task-1",
            workspace_id="ws-1",
            agent_id="agent-1",
            intent="run remote work",
            trace_id="tr_123",
        )


def test_filesystem_binding_is_root_confined(tmp_path: Path):
    root = tmp_path / "agent"
    root.mkdir()
    backend = FilesystemBinding(root).backend()
    backend.write_file(Path("data.txt"), b"ok")
    assert backend.read_file(Path("data.txt")) == b"ok"
    with pytest.raises(PermissionError):
        backend.read_file(Path("../outside.txt"))


def test_local_process_supervisor_applies_bounds_and_reaps(tmp_path: Path):
    supervisor = LocalProcessSupervisor(
        ResourceLimits(cpu_seconds=5, memory_bytes=256 * 1024 * 1024)
    )
    pid = supervisor.start(
        "p1",
        [sys.executable, "-c", "print('ok')"],
        cwd=tmp_path,
    )
    assert pid > 0
    assert supervisor.poll("p1") in {None, 0}
    if "p1" in supervisor.children:
        supervisor.children["p1"].wait(timeout=2)
        assert supervisor.poll("p1") == 0


def test_supervised_process_rejects_environment_escape(tmp_path: Path):
    supervisor = LocalProcessSupervisor(ResourceLimits())
    with pytest.raises(PermissionError, match="unsafe"):
        supervisor.start(
            "p1",
            [sys.executable, "-c", "print('ok')"],
            cwd=tmp_path,
            environment={"PYTHONPATH": "/tmp/attacker"},
        )


def test_mcp_transport_uses_mcp_method_surface(tmp_path: Path):
    client = MCPClient()
    transport = MCPRemoteTransport(client)
    transport.assign(
        endpoint=identity(),
        task_id="task-1",
        run_id="run-1",
        trace_id="tr_1",
        idempotency_key="remote:task-1",
    )
    assert client.requests[0][0:2] == ("tools/call", "tinlance.agent.assign")


def test_network_policy_fails_closed_without_explicit_host_allowlist():
    with pytest.raises(PermissionError, match="allowlist"):
        NetworkPolicy().validate("https://8.8.8.8/mcp")


def test_network_policy_rejects_hostname_resolving_to_private_address(monkeypatch):
    import socket

    def resolve_private(host, port, *, type):
        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("10.20.30.40", port or 443),
            )
        ]

    monkeypatch.setattr(socket, "getaddrinfo", resolve_private)
    policy = NetworkPolicy(allowed_hosts=frozenset({"agent.example"}))

    with pytest.raises(PermissionError, match="non-public"):
        policy.validate("https://agent.example/mcp")


def test_network_policy_allows_allowlisted_hostname_with_public_resolution(monkeypatch):
    import socket

    def resolve_public(host, port, *, type):
        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("93.184.216.34", port or 443),
            )
        ]

    monkeypatch.setattr(socket, "getaddrinfo", resolve_public)
    policy = NetworkPolicy(allowed_hosts=frozenset({"agent.example"}))

    policy.validate("https://agent.example/mcp")


def test_network_policy_rejects_non_global_literal_ip():
    policy = NetworkPolicy(allowed_hosts=frozenset({"10.20.30.40"}))

    with pytest.raises(PermissionError, match="non-public"):
        policy.validate("https://10.20.30.40/mcp")


def test_network_policy_rejects_embedded_url_credentials():
    policy = NetworkPolicy(allowed_hosts=frozenset({"8.8.8.8"}))

    with pytest.raises(PermissionError, match="embedded credentials"):
        policy.validate("https://agent:secret@8.8.8.8/mcp")
