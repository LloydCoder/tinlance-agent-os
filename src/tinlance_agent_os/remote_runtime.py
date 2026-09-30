"""Local and remote agent runtime primitives for M20.

The runtime is a coordination layer. Agent Platform remains authoritative for
identity, capabilities, policy, approvals, consequential execution and evidence.
"""

from __future__ import annotations

import contextlib
import ipaddress
import os
import signal
import subprocess
import sqlite3
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse

from .contracts import AgentPlatformClient
from .store import StateStore
from .system import LocalSystemBackend
from .observability import telemetry


def utc_now() -> datetime:
    return datetime.now(UTC)


class RemoteRuntimeError(RuntimeError):
    pass


class EndpointState(StrEnum):
    ENROLLED = "enrolled"
    HEALTHY = "healthy"
    DRAINING = "draining"
    OFFLINE = "offline"
    DISCONNECTED = "disconnected"


class RemoteTaskState(StrEnum):
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class ResourceLimits:
    cpu_seconds: int = 60
    memory_bytes: int = 512 * 1024 * 1024
    max_processes: int = 16

    def __post_init__(self) -> None:
        if self.cpu_seconds <= 0 or self.memory_bytes <= 0 or self.max_processes <= 0:
            raise ValueError("resource limits must be positive")


@dataclass(frozen=True, slots=True)
class NetworkPolicy:
    allowed_hosts: frozenset[str] = frozenset()
    allow_private_addresses: bool = False

    def validate(self, address: str) -> None:
        parsed = urlparse(address)
        if parsed.scheme not in {"https", "mcp"}:
            raise PermissionError("remote endpoint must use an approved secure scheme")
        if not parsed.hostname:
            raise PermissionError("remote endpoint hostname is required")
        hostname = parsed.hostname.lower()
        if self.allowed_hosts and hostname not in self.allowed_hosts:
            raise PermissionError("remote endpoint is not allowed by network policy")
        try:
            resolved = ipaddress.ip_address(hostname)
        except ValueError:
            return
        if not self.allow_private_addresses and (
            resolved.is_private or resolved.is_loopback or resolved.is_link_local
        ):
            raise PermissionError("private remote address is denied")


@dataclass(frozen=True, slots=True)
class FilesystemBinding:
    root: Path

    def backend(self, *, allowed_commands: frozenset[str] = frozenset()) -> LocalSystemBackend:
        root = self.root.resolve()
        if not root.exists() or not root.is_dir():
            raise ValueError("filesystem binding root must be an existing directory")
        return LocalSystemBackend(root=root, allowed_commands=allowed_commands)


@dataclass(frozen=True, slots=True)
class EndpointIdentity:
    endpoint_id: str
    fingerprint: str
    attestation: str


class EndpointAuthenticator(Protocol):
    def verify(self, identity: EndpointIdentity, workspace_id: str) -> bool: ...


class RemoteTransport(Protocol):
    def assign(
        self,
        *,
        endpoint: EndpointIdentity,
        task_id: str,
        run_id: str,
        trace_id: str,
        idempotency_key: str,
    ) -> Mapping[str, object]: ...

    def cancel(
        self,
        *,
        endpoint: EndpointIdentity,
        task_id: str,
        run_id: str,
        trace_id: str,
    ) -> Mapping[str, object]: ...


class MCPClient(Protocol):
    def request(
        self,
        *,
        method: str,
        name: str,
        arguments: Mapping[str, object],
        metadata: Mapping[str, object],
    ) -> Mapping[str, object]: ...


@dataclass(frozen=True, slots=True)
class MCPRemoteTransport:
    """MCP adapter; MCP remains the wire protocol rather than a Tinlance RPC dialect."""

    client: MCPClient
    protocol_version: str = "2026-07-28"

    def assign(
        self,
        *,
        endpoint: EndpointIdentity,
        task_id: str,
        run_id: str,
        trace_id: str,
        idempotency_key: str,
    ) -> Mapping[str, object]:
        return self.client.request(
            method="tools/call",
            name="tinlance.agent.assign",
            arguments={
                "task_id": task_id,
                "run_id": run_id,
                "trace_id": trace_id,
                "idempotency_key": idempotency_key,
            },
            metadata={
                "mcp_protocol_version": self.protocol_version,
                "endpoint_id": endpoint.endpoint_id,
                "tinlance.trace_id": trace_id,
            },
        )

    def cancel(
        self,
        *,
        endpoint: EndpointIdentity,
        task_id: str,
        run_id: str,
        trace_id: str,
    ) -> Mapping[str, object]:
        return self.client.request(
            method="tools/call",
            name="tinlance.agent.cancel",
            arguments={
                "task_id": task_id,
                "run_id": run_id,
                "trace_id": trace_id,
            },
            metadata={
                "mcp_protocol_version": self.protocol_version,
                "endpoint_id": endpoint.endpoint_id,
                "traceparent": trace_id,
            },
        )


@dataclass(frozen=True, slots=True)
class RemoteEndpoint:
    identity: EndpointIdentity
    workspace_id: str
    tenant_id: str
    address: str
    protocol: str
    protocol_version: str
    state: EndpointState
    last_heartbeat: datetime


@dataclass(frozen=True, slots=True)
class RemoteTask:
    task_id: str
    workspace_id: str
    endpoint_id: str
    platform_run_id: str
    idempotency_key: str
    trace_id: str
    state: RemoteTaskState


@dataclass(slots=True)
class LocalProcessSupervisor:
    limits: ResourceLimits
    children: dict[str, subprocess.Popen[bytes]]

    def __init__(self, limits: ResourceLimits) -> None:
        self.limits = limits
        self.children = {}

    def start(
        self,
        process_id: str,
        argv: Sequence[str],
        *,
        cwd: Path,
        environment: Mapping[str, str] | None = None,
    ) -> int:
        if process_id in self.children:
            raise RemoteRuntimeError("process is already supervised")
        if not argv or any(not value or "\\x00" in value for value in argv):
            raise ValueError("invalid process arguments")
        if len(self.children) >= self.limits.max_processes:
            raise RemoteRuntimeError("process limit reached")
        cwd = cwd.resolve()
        if not cwd.is_dir():
            raise ValueError("process working directory must exist")
        env = {"PATH": "/usr/bin:/bin"}
        if environment:
            for key, value in environment.items():
                if key == "PATH" or key.startswith("LD_") or key.startswith("PYTHON"):
                    raise PermissionError("unsafe process environment variable")
                if not key or "\x00" in key or "\x00" in value:
                    raise ValueError("invalid process environment")
                if key not in {"LANG", "LC_ALL", "LC_CTYPE", "LC_MESSAGES", "TZ"}:
                    raise PermissionError("process environment variable is not allowlisted")
                env[key] = value
        preexec = self._resource_limiter()
        process = subprocess.Popen(
            list(argv),
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            start_new_session=True,
            preexec_fn=preexec,
        )
        self.children[process_id] = process
        return process.pid

    def poll(self, process_id: str) -> int | None:
        process = self.children.get(process_id)
        if process is None:
            raise RemoteRuntimeError("process is not supervised")
        code = process.poll()
        if code is not None:
            self.children.pop(process_id, None)
        return code

    def terminate(self, process_id: str) -> None:
        process = self.children.pop(process_id, None)
        if process is None:
            return
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=2)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            with contextlib.suppress(subprocess.TimeoutExpired):
                process.wait(timeout=1)

    def _resource_limiter(self) -> Callable[[], None] | None:
        try:
            import resource
        except ImportError:
            return None

        limits = self.limits

        def limit() -> None:
            resource.setrlimit(resource.RLIMIT_CPU, (limits.cpu_seconds, limits.cpu_seconds))
            resource.setrlimit(resource.RLIMIT_AS, (limits.memory_bytes, limits.memory_bytes))
            resource.setrlimit(resource.RLIMIT_NPROC, (limits.max_processes, limits.max_processes))

        return limit


@dataclass(slots=True)
class RemoteRuntime:
    store: StateStore
    platform: AgentPlatformClient
    authenticator: EndpointAuthenticator
    transport: RemoteTransport
    network_policy: NetworkPolicy
    heartbeat_timeout_seconds: float = 90.0

    def __post_init__(self) -> None:
        if self.heartbeat_timeout_seconds <= 0:
            raise ValueError("heartbeat timeout must be positive")

    def enroll(
        self,
        *,
        workspace_id: str,
        tenant_id: str,
        identity: EndpointIdentity,
        address: str,
        protocol: str = "mcp",
        protocol_version: str = "2026-07-28",
    ) -> RemoteEndpoint:
        if not workspace_id.strip() or not tenant_id.strip():
            raise ValueError("workspace and tenant are required")
        if not self.authenticator.verify(identity, workspace_id):
            raise PermissionError("remote endpoint identity verification failed")
        self.network_policy.validate(address)
        if protocol.lower() != "mcp":
            raise PermissionError("remote runtime requires MCP-compatible transport")
        now = utc_now()
        endpoint = RemoteEndpoint(
            identity=identity,
            workspace_id=workspace_id,
            tenant_id=tenant_id,
            address=address,
            protocol=protocol,
            protocol_version=protocol_version,
            state=EndpointState.ENROLLED,
            last_heartbeat=now,
        )
        self.store.upsert_remote_endpoint(
            (
                identity.endpoint_id,
                workspace_id,
                tenant_id,
                identity.fingerprint,
                address,
                protocol,
                protocol_version,
                endpoint.state.value,
                now.isoformat(),
                now.isoformat(),
                now.isoformat(),
            )
        )
        return endpoint

    def heartbeat(self, identity: EndpointIdentity) -> RemoteEndpoint:
        row = self._endpoint_row(identity.endpoint_id)
        self._verify_endpoint(row, identity)
        now = utc_now()
        state = EndpointState.HEALTHY
        self.store.upsert_remote_endpoint(
            (
                identity.endpoint_id,
                str(row["workspace_id"]),
                str(row["tenant_id"]),
                identity.fingerprint,
                str(row["address"]),
                str(row["protocol"]),
                str(row["protocol_version"]),
                state.value,
                now.isoformat(),
                str(row["enrolled_at"]),
                now.isoformat(),
            )
        )
        return self._endpoint(identity.endpoint_id)

    def mark_unhealthy(self, *, now: datetime | None = None) -> int:
        now = now or utc_now()
        cutoff = now.timestamp() - self.heartbeat_timeout_seconds
        changed = 0
        for row in self.store.query(
            "SELECT * FROM remote_endpoints WHERE state IN (?,?)",
            (EndpointState.ENROLLED.value, EndpointState.HEALTHY.value),
        ):
            heartbeat = datetime.fromisoformat(str(row["last_heartbeat"])).timestamp()
            if heartbeat < cutoff:
                self.store.upsert_remote_endpoint(
                    (
                        str(row["endpoint_id"]),
                        str(row["workspace_id"]),
                        str(row["tenant_id"]),
                        str(row["endpoint_fingerprint"]),
                        str(row["address"]),
                        str(row["protocol"]),
                        str(row["protocol_version"]),
                        EndpointState.OFFLINE.value,
                        str(row["last_heartbeat"]),
                        str(row["enrolled_at"]),
                        now.isoformat(),
                    )
                )
                changed += 1
        return changed

    def drain(self, endpoint_id: str) -> RemoteEndpoint:
        row = self._endpoint_row(endpoint_id)
        now = utc_now().isoformat()
        self.store.upsert_remote_endpoint(
            (
                endpoint_id,
                str(row["workspace_id"]),
                str(row["tenant_id"]),
                str(row["endpoint_fingerprint"]),
                str(row["address"]),
                str(row["protocol"]),
                str(row["protocol_version"]),
                EndpointState.DRAINING.value,
                str(row["last_heartbeat"]),
                str(row["enrolled_at"]),
                now,
            )
        )
        return self._endpoint(endpoint_id)

    def disconnect(self, endpoint_id: str) -> RemoteEndpoint:
        row = self._endpoint_row(endpoint_id)
        now = utc_now().isoformat()
        self.store.upsert_remote_endpoint(
            (
                endpoint_id,
                str(row["workspace_id"]),
                str(row["tenant_id"]),
                str(row["endpoint_fingerprint"]),
                str(row["address"]),
                str(row["protocol"]),
                str(row["protocol_version"]),
                EndpointState.DISCONNECTED.value,
                str(row["last_heartbeat"]),
                str(row["enrolled_at"]),
                now,
            )
        )
        return self._endpoint(endpoint_id)

    def assign(
        self,
        *,
        endpoint_id: str,
        task_id: str,
        workspace_id: str,
        agent_id: str,
        intent: str,
        trace_id: str,
    ) -> RemoteTask:
        endpoint = self._endpoint(endpoint_id)
        if endpoint.workspace_id != workspace_id:
            raise PermissionError("remote endpoint workspace mismatch")
        if endpoint.state is not EndpointState.HEALTHY:
            raise RemoteRuntimeError("remote endpoint is not healthy")
        if not intent.strip():
            raise ValueError("task intent is required")
        idempotency_key = f"remote:{task_id}"
        with telemetry().span(
            "agentos.remote.assign",
            {
                "agentos.task.id": task_id,
                "gen_ai.agent.id": agent_id,
                "agentos.remote.endpoint_id": endpoint_id,
            },
        ) as span:
            run = self.platform.create_run(
                task_id=task_id,
                agent_id=agent_id,
                intent=intent,
                idempotency_key=idempotency_key,
            )
            span.set_attribute("agentos.platform.run_id", run.run_id)
        self.transport.assign(
            endpoint=endpoint.identity,
            task_id=task_id,
            run_id=run.run_id,
            trace_id=trace_id,
            idempotency_key=idempotency_key,
        )
        now = utc_now().isoformat()
        self.store.upsert_remote_task(
            (
                task_id,
                workspace_id,
                endpoint_id,
                run.run_id,
                idempotency_key,
                RemoteTaskState.ASSIGNED.value,
                trace_id,
                now,
                now,
            )
        )
        return RemoteTask(
            task_id=task_id,
            workspace_id=workspace_id,
            endpoint_id=endpoint_id,
            platform_run_id=run.run_id,
            idempotency_key=idempotency_key,
            trace_id=trace_id,
            state=RemoteTaskState.ASSIGNED,
        )

    def cancel(self, task_id: str) -> RemoteTask:
        row = self._remote_task_row(task_id)
        endpoint = self._endpoint(str(row["endpoint_id"]))
        if endpoint.state is EndpointState.DISCONNECTED:
            raise RemoteRuntimeError("remote endpoint is disconnected")
        result = self.transport.cancel(
            endpoint=endpoint.identity,
            task_id=task_id,
            run_id=str(row["platform_task_id"]),
            trace_id=str(row["trace_id"]),
        )
        del result
        with telemetry().span(
            "agentos.remote.cancel",
            {
                "agentos.task.id": task_id,
                "agentos.remote.endpoint_id": str(row["endpoint_id"]),
                "agentos.platform.run_id": str(row["platform_task_id"]),
            },
        ):
            self.platform.cancel_run(run_id=str(row["platform_task_id"]))
        now = utc_now().isoformat()
        self.store.upsert_remote_task(
            (
                str(row["task_id"]),
                str(row["workspace_id"]),
                str(row["endpoint_id"]),
                str(row["platform_task_id"]),
                str(row["idempotency_key"]),
                RemoteTaskState.CANCELLED.value,
                str(row["trace_id"]),
                str(row["assigned_at"]),
                now,
            )
        )
        return RemoteTask(
            task_id=str(row["task_id"]),
            workspace_id=str(row["workspace_id"]),
            endpoint_id=str(row["endpoint_id"]),
            platform_run_id=str(row["platform_task_id"]),
            idempotency_key=str(row["idempotency_key"]),
            trace_id=str(row["trace_id"]),
            state=RemoteTaskState.CANCELLED,
        )

    def reconnect(self, identity: EndpointIdentity) -> RemoteEndpoint:
        return self.heartbeat(identity)

    def route(self, workspace_id: str) -> tuple[RemoteEndpoint, ...]:
        self.mark_unhealthy()
        rows = self.store.query(
            "SELECT * FROM remote_endpoints WHERE workspace_id=? AND state=? "
            "ORDER BY last_heartbeat DESC, endpoint_id",
            (workspace_id, EndpointState.HEALTHY.value),
        )
        return tuple(self._endpoint_from_row(row) for row in rows)

    def _endpoint(self, endpoint_id: str) -> RemoteEndpoint:
        return self._endpoint_from_row(self._endpoint_row(endpoint_id))

    def _endpoint_row(self, endpoint_id: str) -> sqlite3.Row:
        rows = self.store.query(
            "SELECT * FROM remote_endpoints WHERE endpoint_id=?",
            (endpoint_id,),
        )
        if not rows:
            raise RemoteRuntimeError("remote endpoint is not enrolled")
        return rows[0]

    def _remote_task_row(self, task_id: str) -> sqlite3.Row:
        rows = self.store.query("SELECT * FROM remote_tasks WHERE task_id=?", (task_id,))
        if not rows:
            raise RemoteRuntimeError("remote task is not assigned")
        return rows[0]

    def _verify_endpoint(self, row: sqlite3.Row, identity: EndpointIdentity) -> None:
        if str(row["endpoint_fingerprint"]) != identity.fingerprint:
            raise PermissionError("remote endpoint fingerprint mismatch")
        if not self.authenticator.verify(identity, str(row["workspace_id"])):
            raise PermissionError("remote endpoint authentication failed")

    @staticmethod
    def _endpoint_from_row(row: sqlite3.Row) -> RemoteEndpoint:
        return RemoteEndpoint(
            identity=EndpointIdentity(
                str(row["endpoint_id"]),
                str(row["endpoint_fingerprint"]),
                "",
            ),
            workspace_id=str(row["workspace_id"]),
            tenant_id=str(row["tenant_id"]),
            address=str(row["address"]),
            protocol=str(row["protocol"]),
            protocol_version=str(row["protocol_version"]),
            state=EndpointState(str(row["state"])),
            last_heartbeat=datetime.fromisoformat(str(row["last_heartbeat"])),
        )
