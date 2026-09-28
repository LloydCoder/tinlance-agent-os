"""Local Agent OS control daemon over a Unix domain socket."""

from __future__ import annotations

import contextlib
import json
import os
import socket
import stat
import struct
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DaemonConfig:
    socket_path: Path
    max_request_bytes: int = 1_048_576
    backlog: int = 32
    request_timeout_seconds: float = 5.0
    recv_chunk_bytes: int = 65_536

    def __post_init__(self) -> None:
        if not self.socket_path.is_absolute():
            raise ValueError("socket_path must be absolute")
        if self.max_request_bytes <= 0 or self.backlog <= 0:
            raise ValueError("daemon limits must be positive")
        if self.request_timeout_seconds <= 0 or self.recv_chunk_bytes <= 0:
            raise ValueError("daemon timeouts and receive size must be positive")


class AgentOSDaemon:
    """Bounded local control plane; it never performs Platform authorization."""

    def __init__(
        self,
        config: DaemonConfig,
        handler: Callable[[dict[str, object]], dict[str, object]],
    ) -> None:
        self.config = config
        self.handler = handler
        self._stop = threading.Event()
        self._server: socket.socket | None = None

    def serve_forever(self) -> None:
        self.config.socket_path.parent.mkdir(parents=True, exist_ok=True)
        self._validate_socket_parent()
        with contextlib.suppress(FileNotFoundError):
            self.config.socket_path.unlink()
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server = server
        try:
            server.bind(str(self.config.socket_path))
            os.chmod(self.config.socket_path, 0o600)
            server.listen(self.config.backlog)
            server.settimeout(0.5)
            while not self._stop.is_set():
                try:
                    conn, _ = server.accept()
                except TimeoutError:
                    continue
                except OSError:
                    if self._stop.is_set():
                        break
                    raise
                threading.Thread(target=self._handle, args=(conn,), daemon=True).start()
        finally:
            with contextlib.suppress(OSError):
                server.close()
            self._server = None
            with contextlib.suppress(FileNotFoundError):
                self.config.socket_path.unlink()

    def _validate_socket_parent(self) -> None:
        parent = self.config.socket_path.parent
        metadata = parent.stat()
        if metadata.st_uid != os.getuid():
            raise PermissionError("daemon socket parent must be owned by the current user")
        if stat.S_ISLNK(metadata.st_mode) or metadata.st_mode & 0o022:
            raise PermissionError("daemon socket parent must not be group/other writable")

    def _handle(self, conn: socket.socket) -> None:
        with conn:
            conn.settimeout(self.config.request_timeout_seconds)
            try:
                self._verify_peer(conn)
                raw = self._recv_request(conn)
                request = json.loads(raw.decode("utf-8"))
                if not isinstance(request, dict):
                    raise ValueError("request must be an object")
                response = self.handler(request)
                if not isinstance(response, dict):
                    raise ValueError("handler response must be an object")
                self._send(conn, {"ok": True, "result": response})
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                self._send(conn, {"ok": False, "error": "invalid_request", "detail": str(exc)})
            except PermissionError:
                self._send(conn, {"ok": False, "error": "forbidden"})
            except TimeoutError:
                self._send(conn, {"ok": False, "error": "request_timeout"})
            except Exception:
                self._send(conn, {"ok": False, "error": "internal_error"})

    def _recv_request(self, conn: socket.socket) -> bytes:
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = conn.recv(min(self.config.recv_chunk_bytes, self.config.max_request_bytes + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > self.config.max_request_bytes:
                self._send(conn, {"ok": False, "error": "request_too_large"})
                raise ValueError("request exceeds configured limit")
            if b"\n" in chunk:
                break
        raw = b"".join(chunks).split(b"\n", 1)[0]
        if not raw:
            raise ValueError("request is empty")
        return raw

    @staticmethod
    def _verify_peer(conn: socket.socket) -> None:
        if not hasattr(socket, "SO_PEERCRED"):
            return
        raw = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
        if len(raw) != 12:
            raise PermissionError("invalid peer credentials")
        _, uid, _ = struct.unpack("3i", raw)
        if uid != os.getuid():
            raise PermissionError("local daemon peer is not the owning user")

    @staticmethod
    def _send(conn: socket.socket, response: dict[str, object]) -> None:
        conn.sendall((json.dumps(response, separators=(",", ":")) + "\n").encode("utf-8"))

    def shutdown(self) -> None:
        self._stop.set()
        server = self._server
        if server is not None:
            with contextlib.suppress(OSError):
                server.close()
