"""Viewer 会话管理：端口分配、子进程启动、健康检查。"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import uuid
from typing import Dict, List, Optional
from urllib.error import URLError
from urllib.request import urlopen

from discoverse import DISCOVERSE_ROOT_DIR

from web_viewer.launcher.catalog.scanner import check_compatibility, scan_gs_assets
from web_viewer.launcher.session.models import SessionConfig, SessionRecord

_REPO_ROOT = DISCOVERSE_ROOT_DIR
_SERVER_SCRIPT = os.path.join(_REPO_ROOT, "web_viewer", "server.py")
_SESSIONS_DIR = os.path.join(_REPO_ROOT, "models", "mjcf", "tmp", "sessions")
_PORT_MIN = 8765
_PORT_MAX = 8799
_HEALTH_TIMEOUT_S = 90.0
_HEALTH_POLL_S = 0.5


class SessionManager:
    def __init__(self, web_host: str = "0.0.0.0", public_host: Optional[str] = None) -> None:
        self.web_host = web_host
        self.public_host = public_host or "127.0.0.1"
        self._sessions: Dict[str, SessionRecord] = {}
        self._used_ports: set[int] = set()
        os.makedirs(_SESSIONS_DIR, exist_ok=True)

    def list_sessions(self) -> List[SessionRecord]:
        self._reap_exited()
        return list(self._sessions.values())

    def get_session(self, session_id: str) -> Optional[SessionRecord]:
        self._reap_exited()
        return self._sessions.get(session_id)

    def _allocate_port(self) -> int:
        for port in range(_PORT_MIN, _PORT_MAX + 1):
            if port not in self._used_ports:
                self._used_ports.add(port)
                return port
        raise RuntimeError(f"无可用端口（{_PORT_MIN}-{_PORT_MAX} 已占满）")

    def _release_port(self, port: int) -> None:
        self._used_ports.discard(port)

    def _build_gs_urls(self, config: SessionConfig) -> List[str]:
        if not config.enable_gs:
            return []
        assets = {a["id"]: a for a in scan_gs_assets()}
        urls: List[str] = []
        scene = assets.get(config.gs_scene)
        if scene and scene.get("url"):
            urls.append(scene["url"])
        for asset_id in config.gs_assets:
            entry = assets.get(asset_id)
            if entry and entry.get("url") and entry["url"] not in urls:
                urls.append(entry["url"])
        return urls

    def _viewer_url(self, port: int, config: SessionConfig) -> str:
        params = [f"robot={config.robot}"]
        if config.enable_gs:
            gs_urls = self._build_gs_urls(config)
            if gs_urls:
                params.append(f"splats={','.join(gs_urls)}")
            params.append("gs=1")
            ox, oy, oz = (config.gs_offset + [0.0, 0.0, 0.0])[:3]
            if any(abs(v) > 1e-9 for v in (ox, oy, oz)):
                params.append(f"gsOffset={ox},{oy},{oz}")
        else:
            params.append("render=mesh")
        query = "&".join(params)
        return f"http://{self.public_host}:{port}/?{query}"

    def create_session(self, config: SessionConfig) -> SessionRecord:
        compat = check_compatibility(config.robot, config.task)
        if not compat.get("ok"):
            raise ValueError(compat.get("error") or "make_env 兼容性检查失败")

        config.xml_path = compat["xml_path"]
        config.runtime = compat["runtime"]
        session_id = uuid.uuid4().hex[:8]
        config.session_id = session_id
        port = self._allocate_port()

        config_path = os.path.join(_SESSIONS_DIR, f"{session_id}.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config.to_dict(), f, ensure_ascii=False, indent=2)

        cmd = [
            sys.executable,
            _SERVER_SCRIPT,
            "--session-config",
            config_path,
            "--web-host",
            self.web_host,
            "--web-port",
            str(port),
        ]

        proc = subprocess.Popen(
            cmd,
            cwd=_REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        record = SessionRecord(
            session_id=session_id,
            config=config,
            port=port,
            pid=proc.pid,
            status="starting",
            viewer_url=self._viewer_url(port, config),
            created_at=time.time(),
        )
        self._sessions[session_id] = record

        if self._wait_until_ready(port):
            record.status = "running"
            return record

        record.status = "failed"
        record.error = "Viewer 健康检查超时"
        self.stop_session(session_id)
        raise RuntimeError(record.error)

    def _wait_until_ready(self, port: int) -> bool:
        deadline = time.time() + _HEALTH_TIMEOUT_S
        url = f"http://127.0.0.1:{port}/api/config"
        while time.time() < deadline:
            try:
                with urlopen(url, timeout=2.0) as resp:
                    if resp.status == 200:
                        return True
            except (URLError, OSError, TimeoutError):
                pass
            time.sleep(_HEALTH_POLL_S)
        return False

    def stop_session(self, session_id: str) -> bool:
        record = self._sessions.get(session_id)
        if record is None:
            return False

        if record.pid:
            try:
                os.kill(record.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

        self._release_port(record.port)
        record.status = "stopped"
        record.pid = None
        config_path = os.path.join(_SESSIONS_DIR, f"{session_id}.json")
        if os.path.isfile(config_path):
            try:
                os.remove(config_path)
            except OSError:
                pass
        return True

    def stop_all(self) -> int:
        count = 0
        for session_id in list(self._sessions.keys()):
            if self.stop_session(session_id):
                count += 1
        return count

    def _reap_exited(self) -> None:
        for record in self._sessions.values():
            if record.pid is None or record.status != "running":
                continue
            try:
                os.kill(record.pid, 0)
            except ProcessLookupError:
                record.status = "stopped"
                record.pid = None
                self._release_port(record.port)
