import * as THREE from "three";
import { Viewer } from "@mkkellogg/gaussian-splats-3d";
import { OrbitControls } from "https://unpkg.com/three@0.164.1/examples/jsm/controls/OrbitControls.js";

const ARM_RT_W = 320;
const ARM_RT_H = 240;
const ARM_CAM_UPDATE_MS = 120;

function hasVisibleChildren(obj) {
  for (const child of obj.children) {
    if (child.visible) return true;
  }
  return false;
}

export class HybridViewer {
  constructor({ view, statusEl, pipCameraNameEl }) {
    this.view = view;
    this.statusEl = statusEl;
    this.pipCameraNameEl = pipCameraNameEl;

    THREE.Object3D.DEFAULT_UP.set(0, 0, 1);
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x16203a);

    this.camera = new THREE.PerspectiveCamera(50, 1, 0.01, 100);
    this.camera.up.set(0, 0, 1);
    this.camera.position.set(1.8, -1.8, 1.3);

    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.25;
    this.view.appendChild(this.renderer.domElement);

    this.viewer = null;
    this.meshOnlyOrbit = null;
    this.armCamera = null;
    this.armCamBusy = false;
    this.lastArmCamUpdate = 0;
    this.renderLoopStarted = false;

    this.setupHud();
    this.setupLightsAndFallback();
    window.addEventListener("resize", () => this.resize());
    this.resize();
  }

  getRenderTargetSize() {
    return { width: ARM_RT_W, height: ARM_RT_H };
  }

  setupHud() {
    this.armRt = new THREE.WebGLRenderTarget(ARM_RT_W, ARM_RT_H, { depthBuffer: true });
    this.armRt.texture.colorSpace = THREE.SRGBColorSpace;

    this.hudCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 40);
    this.hudCam.position.set(0, 0, 10);
    this.hudScene = new THREE.Scene();

    const hudMat = new THREE.MeshBasicMaterial({
      map: this.armRt.texture,
      depthTest: false,
      depthWrite: false,
      toneMapped: false,
    });
    const hudW = 0.56;
    const hudH = 0.42;
    const margin = 0.04;
    const hudX = 1 - margin - hudW / 2;
    const hudY = -1 + margin + hudH / 2;

    const hudPlane = new THREE.Mesh(new THREE.PlaneGeometry(hudW, hudH), hudMat);
    hudPlane.position.set(hudX, hudY, 0);
    hudPlane.renderOrder = 99999;
    this.hudScene.add(hudPlane);

    const frameMat = new THREE.MeshBasicMaterial({
      color: 0x6378b7,
      depthTest: false,
      depthWrite: false,
      toneMapped: false,
    });
    const hudFrame = new THREE.Mesh(new THREE.PlaneGeometry(hudW + 0.012, hudH + 0.012), frameMat);
    hudFrame.position.set(hudX, hudY, -0.001);
    hudFrame.renderOrder = 99998;
    this.hudScene.add(hudFrame);
  }

  setupLightsAndFallback() {
    this.scene.add(new THREE.HemisphereLight(0xeaf1ff, 0x4a5f86, 0.35));
    const keyLight = new THREE.DirectionalLight(0xffffff, 0.85);
    keyLight.position.set(2.5, -2, 3.2);
    this.scene.add(keyLight);
    this.scene.add(new THREE.AmbientLight(0xaec0e6, 0.25));

    this.grid = new THREE.GridHelper(4, 40, 0x6378b7, 0x324267);
    this.grid.rotation.x = Math.PI / 2;
    this.grid.visible = false;
    this.scene.add(this.grid);

    this.tableGroup = new THREE.Group();
    this.tableGroup.visible = false;
    this.scene.add(this.tableGroup);
    this.tableTopThickness = 0.03;
    const tableTop = new THREE.Mesh(
      new THREE.BoxGeometry(0.9, 0.6, this.tableTopThickness),
      new THREE.MeshStandardMaterial({ color: 0xf2f3f7, roughness: 0.78, metalness: 0.04 })
    );
    tableTop.position.set(0, 0, -this.tableTopThickness / 2);
    this.tableGroup.add(tableTop);
    this.meshTableAligned = false;
  }

  /** Mesh 模式下将占位桌面移到机械臂基座下方（XY 对齐，桌面高度贴近仿真场景）。 */
  alignMeshTableToBasePose(basePose, { frameCamera = true } = {}) {
    if (!basePose?.pos || basePose.pos.length < 3) return;
    if (!this.tableGroup.visible && !this.meshTableActive) return;
    const [x, y, baseZ] = basePose.pos;
    if (![x, y, baseZ].every(Number.isFinite)) return;

    const tableSurfaceZ = baseZ - 0.012;
    this.tableGroup.position.set(x, y, tableSurfaceZ);
    this.grid.position.set(x, y, 0);

    if (this.meshOnlyOrbit) {
      this.meshOnlyOrbit.target.set(x, y, baseZ * 0.45 + 0.15);
      if (frameCamera && !this.meshTableAligned) {
        this.camera.position.set(x + 1.4, y - 1.2, baseZ + 0.55);
        this.meshOnlyOrbit.update();
        this.meshTableAligned = true;
      }
    }
    this.forceRender();
  }

  setRobot(robotRenderer) {
    const cameras = robotRenderer.getCameras();
    const cameraEntries = Object.entries(cameras).filter(([, camera]) => Boolean(camera));
    if (cameraEntries.length > 0) {
      const [name, camera] = cameraEntries[0];
      this.armCamera = camera;
      if (this.pipCameraNameEl) this.pipCameraNameEl.textContent = name;
      if (this.pipCameraNameEl?.parentElement) this.pipCameraNameEl.parentElement.style.display = "";
    } else if (this.pipCameraNameEl?.parentElement) {
      this.pipCameraNameEl.parentElement.style.display = "none";
    }
  }

  enableMeshOnlyMode(message = "Mesh 渲染模式") {
    this.meshTableActive = true;
    this.grid.visible = true;
    this.tableGroup.visible = true;
    if (!this.meshOnlyOrbit) {
      this.meshOnlyOrbit = new OrbitControls(this.camera, this.renderer.domElement);
      this.meshOnlyOrbit.enableDamping = true;
    }
    // 先用默认安装位显示桌面；相机等 /api/state 首帧再对齐
    this.alignMeshTableToBasePose({ pos: [0.3, 1.0, 0.71] }, { frameCamera: false });
    this.status(message);
    return 0;
  }

  async initSplats(splatUrls, options = {}) {
    if (!splatUrls?.length) {
      return this.enableMeshOnlyMode("Mesh 渲染模式：未加载 GS 环境");
    }
    this.status("初始化 3DGS Viewer...");
    const splatPosition = options.position ?? [0, 0, 0];
    this.viewer = new Viewer({
      rootElement: this.view,
      threeScene: this.scene,
      camera: this.camera,
      renderer: this.renderer,
      selfDrivenMode: false,
      useBuiltInControls: true,
      cameraUp: [0, 0, 1],
      initialCameraPosition: [1.8, -1.8, 1.3],
      initialCameraLookAt: [0, 0, 0.35],
      sharedMemoryForWorkers: false,
      gpuAcceleratedSort: false,
      sphericalHarmonicsDegree: 2,
    });

    let loaded = 0;
    for (const url of splatUrls) {
      try {
        this.status(`加载 GS: ${url.split("/").pop()} ...`);
        await this.viewer.addSplatScene(url, {
          splatAlphaRemovalThreshold: 1,
          showLoadingUI: true,
          position: splatPosition,
          rotation: [0, 0, 0, 1],
          scale: [1, 1, 1],
          headers: { "Cache-Control": "no-store", Pragma: "no-cache" },
        });
        loaded++;
      } catch (err) {
        console.warn("跳过或失败:", url, err);
      }
    }

    if (loaded === 0) {
      this.status("ply 存在但解析失败，显示占位网格（请看控制台）");
      this.meshTableActive = true;
      this.grid.visible = true;
      this.tableGroup.visible = true;
      try {
        await this.viewer.dispose();
      } catch {
        /* ignore */
      }
      this.viewer = null;
      this.meshOnlyOrbit = new OrbitControls(this.camera, this.renderer.domElement);
      this.meshOnlyOrbit.enableDamping = true;
      this.alignMeshTableToBasePose({ pos: [0.3, 1.0, 0.71] }, { frameCamera: false });
    }

    return loaded;
  }

  start() {
    if (this.renderLoopStarted) return;
    this.renderLoopStarted = true;
    this.renderLoop();
    this.updateArmCamPiP();
  }

  status(text) {
    if (this.statusEl) this.statusEl.textContent = text;
  }

  resize() {
    const w = this.view.clientWidth;
    const h = this.view.clientHeight;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
    this.forceRender();
  }

  forceRender() {
    if (this.viewer?.forceRenderNextFrame) this.viewer.forceRenderNextFrame();
  }

  async waitViewerSort() {
    if (this.viewer?.sortPromise) {
      try {
        await this.viewer.sortPromise;
      } catch {
        /* ignore */
      }
    }
  }

  async updateArmCamPiP() {
    if (!this.viewer?.initialized || !this.viewer.splatRenderReady || !this.armCamera || this.armCamBusy) return;
    this.armCamBusy = true;
    const mainCam = this.viewer.camera;
    const savedRt = this.renderer.getRenderTarget();
    const savedAutoClear = this.renderer.autoClear;

    try {
      this.viewer.camera = this.armCamera;
      this.armCamera.aspect = ARM_RT_W / ARM_RT_H;
      this.armCamera.updateProjectionMatrix();
      this.armCamera.updateMatrixWorld(true);

      await this.waitViewerSort();
      await this.viewer.runSplatSort(true, true);
      await this.waitViewerSort();

      const splatMesh = this.viewer.splatMesh;
      if (splatMesh && splatMesh.getSplatCount() > 0) {
        splatMesh.updateTransforms();
        const pr = this.viewer.devicePixelRatio || this.renderer.getPixelRatio();
        const fa = this.viewer.focalAdjustment ?? 1;
        const flx = this.armCamera.projectionMatrix.elements[0] * 0.5 * pr * ARM_RT_W;
        const fly = this.armCamera.projectionMatrix.elements[5] * 0.5 * pr * ARM_RT_H;
        splatMesh.updateUniforms(
          new THREE.Vector2(ARM_RT_W, ARM_RT_H),
          flx * fa,
          fly * fa,
          false,
          1.0,
          1.0 / fa
        );
      }

      this.renderer.setRenderTarget(this.armRt);
      this.renderer.autoClear = true;
      this.renderer.setClearColor(this.scene.background);
      this.renderer.clear();

      if (hasVisibleChildren(this.scene)) {
        this.renderer.render(this.scene, this.armCamera);
        this.renderer.autoClear = false;
      }
      if (splatMesh && splatMesh.getSplatCount() > 0) {
        this.renderer.render(splatMesh, this.armCamera);
      }

      this.viewer.camera = mainCam;
      await this.waitViewerSort();
      await this.viewer.runSplatSort(true, true);
      await this.waitViewerSort();
      this.viewer.updateSplatMesh();
    } catch (err) {
      console.warn("腕部相机 GS 渲染失败:", err);
      this.viewer.camera = mainCam;
    } finally {
      this.renderer.setRenderTarget(savedRt);
      this.renderer.autoClear = savedAutoClear;
      this.armCamBusy = false;
      this.lastArmCamUpdate = performance.now();
    }
  }

  renderHudOverlay() {
    if (!this.armCamera) return;
    this.renderer.autoClear = false;
    this.renderer.render(this.hudScene, this.hudCam);
    this.renderer.autoClear = true;
  }

  renderLoop() {
    requestAnimationFrame(() => this.renderLoop());
    if (this.viewer) {
      if (!this.armCamBusy) {
        this.viewer.update();
        this.viewer.render();
      }
      this.renderHudOverlay();
      if (this.armCamera && !this.armCamBusy && performance.now() - this.lastArmCamUpdate >= ARM_CAM_UPDATE_MS) {
        this.updateArmCamPiP();
      }
    } else if (this.meshOnlyOrbit) {
      this.meshOnlyOrbit.update();
      this.renderer.setRenderTarget(null);
      this.renderer.autoClear = true;
      this.renderer.render(this.scene, this.camera);
      if (this.armCamera) {
        this.renderer.setRenderTarget(this.armRt);
        this.renderer.render(this.scene, this.armCamera);
        this.renderer.setRenderTarget(null);
        this.renderHudOverlay();
      }
    }
  }
}
