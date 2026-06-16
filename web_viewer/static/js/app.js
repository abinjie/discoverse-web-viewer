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

async function fetchViewerConfig() {
  try {
    const r = await fetch("/api/config", { cache: "no-store" });
    return await r.json();
  } catch {
    return {};
  }
}

function shouldEnableGs(config) {
  const q = new URLSearchParams(location.search);
  if (q.get("render") === "mesh" || q.get("gs") === "0") return false;
  if (q.get("render") === "gs" || q.get("gs") === "1") return true;
  if (q.get("splats") || q.get("extras") === "1" || q.get("full") === "1") return true;
  return Boolean(config?.enable_gs);
}

function resolveEnvSplatUrls(config) {
  const q = new URLSearchParams(location.search);
  const csv = (q.get("splats") || "").trim();
  if (csv) {
    return csv.split(",").map((s) => s.trim()).filter(Boolean);
  }
  if (q.get("extras") === "1" || q.get("full") === "1") return [...ENV_SPLATS_FULL];
  if (config?.enable_gs) return [ENV_SPLATS_FULL[0]];
  return [];
}

function parseNumber(value, fallback) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function resolveGsPosition(config) {
  const q = new URLSearchParams(location.search);
  const offset = (q.get("gsOffset") || "").trim();
  if (offset) {
    const parts = offset.split(",").map((v) => Number(v.trim()));
    if (parts.length === 3 && parts.every(Number.isFinite)) return parts;
    console.warn(`忽略非法 gsOffset 参数: ${offset}`);
  }
  const hasUrlOffset = q.has("gsX") || q.has("gsY") || q.has("gsZ");
  if (hasUrlOffset) {
    return [
      parseNumber(q.get("gsX"), 0),
      parseNumber(q.get("gsY"), 0),
      parseNumber(q.get("gsZ"), 0),
    ];
  }
  const cfgOffset = config?.gs_offset;
  if (Array.isArray(cfgOffset) && cfgOffset.length === 3) {
    return cfgOffset.map((v) => Number(v));
  }
  return [0, 0, 0];
}

async function getRobotName(config) {
  const q = new URLSearchParams(location.search);
  const robot = q.get("robot");
  if (robot) return robot;
  return config?.robot || "airbot_play";
}

const view = document.getElementById("view");
const statusEl = document.getElementById("status");
const timeEl = document.getElementById("time");
const robotNameEl = document.getElementById("robot_name");
const pipCameraNameEl = document.getElementById("pip_camera_name");

const viewer = new HybridViewer({ view, statusEl, pipCameraNameEl });

try {
  const viewerConfig = await fetchViewerConfig();
  const robot = createRobotRenderer(await getRobotName(viewerConfig));
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

  const enableGs = shouldEnableGs(viewerConfig);
  const splatUrls = enableGs ? resolveEnvSplatUrls(viewerConfig) : [];
  const loaded = await viewer.initSplats(splatUrls, { position: resolveGsPosition(viewerConfig) });
  if (loaded > 0) {
    viewer.status(`已加载 ${loaded} 个环境 ply；机器人/物体由独立 renderer 驱动`);
  }

  const stateClient = new StateClient({
    onState: (state) => {
      if (!state?.ok) {
        if (state?.error) viewer.status(`状态未就绪：${state.error}`);
        return;
      }
      if (typeof state.time === "number") timeEl.textContent = `${state.time.toFixed(2)} s`;
      robot.applyState(state.robot);
      objects.applyState(state.objects);
      if (!enableGs && state.robot?.base_pose) {
        viewer.alignMeshTableToBasePose(state.robot.base_pose);
      }
      viewer.forceRender();
    },
    onError: (err) => {
      console.warn("状态同步失败:", err);
    },
  });
  stateClient.start();

  viewer.start();
} catch (err) {
  console.error(err);
  statusEl.textContent = `初始化失败：${err.message}`;
}
