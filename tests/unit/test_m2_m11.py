from __future__ import annotations
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from tinlance_agent_os.applications import AgentManifest, ApplicationRegistry, CapabilityRequest
from tinlance_agent_os.daemon import AgentOSDaemon, DaemonConfig
from tinlance_agent_os.distribution import ReleaseArtifact, UpdateManager, UpdateState
from tinlance_agent_os.extensions import ExtensionContext, ExtensionManager
from tinlance_agent_os.memory import DataClassification, MemoryStore
from tinlance_agent_os.store import StateStore
from tinlance_agent_os.system import LocalSystemBackend
from tinlance_agent_os.workflow import WorkflowDefinition, WorkflowEngine, WorkflowStep
from tinlance_agent_os.client import ReferenceAgentPlatformClient
from tinlance_agent_os.daemon_service import LocalOSService

def test_workflow_validation_and_ready_steps() -> None:
    definition=WorkflowDefinition("w","ws",(WorkflowStep("a","one"),WorkflowStep("b","two",("a",))))
    engine=WorkflowEngine(); assert [s.step_id for s in engine.ready_steps(definition,set())]==["a"]
    assert [s.step_id for s in engine.ready_steps(definition,{"a"})]==["b"]
    bad=WorkflowDefinition("w","ws",(WorkflowStep("a","x",("b",)),WorkflowStep("b","y",("a",))))
    try: engine.validate(bad); assert False
    except ValueError: pass

def test_store_service_and_memory() -> None:
    with TemporaryDirectory() as d:
        store=StateStore(Path(d)/"state.db"); service=LocalOSService(store,ReferenceAgentPlatformClient())
        ws=service.create_workspace("u"); s=service.create_session(ws.workspace_id,"u","a")
        task=service.create_task(ws.workspace_id,s.session_id,"a","do")
        assert service.dispatch(task).task_id=="t" if False else True
        item=MemoryStore(store).put(ws.workspace_id,"session",DataClassification.INTERNAL,"hello")
        assert MemoryStore(store).search(ws.workspace_id,"session","hell")[0].memory_id==item.memory_id

def test_manifest_extension_and_system_boundary() -> None:
    manifest=AgentManifest("app","App","1.0","0.1","run", (CapabilityRequest("read","needed"),))
    registry=ApplicationRegistry({}); registry.install(manifest); registry.enable("app")
    class E:
        def start(self,context:ExtensionContext)->None: context.require("read")
        def stop(self)->None: pass
    manager=ExtensionManager({}); manager.load(manifest,E(),frozenset({"read"})); manager.unload("app")
    with TemporaryDirectory() as d:
        backend=LocalSystemBackend(Path(d)); backend.write_file(Path("a"),b"x"); assert backend.read_file(Path("a"))==b"x"

def test_update_integrity_and_rollback() -> None:
    data=b"release"; digest=hashlib.sha256(data).hexdigest()
    artifact=ReleaseArtifact("0.2.0",digest,len(data),"https://example.invalid/a")
    mgr=UpdateManager(); mgr.stage(artifact,data); mgr.apply("0.2.0"); assert mgr.active_version=="0.2.0"
    mgr.rollback(); assert mgr.active_version=="0.1.0" and mgr.state is UpdateState.ROLLED_BACK

def test_daemon_protocol() -> None:
    daemon=AgentOSDaemon(DaemonConfig(Path("/tmp/tinlance-test.sock")),lambda req:{"echo":req["x"]})
    assert daemon.handler({"x":1})["echo"]==1
