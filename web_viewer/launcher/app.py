#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DISCOVERSE Web Viewer Launcher — FastAPI 入口。"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from web_viewer.launcher.catalog.scanner import check_compatibility, scan_catalog
from web_viewer.launcher.session.manager import SessionManager
from web_viewer.launcher.session.models import SessionConfig

_LAUNCHER_DIR = os.path.dirname(os.path.abspath(__file__))
_STATIC_DIR = os.path.join(_LAUNCHER_DIR, "static")

app = FastAPI(title="DISCOVERSE Web Viewer Launcher", version="0.1.0")
_session_manager: Optional[SessionManager] = None

if os.path.isdir(_STATIC_DIR):
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="launcher-static")


class CreateSessionBody(BaseModel):
    robot: str = Field(..., pattern="^(airbot_play|ur5e)$")
    task: str
    enable_gs: bool = False
    gs_scene: str = "lab3"
    gs_assets: List[str] = Field(default_factory=list)
    gs_offset: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    randomize: bool = False
    sync: bool = False


def _manager() -> SessionManager:
    if _session_manager is None:
        raise HTTPException(status_code=503, detail="Launcher 尚未初始化")
    return _session_manager


@app.get("/")
@app.get("/launcher")
async def launcher_page() -> HTMLResponse:
    index_path = os.path.join(_STATIC_DIR, "index.html")
    if not os.path.isfile(index_path):
        return HTMLResponse("<p>Missing launcher static/index.html</p>", status_code=500)
    with open(index_path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/api/catalog")
async def api_catalog() -> Dict[str, Any]:
    return scan_catalog()


@app.get("/api/catalog/compatibility")
async def api_compatibility(robot: str, task: str) -> Dict[str, Any]:
    return check_compatibility(robot, task)


@app.get("/api/sessions")
async def api_list_sessions() -> Dict[str, Any]:
    sessions = _manager().list_sessions()
    return {
        "sessions": [s.to_dict() for s in sessions if s.status in ("starting", "running")],
    }


@app.get("/api/sessions/{session_id}")
async def api_get_session(session_id: str) -> Dict[str, Any]:
    record = _manager().get_session(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    return record.to_dict()


@app.post("/api/sessions")
async def api_create_session(body: CreateSessionBody) -> Dict[str, Any]:
    config = SessionConfig(
        robot=body.robot,  # type: ignore[arg-type]
        task=body.task,
        enable_gs=body.enable_gs,
        gs_scene=body.gs_scene,
        gs_assets=body.gs_assets,
        gs_offset=body.gs_offset,
        randomize=body.randomize,
        sync=body.sync,
    )
    try:
        record = _manager().create_session(config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return record.to_dict()


@app.delete("/api/sessions/{session_id}")
async def api_delete_session(session_id: str) -> Dict[str, Any]:
    if not _manager().stop_session(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"ok": True, "session_id": session_id}


@app.delete("/api/sessions")
async def api_delete_all_sessions() -> Dict[str, Any]:
    count = _manager().stop_all()
    return {"ok": True, "stopped": count}


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="DISCOVERSE Web Viewer Launcher")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Launcher 绑定地址")
    parser.add_argument("--port", type=int, default=8080, help="Launcher 端口")
    parser.add_argument(
        "--public-host",
        type=str,
        default=None,
        help="写入 viewer_url 的主机名（默认 127.0.0.1；远程访问请设为机器 IP）",
    )
    parser.add_argument(
        "--viewer-bind-host",
        type=str,
        default="0.0.0.0",
        help="Viewer 子进程绑定地址",
    )
    args = parser.parse_args()

    global _session_manager
    _session_manager = SessionManager(web_host=args.viewer_bind_host, public_host=args.public_host)

    print(f"Launcher: http://{args.host}:{args.port}/launcher")
    if args.public_host:
        print(f"Viewer URL 将使用 public-host={args.public_host}")
    else:
        print("提示: 远程浏览器访问时请加 --public-host <本机IP>")

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
