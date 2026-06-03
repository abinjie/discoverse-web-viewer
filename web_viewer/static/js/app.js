import { OBJLoader } from "https://unpkg.com/three@0.164.1/examples/jsm/loaders/OBJLoader.js";
import { HybridViewer } from "./core/hybrid_viewer.js";
import { ObjectRenderer } from "./core/object_renderer.js";
import { StateClient } from "./core/state_client.js";
import { createRobotRenderer } from "./robots/registry.js";

const ENV_SPLATS_FULL = [
  "/models/3dgs/scene/lab3/point_cloud.gs3d.ply",
  "/models/3dgs/hinge/drawer_1.webgs.ply",
  "/models/3dgs/hinge/drawer_2.webgs.ply",
  "/models/3dgs/object/bowl_pink.webgs.ply",
];

function resolveEnvSplatUrls() {
  const q = new URLSearchParams(location.search);
  const csv = (q.get("splats") || "").trim();
  if (csv) {
    return csv.split(",").map((s) => s.trim()).filter(Boolean);
  }
  if (q.get("extras") === "1" || q.get("full") === "1") return [...ENV_SPLATS_FULL];
  return [ENV_SPLATS_FULL[0]];
}

async function getRobotName() {
  const q = new URLSearchParams(location.search);
  const robot = q.get("robot");
  if (robot) return robot;
  try {
    const r = await fetch("/api/config", { cache: "no-store" });
    const config = await r.json();
    return config.robot || "airbot_play";
  } catch {
    return "airbot_play";
  }
}

const view = document.getElementById("view");
const statusEl = document.getElementById("status");
const timeEl = document.getElementById("time");
const robotNameEl = document.getElementById("robot_name");
const pipCameraNameEl = document.getElementById("pip_camera_name");

const viewer = new HybridViewer({ view, statusEl, pipCameraNameEl });

try {
  const robot = createRobotRenderer(await getRobotName());
  robotNameEl.textContent = robot.getName();

  await robot.load({
    scene: viewer.scene,
    objLoader: new OBJLoader(),
    renderTargetSize: viewer.getRenderTargetSize(),
    status: (text) => viewer.status(text),
  });
  viewer.setRobot(robot);

  const objectParent = robot.getObjectFrame() || viewer.scene;
  const objects = new ObjectRenderer({ parent: objectParent });

  const stateClient = new StateClient({
    onState: (state) => {
      if (!state?.ok) {
        if (state?.error) viewer.status(`状态未就绪：${state.error}`);
        return;
      }
      if (typeof state.time === "number") timeEl.textContent = `${state.time.toFixed(2)} s`;
      robot.applyState(state.robot);
      objects.applyState(state.objects);
      viewer.forceRender();
    },
    onError: (err) => {
      console.warn("状态同步失败:", err);
    },
  });
  stateClient.start();

  const loaded = await viewer.initSplats(resolveEnvSplatUrls());
  if (loaded > 0) viewer.status(`已加载 ${loaded} 个环境 ply；机器人/物体由独立 renderer 驱动`);
  viewer.start();
} catch (err) {
  console.error(err);
  statusEl.textContent = `初始化失败：${err.message}`;
}
