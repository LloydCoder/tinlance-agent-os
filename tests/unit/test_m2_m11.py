from __future__ import annotations

import hashlib
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import struct
import socket
import threading
import time

from tinlance_agent_os.applications import (
    AgentManifest,
    ApplicationRegistry,
    CapabilityRequest,
)
from tinlance_agent_os.client import ReferenceAgentPlatformClient
from tinlance_agent_os.daemon import AgentOSDaemon, DaemonConfig
from tinlance_agent_os.daemon_service import LocalOSService
from tinlance_agent_os.distribution import ReleaseArtifact, UpdateManager, UpdateState
from tinlance_agent_os.extensions import ExtensionContext, ExtensionManager
from tinlance_agent_os.enterprise import FleetRegistry, FleetState, RemoteAgent
from tinlance_agent_os.memory import DataClassification, MemoryStore
from tinlance_agent_os.shell import AgentShell, ShellCommand
from tinlance_agent_os.store import StateStore
from tinlance_agent_os.system import LocalSystemBackend
from tinlance_agent_os.workflow import (
    WorkflowDefinition,
    WorkflowEngine,
    WorkflowState,
    WorkflowStep,
)


def test_workflow_validation_and_ready_steps() -> None:
    definition = WorkflowDefinition(
        "w",
        "ws",
        (WorkflowStep("a", "one"), WorkflowStep("b", "two", ("a",))),
    )
    engine = WorkflowEngine()
    assert [s.step_id for s in engine.ready_steps(definition, set())] == ["a"]
    assert [s.step_id for s in engine.ready_steps(definition, {"a"})] == ["b"]
    bad = WorkflowDefinition(
        "w",
        "ws",
        (WorkflowStep("a", "x", ("b",)), WorkflowStep("b", "y", ("a",))),
    )
    try:
        engine.validate(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("cycle should be rejected")


def test_store_service_and_memory() -> None:
    with TemporaryDirectory() as directory:
        store = StateStore(Path(directory) / "state.db")
        service = LocalOSService(store, ReferenceAgentPlatformClient())
        workspace = service.create_workspace("u")
        session = service.create_session(workspace.workspace_id, "u", "a")
        task = service.create_task(
            workspace.workspace_id,
            session.session_id,
            "a",
            "do",
        )
        assert service.dispatch(task).task_id == task.task_id
        item = MemoryStore(store).put(
            workspace.workspace_id,
            "session",
            DataClassification.INTERNAL,
            "hello",
        )
        found = MemoryStore(store).search(workspace.workspace_id, "session", "hell")
        assert found[0].memory_id == item.memory_id


def test_manifest_extension_and_system_boundary() -> None:
    manifest = AgentManifest(
        "app",
        "App",
        "1.0",
        "0.1",
        "run",
        (CapabilityRequest("read", "needed"),),
    )
    registry = ApplicationRegistry({})
    registry.install(manifest)
    registry.enable("app")

    class ExtensionDouble:
        def start(self, context: ExtensionContext) -> None:
            context.require("read")

        def stop(self) -> None:
            return

    manager = ExtensionManager({})
    manager.load(manifest, ExtensionDouble(), frozenset({"read"}))
    manager.unload("app")

    with TemporaryDirectory() as directory:
        backend = LocalSystemBackend(Path(directory))
        backend.write_file(Path("a"), b"x")
        assert backend.read_file(Path("a")) == b"x"


def test_update_integrity_and_rollback() -> None:
    data = b"release"
    digest = hashlib.sha256(data).hexdigest()
    artifact = ReleaseArtifact(
        "0.2.0",
        digest,
        len(data),
        "https://example.invalid/a",
    )
    manager = UpdateManager()
    manager.stage(artifact, data)
    manager.apply("0.2.0")
    assert manager.active_version == "0.2.0"
    manager.rollback()
    assert manager.active_version == "0.1.0"
    assert manager.state is UpdateState.ROLLED_BACK


def test_daemon_protocol_handler() -> None:
    daemon = AgentOSDaemon(
        DaemonConfig(Path("/tmp/tinlance-test.sock")),
        lambda request: {"echo": request["x"]},
    )
    assert daemon.handler({"x": 1})["echo"] == 1


def test_shell_commands_and_system_policy() -> None:
    shell = AgentShell({})
    shell.register(ShellCommand("health", "Health", lambda: "ok"))
    assert shell.invoke("health") == "ok"
    try:
        shell.register(ShellCommand("health", "Duplicate", lambda: "bad"))
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate shell command should fail")
    with TemporaryDirectory() as directory:
        backend = LocalSystemBackend(Path(directory))
        try:
            backend.run_process(["echo", "ok"])
        except PermissionError:
            pass
        else:
            raise AssertionError("process execution should fail closed")
        backend = LocalSystemBackend(Path(directory), frozenset({"echo"}))
        assert backend.run_process(["echo", "ok"]) == 0


def test_application_disable_and_restricted_memory() -> None:
    manifest = AgentManifest("app", "App", "1", "0", "entry")
    registry = ApplicationRegistry({})
    registry.install(manifest)
    registry.disable("app")
    assert registry.items["app"][1].value == "disabled"
    with TemporaryDirectory() as directory:
        memory = MemoryStore(StateStore(Path(directory) / "state.db"))
        try:
            memory.put("ws", "scope", DataClassification.RESTRICTED, "secret")
        except PermissionError:
            pass
        else:
            raise AssertionError("restricted memory should fail closed")


def test_reference_client_validation_and_cancel() -> None:
    client = ReferenceAgentPlatformClient()
    try:
        client.create_run(task_id="", agent_id="a", intent="x")
    except ValueError:
        pass
    else:
        raise AssertionError("invalid run should fail")
    run = client.create_run(task_id="t", agent_id="a", intent="x")
    assert client.cancel_run(run_id=run.run_id).state == "cancelled"
    assert client.list_capabilities(agent_id="a")
    assert client.get_evidence(run_id=run.run_id)
    try:
        client.request_approval(run_id="", action="x")
    except ValueError:
        pass
    else:
        raise AssertionError("invalid approval should fail")


def test_distribution_failure_and_workflow_unknown_dependency() -> None:
    manager = UpdateManager()
    data = b"release"
    artifact = ReleaseArtifact(
        "0.2.0",
        hashlib.sha256(data).hexdigest(),
        len(data),
        "https://example.invalid/a",
    )
    try:
        manager.stage(artifact, b"bad")
    except ValueError:
        pass
    else:
        raise AssertionError("bad artifact should fail")
    try:
        WorkflowEngine().ready_steps(
            WorkflowDefinition("w", "ws", (WorkflowStep("a", "x"),)),
            {"missing"},
        )
    except ValueError:
        pass
    else:
        raise AssertionError("unknown completed step should fail")


def test_daemon_handler_protocol_paths() -> None:
    class Connection:
        def __init__(self, payload: bytes) -> None:
            self.payload = payload
            self.sent: list[bytes] = []

        def __enter__(self) -> Connection:
            return self

        def __exit__(self, *_args: object) -> None:
            return

        def settimeout(self, _value: float) -> None:
            return

        def recv(self, _size: int) -> bytes:
            payload, self.payload = self.payload, b""
            return payload

        def sendall(self, data: bytes) -> None:
            self.sent.append(data)

        def getsockopt(self, *_args: object) -> bytes:
            return struct.pack("3i", 0, os.getuid(), 0)

    daemon = AgentOSDaemon(
        DaemonConfig(Path("/tmp/unused.sock"), max_request_bytes=100),
        lambda request: {"ok": request["x"]},
    )
    oversized = Connection(b"x" * 101)
    daemon._handle(oversized)
    assert b"request_too_large" in oversized.sent[0]
    invalid = Connection(b"not-json")
    daemon._handle(invalid)
    assert b"invalid_request" in invalid.sent[0]
    valid = Connection(b'{"x":1}')
    daemon._handle(valid)
    assert b'"ok":true' in valid.sent[0]


def test_workflow_execution_lifecycle() -> None:
    definition = WorkflowDefinition(
        "w",
        "ws",
        (WorkflowStep("a", "one"), WorkflowStep("b", "two", ("a",))),
    )
    engine = WorkflowEngine()
    execution = engine.start(definition)
    assert execution.state is WorkflowState.RUNNING
    execution = engine.complete_step(definition, execution, "a")
    assert execution.completed == frozenset({"a"})
    execution = engine.complete_step(definition, execution, "b")
    assert execution.state is WorkflowState.COMPLETED


def test_system_rejects_absolute_executable_bypass() -> None:
    with TemporaryDirectory() as directory:
        backend = LocalSystemBackend(Path(directory), frozenset({"echo"}))
        try:
            backend.run_process(["/bin/echo", "ok"])
        except PermissionError:
            pass
        else:
            raise AssertionError("absolute executable bypass should fail")


def test_daemon_accepts_fragmented_line_protocol() -> None:
    class Connection:
        def __init__(self) -> None:
            self.parts = [b'{"x":', b"1}\n"]
            self.sent: list[bytes] = []

        def __enter__(self) -> Connection:
            return self

        def __exit__(self, *_args: object) -> None:
            return

        def settimeout(self, _value: float) -> None:
            return

        def recv(self, _size: int) -> bytes:
            return self.parts.pop(0) if self.parts else b""

        def sendall(self, data: bytes) -> None:
            self.sent.append(data)

        def getsockopt(self, *_args: object) -> bytes:
            return struct.pack("3i", 0, os.getuid(), 0)

    daemon = AgentOSDaemon(
        DaemonConfig(Path("/tmp/unused.sock"), max_request_bytes=100),
        lambda request: {"ok": request["x"]},
    )
    connection = Connection()
    daemon._handle(connection)
    assert b'"ok":true' in connection.sent[0]


def test_daemon_rejects_bad_peer_and_empty_request() -> None:
    class Connection:
        def __init__(self, payload: bytes, uid: int) -> None:
            self.payload = payload
            self.uid = uid
            self.sent: list[bytes] = []

        def __enter__(self) -> Connection:
            return self

        def __exit__(self, *_args: object) -> None:
            return

        def settimeout(self, _value: float) -> None:
            return

        def recv(self, _size: int) -> bytes:
            payload, self.payload = self.payload, b""
            return payload

        def sendall(self, data: bytes) -> None:
            self.sent.append(data)

        def getsockopt(self, *_args: object) -> bytes:
            return struct.pack("3i", 0, self.uid, 0)

    daemon = AgentOSDaemon(
        DaemonConfig(Path("/tmp/unused.sock")),
        lambda _request: {"ok": True},
    )
    forbidden = Connection(b"{}", os.getuid() + 1)
    daemon._handle(forbidden)
    assert b'"forbidden"' in forbidden.sent[0]
    empty = Connection(b"", os.getuid())
    daemon._handle(empty)
    assert b'"invalid_request"' in empty.sent[0]


def test_application_and_extension_rejection_paths() -> None:
    manifest = AgentManifest("app", "App", "1", "0", "entry")
    registry = ApplicationRegistry({})
    registry.install(manifest)
    registry.uninstall("app")
    try:
        registry.enable("app")
    except ValueError:
        pass
    else:
        raise AssertionError("uninstalled app should not enable")
    try:
        AgentManifest(
            "app",
            "App",
            "1",
            "0",
            "entry",
            (CapabilityRequest("x", "r"), CapabilityRequest("x", "r")),
        ).validate()
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate capability should fail")


def test_workflow_failure_and_cancel_paths() -> None:
    definition = WorkflowDefinition("w", "ws", (WorkflowStep("a", "one"),))
    engine = WorkflowEngine()
    execution = engine.start(definition)
    failed = engine.fail_step(definition, execution, "a")
    assert failed.state is WorkflowState.FAILED
    cancelled = engine.cancel(definition, execution)
    assert cancelled.state is WorkflowState.CANCELLED


def test_memory_and_remote_validation_paths() -> None:
    with TemporaryDirectory() as directory:
        memory = MemoryStore(StateStore(Path(directory) / "state.db"))
        try:
            memory.search("ws", "scope", "")
        except ValueError:
            pass
        else:
            raise AssertionError("empty memory query should fail")
    registry = FleetRegistry({})
    try:
        registry.register(RemoteAgent("a", "http://example.invalid", FleetState.ONLINE))
    except ValueError:
        pass
    else:
        raise AssertionError("insecure remote endpoint should fail")


def test_distribution_and_system_validation_paths() -> None:
    try:
        ReleaseArtifact("", "0" * 64, 0, "https://example.invalid/a")
    except ValueError:
        pass
    else:
        raise AssertionError("empty release version should fail")
    with TemporaryDirectory() as directory:
        backend = LocalSystemBackend(Path(directory))
        try:
            backend.run_process(["echo"], timeout=0)
        except ValueError:
            pass
        else:
            raise AssertionError("non-positive process timeout should fail")


def test_daemon_serves_real_unix_socket_and_shutdown() -> None:
    with TemporaryDirectory() as directory:
        socket_path = Path(directory) / "agentos.sock"
        daemon = AgentOSDaemon(
            DaemonConfig(socket_path, request_timeout_seconds=1),
            lambda request: {"echo": request["x"]},
        )
        thread = threading.Thread(target=daemon.serve_forever, daemon=True)
        thread.start()
        for _ in range(50):
            if socket_path.exists():
                break
            time.sleep(0.01)
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.connect(str(socket_path))
            client.sendall(b'{"x":1}\n')
            response = client.recv(1024)
        assert b'"echo":1' in response
        daemon.shutdown()
        thread.join(timeout=2)
        assert not thread.is_alive()


def test_local_service_validates_lifecycle_and_daemon_operations() -> None:
    with TemporaryDirectory() as directory:
        service = LocalOSService(
            StateStore(Path(directory) / "state.db"),
            ReferenceAgentPlatformClient(),
        )
        workspace = service.create_workspace("owner")
        session = service.create_session(workspace.workspace_id, "owner", "agent")
        task = service.create_task(
            workspace.workspace_id,
            session.session_id,
            "agent",
            "run",
        )
        run = service.dispatch(task)
        assert run.task_id == task.task_id
        assert service.handle({"operation": "health"})["ready"] is True
        assert service.handle({"operation": "principal"})["user_id"] == "reference-user"
        try:
            service.handle({})
        except ValueError:
            pass
        else:
            raise AssertionError("missing daemon operation should fail")
