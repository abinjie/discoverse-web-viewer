#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DISCOVERSE browser viewer with robot-renderer decoupling.

运行:
  python web_viewer/server.py --web-host 0.0.0.0 --web-port 8765

浏览器:
  http://127.0.0.1:8765/?robot=airbot_play
"""

import asyncio
import os
import sys
import threading
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import numpy as np
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from scipy.spatial.transform import Rotation
from starlette.datastructures import MutableHeaders
from starlette.middleware.gzip import GZipMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_TASKS_DIR = os.path.join(_REPO_ROOT, "examples", "tasks_airbot_play")
if _TASKS_DIR not in sys.path:
    sys.path.insert(0, _TASKS_DIR)
_UNIVERSAL_TASKS_DIR = os.path.join(_REPO_ROOT, "examples", "universal_tasks")
if _UNIVERSAL_TASKS_DIR not in sys.path:
    sys.path.insert(0, _UNIVERSAL_TASKS_DIR)

from discoverse.robots import AirbotPlayIK
from discoverse.utils import SimpleStateMachine, get_body_tmat, step_func
from stack_block import SimNode, cfg

STATE: Dict[str, Any] = {"node": None, "sim_thread": None, "args": None, "stop_requested": False}
AIRBOT_JOINT_NAMES = ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6"]
UR5E_JOINT_NAMES = [
    "shoulder_pan_joint",
    "shoulder_lift_joint",
    "elbow_joint",
    "wrist_1_joint",
    "wrist_2_joint",
    "wrist_3_joint",
]
BLOCK_NAMES = ["block_red", "block_green", "block_blue"]
TASK_OBJECT_NAMES = {
    "place_block": ["block_green", "bowl_pink"],
    "stack_block": ["block_red", "block_green", "block_blue"],
}


def _run_airbot_stack_sim(_args: Optional[Any] = None) -> None:
    cfg.headless = True
    cfg.sync = True
    cfg.render_set["fps"] = 30
    cfg.enable_render = False
    cfg.obs_rgb_cam_id = []
    cfg.obs_depth_cam_id = []
    cfg.use_gaussian_renderer = False

    sim_node = SimNode(cfg)
    STATE["node"] = sim_node

    arm_ik = AirbotPlayIK()
    trmat = Rotation.from_euler("xyz", [0.0, np.pi / 2, 0.0], degrees=False).as_matrix()
    tmat_armbase_2_world = np.linalg.inv(get_body_tmat(sim_node.mj_data, "arm_base"))

    stm = SimpleStateMachine()
    stm.max_state_cnt = 18
    max_time = 12.0
    action = np.zeros(7)
    move_speed = 0.75

    sim_node.reset()
    try:
        while sim_node.running:
            step_start_wall = time.perf_counter()
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
                        sim_node.target_control[:6] = arm_ik.properIK(
                            tmat_tgt_local[:3, 3], trmat, sim_node.mj_data.qpos[:6]
                        )
                        sim_node.target_control[6] = 0.04
                    elif stm.state_idx == 1:
                        tmat_jujube = get_body_tmat(sim_node.mj_data, "block_green")
                        tmat_jujube[:3, 3] = tmat_jujube[:3, 3] + 0.028 * tmat_jujube[:3, 2]
                        tmat_tgt_local = tmat_armbase_2_world @ tmat_jujube
                        sim_node.target_control[:6] = arm_ik.properIK(
                            tmat_tgt_local[:3, 3], trmat, sim_node.mj_data.qpos[:6]
                        )
                    elif stm.state_idx == 2:
                        sim_node.target_control[6] = 0.0
                    elif stm.state_idx == 3:
                        sim_node.delay_cnt = int(0.35 / sim_node.delta_t)
                    elif stm.state_idx == 4:
                        tmat_tgt_local[2, 3] += 0.07
                        sim_node.target_control[:6] = arm_ik.properIK(
                            tmat_tgt_local[:3, 3], trmat, sim_node.mj_data.qpos[:6]
                        )
                    elif stm.state_idx == 5:
                        tmat_plate = get_body_tmat(sim_node.mj_data, "block_blue")
                        tmat_plate[:3, 3] = tmat_plate[:3, 3] + np.array([0.0, 0.0, 0.13])
                        tmat_tgt_local = tmat_armbase_2_world @ tmat_plate
                        sim_node.target_control[:6] = arm_ik.properIK(
                            tmat_tgt_local[:3, 3], trmat, sim_node.mj_data.qpos[:6]
                        )
                    elif stm.state_idx == 6:
                        tmat_tgt_local[2, 3] -= 0.04
                        sim_node.target_control[:6] = arm_ik.properIK(
                            tmat_tgt_local[:3, 3], trmat, sim_node.mj_data.qpos[:6]
                        )
                    elif stm.state_idx == 7:
                        sim_node.target_control[6] = 0.04
                    elif stm.state_idx == 8:
                        tmat_tgt_local[2, 3] += 0.05
                        sim_node.target_control[:6] = arm_ik.properIK(
                            tmat_tgt_local[:3, 3], trmat, sim_node.mj_data.qpos[:6]
                        )
                    elif stm.state_idx == 9:
                        tmat_jujube = get_body_tmat(sim_node.mj_data, "block_red")
                        tmat_jujube[:3, 3] = tmat_jujube[:3, 3] + 0.1 * tmat_jujube[:3, 2]
                        tmat_tgt_local = tmat_armbase_2_world @ tmat_jujube
                        sim_node.target_control[:6] = arm_ik.properIK(
                            tmat_tgt_local[:3, 3], trmat, sim_node.mj_data.qpos[:6]
                        )
                        sim_node.target_control[6] = 0.04
                    elif stm.state_idx == 10:
                        tmat_jujube = get_body_tmat(sim_node.mj_data, "block_red")
                        tmat_jujube[:3, 3] = tmat_jujube[:3, 3] + 0.028 * tmat_jujube[:3, 2]
                        tmat_tgt_local = tmat_armbase_2_world @ tmat_jujube
                        sim_node.target_control[:6] = arm_ik.properIK(
                            tmat_tgt_local[:3, 3], trmat, sim_node.mj_data.qpos[:6]
                        )
                    elif stm.state_idx == 11:
                        sim_node.target_control[6] = 0.0
                    elif stm.state_idx == 12:
                        sim_node.delay_cnt = int(0.35 / sim_node.delta_t)
                    elif stm.state_idx == 13:
                        tmat_tgt_local[2, 3] += 0.07
                        sim_node.target_control[:6] = arm_ik.properIK(
                            tmat_tgt_local[:3, 3], trmat, sim_node.mj_data.qpos[:6]
                        )
                    elif stm.state_idx == 14:
                        tmat_plate = get_body_tmat(sim_node.mj_data, "block_green")
                        tmat_plate[:3, 3] = tmat_plate[:3, 3] + np.array([0.0, 0.0, 0.10])
                        tmat_tgt_local = tmat_armbase_2_world @ tmat_plate
                        sim_node.target_control[:6] = arm_ik.properIK(
                            tmat_tgt_local[:3, 3], trmat, sim_node.mj_data.qpos[:6]
                        )
                    elif stm.state_idx == 15:
                        tmat_tgt_local[2, 3] -= 0.04
                        sim_node.target_control[:6] = arm_ik.properIK(
                            tmat_tgt_local[:3, 3], trmat, sim_node.mj_data.qpos[:6]
                        )
                    elif stm.state_idx == 16:
                        sim_node.target_control[6] = 0.04
                    elif stm.state_idx == 17:
                        tmat_tgt_local[2, 3] += 0.05
                        sim_node.target_control[:6] = arm_ik.properIK(
                            tmat_tgt_local[:3, 3], trmat, sim_node.mj_data.qpos[:6]
                        )

                    dif = np.abs(action - sim_node.target_control)
                    sim_node.joint_move_ratio = dif / (np.max(dif) + 1e-6)
                elif sim_node.mj_data.time > max_time:
                    sim_node.reset()
                else:
                    stm.update()

                if sim_node.checkActionDone():
                    stm.next()
            except ValueError as exc:
                print("Error: ", exc)
                sim_node.reset()

            for i in range(sim_node.nj - 1):
                action[i] = step_func(
                    action[i],
                    sim_node.target_control[i],
                    move_speed * sim_node.joint_move_ratio[i] * sim_node.delta_t,
                )
            action[6] = sim_node.target_control[6]
            sim_node.step(action)

            if stm.state_idx >= stm.max_state_cnt:
                sim_node.reset()

            elapsed = time.perf_counter() - step_start_wall
            time.sleep(max(0.0, float(sim_node.delta_t) - elapsed))
    finally:
        STATE["node"] = None


def _run_universal_task_sim(args: Any) -> None:
    import mujoco

    from discoverse import DISCOVERSE_ROOT_DIR
    from discoverse.universal_manipulation import UniversalTaskBase
    from universal_task_runtime import UniversalRuntimeTaskExecutor, generate_robot_task_model

    class HeadlessUniversalRuntimeTaskExecutor(UniversalRuntimeTaskExecutor):
        """Web Viewer 只需要状态，不创建 MuJoCo Renderer，避免无 DISPLAY 环境下 OpenGL 初始化失败。"""

        def __init__(self, task: UniversalTaskBase, mj_model: mujoco.MjModel, mj_data: mujoco.MjData, robot_name: str, sync: bool = False):
            self.task = task
            self.viewer = None
            self.mj_model = mj_model
            self.mj_data = mj_data
            self.renderer = None
            self.robot_name = robot_name
            self.sync = sync

            self.sim_timestep = mj_model.opt.timestep
            self.viewer_fps = 60
            self.resolved_states = task.task_config.get_resolved_states()
            self.total_states = len(self.resolved_states)
            self.n_arm_joints = len(task.robot_interface.arm_joints)
            self.gripper_ctrl_idx = self.n_arm_joints
            self.joint_pos_sensor_idx = [
                mujoco.mj_name2id(mj_model, mujoco.mjtObj.mjOBJ_SENSOR, sensor_name)
                for sensor_name in task.robot_interface.joint_pos_sensors
            ]
            print(f"🔍 关节位置传感器: {task.robot_interface.joint_pos_sensors}")
            print(f"🔍 关节位置传感器索引: {self.joint_pos_sensor_idx}")

            self.mujoco_ctrl_dim = mj_model.nu
            self.move_speed = 1.5
            self.max_time = 20.0
            self.task.randomizer.set_viewer(None)
            self.task.randomizer.set_renderer(None)
            self.record_frq = self.task.task_config.record_fps
            self.camera_cfgs = {}
            self.camera_encoders = {}
            self.reset(random=False)

    xml_path = args.xml or generate_robot_task_model(args.robot, args.task)
    mj_model = mujoco.MjModel.from_xml_path(xml_path)
    mj_data = mujoco.MjData(mj_model)

    configs_root = os.path.join(DISCOVERSE_ROOT_DIR, "discoverse", "configs")
    robot_config_path = os.path.join(configs_root, "robots", f"{args.robot}.yaml")
    task_config_path = os.path.join(configs_root, "tasks", f"{args.task}.yaml")
    task = UniversalTaskBase(
        robot_config_path=robot_config_path,
        task_config_path=task_config_path,
        mj_model=mj_model,
        mj_data=mj_data,
    )
    executor = HeadlessUniversalRuntimeTaskExecutor(task, mj_model, mj_data, args.robot, sync=args.sync)

    STATE["node"] = {
        "kind": "universal",
        "robot_name": args.robot,
        "task_name": args.task,
        "xml_path": xml_path,
        "mj_model": mj_model,
        "mj_data": mj_data,
        "executor": executor,
    }

    try:
        while not STATE.get("stop_requested", False):
            step_start_wall = time.perf_counter()
            if not executor.running:
                executor.reset(random=not args.no_random)

            if not executor.step():
                executor.reset(random=not args.no_random)

            elapsed = time.perf_counter() - step_start_wall
            step_dt = float(mj_model.opt.timestep) * 5.0
            time.sleep(max(0.0, step_dt - elapsed))
    finally:
        STATE["node"] = None


def _run_sim(args: Optional[Any] = None) -> None:
    if args is not None and args.robot != "airbot_play":
        _run_universal_task_sim(args)
        return
    _run_airbot_stack_sim(args)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    args = STATE.get("args")
    STATE["stop_requested"] = False
    thread = threading.Thread(target=_run_sim, args=(args,), name="discoverse-mujoco-sim", daemon=True)
    STATE["sim_thread"] = thread
    thread.start()

    deadline = time.time() + 120.0
    while time.time() < deadline and STATE["node"] is None:
        await asyncio.sleep(0.02)

    yield

    STATE["stop_requested"] = True
    node = STATE.get("node")
    if node is not None and not isinstance(node, dict):
        node.running = False
    thread.join(timeout=12.0)


def _strip_gzip_from_accept_encoding(raw_headers: list) -> list:
    out = []
    for name, value in raw_headers:
        if name.lower() != b"accept-encoding":
            out.append((name, value))
            continue
        enc = value.decode("latin1")
        parts = [p.strip() for p in enc.split(",") if p.strip().lower() != "gzip"]
        if parts:
            out.append((name, ", ".join(parts).encode("latin1")))
    return out


class DisablePathSendForModelsMiddleware:
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


class StripGzipAcceptForGs3dPlyMiddleware:
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
                headers = MutableHeaders(scope=message)
                headers["cache-control"] = "no-store, max-age=0, must-revalidate"
                if "etag" in headers:
                    del headers["etag"]
            await send(message)

        await self.app(scope, receive, send_wrapper)


app = FastAPI(lifespan=lifespan)

_STATIC = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_STATIC):
    app.mount("/static", StaticFiles(directory=_STATIC), name="static")

_MODELS = os.path.join(_REPO_ROOT, "models")
if os.path.isdir(_MODELS):
    app.mount("/models", StaticFiles(directory=_MODELS), name="models")


def _pose_from_tmat(tmat: np.ndarray) -> Dict[str, Any]:
    quat_xyzw = Rotation.from_matrix(tmat[:3, :3]).as_quat()
    return {
        "pos": tmat[:3, 3].tolist(),
        "quat_wxyz": [quat_xyzw[3], quat_xyzw[0], quat_xyzw[1], quat_xyzw[2]],
    }


def _universal_node_state(node: Dict[str, Any]) -> Dict[str, Any]:
    import mujoco

    mj_model = node["mj_model"]
    mj_data = node["mj_data"]
    executor = node["executor"]
    robot_name = node["robot_name"]
    task_name = node["task_name"]
    robot_interface = executor.task.robot_interface

    base_link = robot_interface.robot_config.config["kinematics"]["base_link"]
    try:
        tmat_base = get_body_tmat(mj_data, base_link)
    except Exception:
        tmat_base = get_body_tmat(mj_data, f"{robot_name}_pose")
    inv_tmat_base = np.linalg.inv(tmat_base)

    joint_values = {}
    for joint_name, sensor_name in zip(robot_interface.arm_joints, robot_interface.joint_pos_sensors):
        sensor_id = mujoco.mj_name2id(mj_model, mujoco.mjtObj.mjOBJ_SENSOR, sensor_name)
        joint_values[joint_name] = float(mj_data.sensordata[sensor_id])

    gripper_value = 0.0
    if len(robot_interface.joint_pos_sensors) > len(robot_interface.arm_joints):
        sensor_name = robot_interface.joint_pos_sensors[len(robot_interface.arm_joints)]
        sensor_id = mujoco.mj_name2id(mj_model, mujoco.mjtObj.mjOBJ_SENSOR, sensor_name)
        gripper_value = float(mj_data.sensordata[sensor_id])
    joint_values["gripper"] = gripper_value

    objects = {}
    for object_name in TASK_OBJECT_NAMES.get(task_name, []):
        try:
            tmat_obj = get_body_tmat(mj_data, object_name)
        except Exception:
            continue
        objects[object_name] = _pose_from_tmat(inv_tmat_base @ tmat_obj)

    return {
        "ok": True,
        "time": float(mj_data.time),
        "robot": {
            "name": robot_name,
            "base_pose": _pose_from_tmat(tmat_base),
            "joints": joint_values,
            "joint_order": list(robot_interface.arm_joints) + ["gripper"],
        },
        "objects": objects,
        "objects_frame": "robot_base",
        "task": {
            "name": task_name,
            "xml_path": node["xml_path"],
            "state_index": int(executor.stm.state_idx),
            "total_states": int(executor.total_states),
        },
    }


def _legacy_state() -> Dict[str, Any]:
    node = STATE.get("node")
    if node is None:
        return {"ok": False, "error": "sim not ready"}
    if isinstance(node, dict):
        state = _universal_node_state(node)
        joints = state["robot"]["joints"]
        joint_order = state["robot"]["joint_order"]
        return {
            "ok": True,
            "time": state["time"],
            "robot_name": state["robot"]["name"],
            "jq": [joints.get(name, 0.0) for name in joint_order],
            "blocks": state["objects"],
            "arm_base_world": state["robot"]["base_pose"],
        }

    jq = node.mj_data.qpos[:7].tolist()
    tmat_armbase = get_body_tmat(node.mj_data, "arm_base")
    inv_tmat_armbase = np.linalg.inv(tmat_armbase)

    blocks = {}
    for block_name in BLOCK_NAMES:
        tmat_block = get_body_tmat(node.mj_data, block_name)
        tmat_local = inv_tmat_armbase @ tmat_block
        blocks[block_name] = _pose_from_tmat(tmat_local)

    return {
        "ok": True,
        "time": float(node.mj_data.time),
        "jq": jq,
        "blocks": blocks,
        "arm_base_world": _pose_from_tmat(tmat_armbase),
    }


def _api_state() -> Dict[str, Any]:
    node = STATE.get("node")
    if isinstance(node, dict):
        return _universal_node_state(node)

    legacy = _legacy_state()
    if not legacy.get("ok"):
        return legacy

    jq = legacy["jq"]
    joints = {name: jq[i] if len(jq) > i else 0.0 for i, name in enumerate(AIRBOT_JOINT_NAMES)}
    joints["gripper"] = jq[6] if len(jq) > 6 else 0.0

    return {
        "ok": True,
        "time": legacy["time"],
        "robot": {
            "name": "airbot_play",
            "base_pose": legacy["arm_base_world"],
            "joints": joints,
            "joint_order": AIRBOT_JOINT_NAMES + ["gripper"],
        },
        "objects": legacy["blocks"],
        "objects_frame": "robot_base",
    }


@app.get("/")
async def index():
    index_path = os.path.join(_STATIC, "index.html")
    if os.path.isfile(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<p>Missing web_viewer/static/index.html</p>", status_code=500)


@app.get("/api/state")
async def api_state():
    return _api_state()


@app.get("/api/config")
async def api_config():
    args = STATE.get("args")
    return {
        "robot": getattr(args, "robot", "airbot_play") if args is not None else "airbot_play",
        "task": getattr(args, "task", "stack_block") if args is not None else "stack_block",
    }


@app.get("/state")
async def state():
    return _legacy_state()


asgi_app = NoCacheModelsPlyMiddleware(
    GZipMiddleware(
        StripGzipAcceptForGs3dPlyMiddleware(DisablePathSendForModelsMiddleware(app)),
        minimum_size=500,
        compresslevel=6,
    )
)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--robot", type=str, default="airbot_play", choices=["airbot_play", "ur5e"])
    parser.add_argument("--task", type=str, default=None)
    parser.add_argument("--xml", type=str, default=None, help="可选：直接加载已生成的 MuJoCo XML")
    parser.add_argument("-s", "--sync", action="store_true", help="通用任务按仿真步长同步墙钟时间")
    parser.set_defaults(no_random=True)
    parser.add_argument("--randomize", action="store_false", dest="no_random", help="通用任务 reset 时启用场景随机化")
    parser.add_argument("--no-random", action="store_true", help="通用任务 reset 时关闭场景随机化（默认）")
    parser.add_argument("--web-host", type=str, default="0.0.0.0")
    parser.add_argument("--web-port", type=int, default=8765)
    args = parser.parse_args()

    if args.task is None:
        args.task = "place_block" if args.robot == "ur5e" else "stack_block"
    if args.robot == "airbot_play" and args.task != "stack_block":
        parser.error("当前 web_viewer 的 airbot_play 后端只支持 task=stack_block")
    if args.robot == "ur5e" and args.task != "place_block":
        parser.error("当前 web_viewer 的 ur5e 后端只支持 task=place_block")

    STATE["args"] = args
    uvicorn.run(asgi_app, host=args.web_host, port=args.web_port, log_level="info")


if __name__ == "__main__":
    main()
