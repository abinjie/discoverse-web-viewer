#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本机网页遥操作 DISCOVERSE 机械臂（MuJoCo + mink IK）。

运行（需在仓库根目录或已 pip install -e .）:

  cd /path/to/DISCOVERSE
  pip install "discoverse[web-teleop]"  # 或: pip install fastapi "uvicorn[standard]"
  python examples/web_teleop/web_app.py -r airbot_play

或:

  python examples/mocap_ik/mocap_ik_manipulator.py --web-teleop -r airbot_play

浏览器打开 http://127.0.0.1:8765
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_MOCAP_IK_DIR = os.path.join(_REPO_ROOT, "examples", "mocap_ik")
if _MOCAP_IK_DIR not in sys.path:
    sys.path.insert(0, _MOCAP_IK_DIR)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import numpy as np
import uvicorn

from mocap_ik_manipulator import Manipulator, parse_args

STATE: Dict[str, Any] = {"node": None, "sim_thread": None}


def _run_sim(args) -> None:
    args.web_teleop = True
    node = Manipulator(args)
    STATE["node"] = node
    try:
        node.run()
    finally:
        STATE["node"] = None


def _norm_quat_wxyz(q: np.ndarray) -> np.ndarray:
    q = np.asarray(q, dtype=np.float64).reshape(4)
    n = np.linalg.norm(q)
    if n < 1e-9:
        return np.array([1.0, 0.0, 0.0, 0.0])
    return q / n


@asynccontextmanager
async def lifespan(app: FastAPI):
    args: Any = STATE["args"]
    t = threading.Thread(target=_run_sim, args=(args,), name="discoverse-mujoco-sim", daemon=False)
    STATE["sim_thread"] = t
    t.start()
    deadline = time.time() + 120.0
    while time.time() < deadline and STATE["node"] is None:
        await asyncio.sleep(0.02)
    yield
    node = STATE.get("node")
    if node is not None:
        node.request_stop()
    t.join(timeout=12.0)


app = FastAPI(lifespan=lifespan)
_STATIC = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_STATIC):
    app.mount("/static", StaticFiles(directory=_STATIC), name="static")
_MODELS = os.path.join(_REPO_ROOT, "models")
if os.path.isdir(_MODELS):
    app.mount("/models", StaticFiles(directory=_MODELS), name="models")


@app.get("/")
async def index():
    index_path = os.path.join(_STATIC, "webgl.html")
    if os.path.isfile(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<p>Missing static/webgl.html</p>", status_code=500)


@app.get("/mjpeg")
async def mjpeg_page():
    index_path = os.path.join(_STATIC, "index.html")
    if os.path.isfile(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<p>Missing static/index.html</p>", status_code=500)


@app.get("/state")
async def get_state():
    node = STATE.get("node")
    if node is None:
        return {"ok": False, "error": "sim not ready"}
    obs = node.get_observation()
    return {
        "ok": True,
        "time": float(obs["time"]),
        "jq": obs["jq"],
        "eef_pos": obs["eef_pos"],
        "eef_quat": obs["eef_quat"],
        "target_pos": obs["action"][:3],
        "target_quat": obs["action"][3:7],
    }


@app.get("/video.mjpeg")
async def video_mjpeg():
    async def gen():
        boundary = b"frame"
        while True:
            node = STATE.get("node")
            if node is None or node._latest_frame_lock is None:
                await asyncio.sleep(0.05)
                continue
            with node._latest_frame_lock:
                jpg = node._latest_jpeg
            if not jpg:
                await asyncio.sleep(0.02)
                continue
            yield (
                b"--" + boundary + b"\r\n"
                b"Content-Type: image/jpeg\r\n"
                b"Content-Length: " + str(len(jpg)).encode("ascii") + b"\r\n"
                b"Cache-Control: no-cache\r\n"
                b"Pragma: no-cache\r\n"
                b"Expires: 0\r\n\r\n"
                + jpg
                + b"\r\n"
            )
            await asyncio.sleep(1.0 / 24.0)

    return StreamingResponse(
        gen(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Accel-Buffering": "no",
        },
    )


@app.websocket("/ws")
async def ws_control(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            node = STATE.get("node")
            if node is None or node._target_cmd_lock is None:
                await asyncio.sleep(0.01)
                continue
            cmd = data.get("cmd")
            if cmd == "reset":
                node.request_web_reset()
                await ws.send_json({"ok": True, "cmd": "reset"})
                continue
            if cmd == "set_target" or "pos" in data:
                pos = data.get("pos")
                quat = data.get("quat_wxyz")
                if pos is None or quat is None:
                    await ws.send_json({"ok": False, "error": "need pos and quat_wxyz"})
                    continue
                p = np.asarray(pos, dtype=np.float64).reshape(3)
                q = _norm_quat_wxyz(np.asarray(quat, dtype=np.float64).reshape(4))
                with node._target_cmd_lock:
                    node._web_cmd_pos[:] = p
                    node._web_cmd_quat[:] = q
                await ws.send_json({"ok": True})
            else:
                await ws.send_json({"ok": False, "error": "unknown message"})
    except WebSocketDisconnect:
        pass


def run_server(args: Optional[Any] = None) -> None:
    if args is None:
        args = parse_args()
    args.web_teleop = True
    STATE["args"] = args
    uvicorn.run(
        app,
        host=args.web_host,
        port=args.web_port,
        log_level="info",
        ws_ping_interval=None,
    )


def main() -> None:
    run_server()


if __name__ == "__main__":
    main()
