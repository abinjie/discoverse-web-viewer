import asyncio
import json
import os
import sys
import threading
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import numpy as np
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import MutableHeaders
from starlette.middleware.gzip import GZipMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_TASKS_DIR = os.path.join(_REPO_ROOT, "examples", "tasks_airbot_play")
if _TASKS_DIR not in sys.path:
    sys.path.insert(0, _TASKS_DIR)

from scipy.spatial.transform import Rotation
from discoverse.utils import get_body_tmat, step_func, SimpleStateMachine
from discoverse.robots import AirbotPlayIK
from stack_block import SimNode, cfg, robot_name, task_name

STATE: Dict[str, Any] = {"node": None, "sim_thread": None, "args": None}

def _run_sim(args) -> None:
    # 强制无头模式，避免在服务器上弹窗
    cfg.headless = True
    cfg.sync = True
    cfg.render_set["fps"] = 30
    
    sim_node = SimNode(cfg)
    STATE["node"] = sim_node
    
    arm_ik = AirbotPlayIK()
    trmat = Rotation.from_euler("xyz", [0., np.pi/2, 0.], degrees=False).as_matrix()
    tmat_armbase_2_world = np.linalg.inv(get_body_tmat(sim_node.mj_data, "arm_base"))
    
    stm = SimpleStateMachine()
    stm.max_state_cnt = 18
    max_time = 12.0
    action = np.zeros(7)
    move_speed = 0.75
    
    sim_node.reset()
    try:
        while sim_node.running:
            if sim_node.reset_sig:
                sim_node.reset_sig = False
                stm.reset()
                action[:] = sim_node.target_control[:]
            
            try:
                if stm.trigger():
                    if stm.state_idx == 0:
                        tmat_jujube = get_body_tmat(sim_node.mj_data, "block_green")
                        tmat_jujube[:3, 3] = tmat_jujube[:3, 3] + 0.1 * tmat_jujube[:3, 2]
                        tmat_tgt_local = tmat_armbase_2_world @ tmat_jujube
                        sim_node.target_control[:6] = arm_ik.properIK(tmat_tgt_local[:3,3], trmat, sim_node.mj_data.qpos[:6])
                        sim_node.target_control[6] = 0.04
                    elif stm.state_idx == 1:
                        tmat_jujube = get_body_tmat(sim_node.mj_data, "block_green")
                        tmat_jujube[:3, 3] = tmat_jujube[:3, 3] + 0.028 * tmat_jujube[:3, 2]
                        tmat_tgt_local = tmat_armbase_2_world @ tmat_jujube
                        sim_node.target_control[:6] = arm_ik.properIK(tmat_tgt_local[:3,3], trmat, sim_node.mj_data.qpos[:6])
                    elif stm.state_idx == 2:
                        sim_node.target_control[6] = 0.0
                    elif stm.state_idx == 3:
                        sim_node.delay_cnt = int(0.35/sim_node.delta_t)
                    elif stm.state_idx == 4:
                        tmat_tgt_local[2,3] += 0.07
                        sim_node.target_control[:6] = arm_ik.properIK(tmat_tgt_local[:3,3], trmat, sim_node.mj_data.qpos[:6])
                    elif stm.state_idx == 5:
                        tmat_plate = get_body_tmat(sim_node.mj_data, "block_blue")
                        tmat_plate[:3,3] = tmat_plate[:3, 3] + np.array([0.0, 0.0, 0.13])
                        tmat_tgt_local = tmat_armbase_2_world @ tmat_plate
                        sim_node.target_control[:6] = arm_ik.properIK(tmat_tgt_local[:3,3], trmat, sim_node.mj_data.qpos[:6])
                    elif stm.state_idx == 6:
                        tmat_tgt_local[2,3] -= 0.04
                        sim_node.target_control[:6] = arm_ik.properIK(tmat_tgt_local[:3,3], trmat, sim_node.mj_data.qpos[:6])
                    elif stm.state_idx == 7:
                        sim_node.target_control[6] = 0.04
                    elif stm.state_idx == 8:
                        tmat_tgt_local[2,3] += 0.05
                        sim_node.target_control[:6] = arm_ik.properIK(tmat_tgt_local[:3,3], trmat, sim_node.mj_data.qpos[:6])
                    elif stm.state_idx == 9:
                        tmat_jujube = get_body_tmat(sim_node.mj_data, "block_red")
                        tmat_jujube[:3, 3] = tmat_jujube[:3, 3] + 0.1 * tmat_jujube[:3, 2]
                        tmat_tgt_local = tmat_armbase_2_world @ tmat_jujube
                        sim_node.target_control[:6] = arm_ik.properIK(tmat_tgt_local[:3,3], trmat, sim_node.mj_data.qpos[:6])
                        sim_node.target_control[6] = 0.04
                    elif stm.state_idx == 10:
                        tmat_jujube = get_body_tmat(sim_node.mj_data, "block_red")
                        tmat_jujube[:3, 3] = tmat_jujube[:3, 3] + 0.028 * tmat_jujube[:3, 2]
                        tmat_tgt_local = tmat_armbase_2_world @ tmat_jujube
                        sim_node.target_control[:6] = arm_ik.properIK(tmat_tgt_local[:3,3], trmat, sim_node.mj_data.qpos[:6])
                    elif stm.state_idx == 11:
                        sim_node.target_control[6] = 0.0
                    elif stm.state_idx == 12:
                        sim_node.delay_cnt = int(0.35/sim_node.delta_t)
                    elif stm.state_idx == 13:
                        tmat_tgt_local[2,3] += 0.07
                        sim_node.target_control[:6] = arm_ik.properIK(tmat_tgt_local[:3,3], trmat, sim_node.mj_data.qpos[:6])
                    elif stm.state_idx == 14:
                        tmat_plate = get_body_tmat(sim_node.mj_data, "block_green")
                        tmat_plate[:3,3] = tmat_plate[:3, 3] + np.array([0.0, 0.0, 0.10])
                        tmat_tgt_local = tmat_armbase_2_world @ tmat_plate
                        sim_node.target_control[:6] = arm_ik.properIK(tmat_tgt_local[:3,3], trmat, sim_node.mj_data.qpos[:6])
                    elif stm.state_idx == 15:
                        tmat_tgt_local[2,3] -= 0.04
                        sim_node.target_control[:6] = arm_ik.properIK(tmat_tgt_local[:3,3], trmat, sim_node.mj_data.qpos[:6])
                    elif stm.state_idx == 16:
                        sim_node.target_control[6] = 0.04
                    elif stm.state_idx == 17:
                        tmat_tgt_local[2,3] += 0.05
                        sim_node.target_control[:6] = arm_ik.properIK(tmat_tgt_local[:3,3], trmat, sim_node.mj_data.qpos[:6])
                    
                    dif = np.abs(action - sim_node.target_control)
                    sim_node.joint_move_ratio = dif / (np.max(dif) + 1e-6)
                elif sim_node.mj_data.time > max_time:
                    sim_node.reset()
                else:
                    stm.update()
                
                if sim_node.checkActionDone():
                    stm.next()
            except ValueError as ve:
                print("Error: ", ve)
                sim_node.reset()
            
            for i in range(sim_node.nj-1):
                action[i] = step_func(action[i], sim_node.target_control[i], move_speed * sim_node.joint_move_ratio[i] * sim_node.delta_t)
            action[6] = sim_node.target_control[6]
            
            sim_node.step(action)
            
            if stm.state_idx >= stm.max_state_cnt:
                sim_node.reset()
            
            # 控制帧率
            time.sleep(max(0, 1.0/30.0 - sim_node.delta_t))
            
    finally:
        STATE["node"] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    t = threading.Thread(target=_run_sim, args=(None,), name="discoverse-mujoco-sim", daemon=True)
    STATE["sim_thread"] = t
    t.start()
    deadline = time.time() + 120.0
    while time.time() < deadline and STATE["node"] is None:
        await asyncio.sleep(0.02)
    yield
    node = STATE.get("node")
    if node is not None:
        node.running = False
    t.join(timeout=12.0)


class DisablePathSendForModelsMiddleware:
    """pathsend 响应不会经过 GZipMiddleware（Starlette 直接放行），大 ply 仍是原始字节。

    仅对 /models/ 关闭 pathsend，让 FileResponse 走分块读取，gzip 才能生效。
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            path = scope.get("path") or ""
            ext = scope.get("extensions") or {}
            if path.startswith("/models/") and "http.response.pathsend" in ext:
                scope = dict(scope)
                scope["extensions"] = {k: v for k, v in ext.items() if k != "http.response.pathsend"}
        await self.app(scope, receive, send)


def _strip_gzip_from_accept_encoding(raw_headers: list) -> list:
    """从 Accept-Encoding 去掉 gzip，避免 GZipMiddleware 使用分块 gzip（无 Content-Length）。"""
    out: list = []
    for name, value in raw_headers:
        if name.lower() != b"accept-encoding":
            out.append((name, value))
            continue
        enc = value.decode("latin1")
        parts = [p.strip() for p in enc.split(",") if p.strip().lower() != "gzip"]
        if parts:
            out.append((name, ", ".join(parts).encode("latin1")))
    return out


class StripGzipAcceptForGs3dPlyMiddleware:
    """小体积 *.gs3d.ply 不需要 gzip；分块 gzip 会丢失 Content-Length，GaussianSplats3D 进度无百分比且像卡住。"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            path = scope.get("path") or ""
            if path.endswith(".gs3d.ply"):
                scope = dict(scope)
                scope["headers"] = _strip_gzip_from_accept_encoding(list(scope["headers"]))
        await self.app(scope, receive, send)


class NoCacheModelsPlyMiddleware:
    """PLY 体积大且调试频繁：禁用缓存，避免 304 + 旧字节导致解析异常或「看似卡住」。"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path") or ""
        if not (path.startswith("/models/") and path.endswith(".ply")):
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                h = MutableHeaders(scope=message)
                h["cache-control"] = "no-store, max-age=0, must-revalidate"
                if "etag" in h:
                    del h["etag"]
            await send(message)

        await self.app(scope, receive, send_wrapper)


app = FastAPI(lifespan=lifespan)

_STATIC = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_STATIC):
    app.mount("/static", StaticFiles(directory=_STATIC), name="static")
_MODELS = os.path.join(_REPO_ROOT, "models")
if os.path.isdir(_MODELS):
    app.mount("/models", StaticFiles(directory=_MODELS), name="models")

@app.get("/")
async def index():
    index_path = os.path.join(_STATIC, "webgl_auto_stack.html")
    if os.path.isfile(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<p>Missing static/webgl_auto_stack.html</p>", status_code=500)


@app.get("/hybrid")
async def hybrid():
    """环境 3DGS（ply）+ 机械臂/方块 mesh，与 stack_block gs_model_dict 对齐（不含方块 ply）。"""
    path = os.path.join(_STATIC, "webgl_auto_stack_hybrid.html")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<p>Missing static/webgl_auto_stack_hybrid.html</p>", status_code=500)


@app.get("/gs")
async def gs_ply_viewer():
    """仅浏览器预览 3DGS PLY；可选查询参数 ?ply=/models/3dgs/..."""
    path = os.path.join(_STATIC, "gs_ply_viewer.html")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<p>Missing static/gs_ply_viewer.html</p>", status_code=500)


@app.get("/state")
async def get_state():
    node = STATE.get("node")
    if node is None:
        return {"ok": False, "error": "sim not ready"}
    
    # 获取关节状态
    jq = node.mj_data.qpos[:7].tolist()
    
    # 获取三个方块的位姿，转为相对于 armbase 的局部坐标
    tmat_armbase = get_body_tmat(node.mj_data, "arm_base")
    inv_tmat_armbase = np.linalg.inv(tmat_armbase)
    
    blocks = {}
    for b in ["block_red", "block_green", "block_blue"]:
        tmat_b = get_body_tmat(node.mj_data, b)
        tmat_local = inv_tmat_armbase @ tmat_b
        pos = tmat_local[:3, 3].tolist()
        quat_xyzw = Rotation.from_matrix(tmat_local[:3, :3]).as_quat()
        quat_wxyz = [quat_xyzw[3], quat_xyzw[0], quat_xyzw[1], quat_xyzw[2]]
        blocks[b] = {"pos": pos, "quat_wxyz": quat_wxyz}
        
    return {
        "ok": True,
        "time": float(node.mj_data.time),
        "jq": jq,
        "blocks": blocks
    }


# 外层禁止 ply 缓存；内层 gzip + pathsend + *.gs3d.ply 剥 gzip 请求（保留 Content-Length）
asgi_app = NoCacheModelsPlyMiddleware(
    GZipMiddleware(
        StripGzipAcceptForGs3dPlyMiddleware(DisablePathSendForModelsMiddleware(app)),
        minimum_size=500,
        compresslevel=6,
    )
)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--web-host", type=str, default="0.0.0.0")
    parser.add_argument("--web-port", type=int, default=8765)
    args = parser.parse_args()
    
    uvicorn.run(asgi_app, host=args.web_host, port=args.web_port, log_level="info")

if __name__ == "__main__":
    main()
