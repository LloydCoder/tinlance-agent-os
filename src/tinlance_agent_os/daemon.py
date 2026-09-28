"""Local Agent OS control daemon over a Unix domain socket."""
from __future__ import annotations
import json, os, socket, threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

@dataclass(frozen=True, slots=True)
class DaemonConfig:
    socket_path: Path
    max_request_bytes: int = 1_048_576
    backlog: int = 32

class AgentOSDaemon:
    def __init__(self, config: DaemonConfig, handler: Callable[[dict[str, object]], dict[str, object]]) -> None:
        self.config, self.handler = config, handler
        self._stop = threading.Event()
        self._server: socket.socket | None = None
    def serve_forever(self) -> None:
        self.config.socket_path.parent.mkdir(parents=True, exist_ok=True)
        try: self.config.socket_path.unlink()
        except FileNotFoundError: pass
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server = server
        server.bind(str(self.config.socket_path)); os.chmod(self.config.socket_path, 0o600)
        server.listen(self.config.backlog); server.settimeout(0.5)
        try:
            while not self._stop.is_set():
                try: conn, _ = server.accept()
                except TimeoutError: continue
                threading.Thread(target=self._handle, args=(conn,), daemon=True).start()
        finally:
            server.close()
            try: self.config.socket_path.unlink()
            except FileNotFoundError: pass
    def _handle(self, conn: socket.socket) -> None:
        with conn:
            conn.settimeout(5)
            raw = conn.recv(self.config.max_request_bytes + 1)
            if len(raw) > self.config.max_request_bytes:
                self._send(conn, {"ok":False,"error":"request_too_large"}); return
            try:
                request = json.loads(raw.decode("utf-8"))
                if not isinstance(request, dict): raise ValueError
                response = self.handler(request)
                self._send(conn, {"ok":True,"result":response})
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                self._send(conn, {"ok":False,"error":"invalid_request","detail":str(exc)})
            except Exception:
                self._send(conn, {"ok":False,"error":"internal_error"})
    @staticmethod
    def _send(conn: socket.socket, response: dict[str, object]) -> None:
        conn.sendall((json.dumps(response,separators=(",",":"))+"\n").encode())
    def shutdown(self) -> None:
        self._stop.set()
        if self._server: self._server.close()
