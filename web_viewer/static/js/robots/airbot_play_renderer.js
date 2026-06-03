import * as THREE from "three";
import { applyPose, quatFromWxyz } from "../core/math.js";
import { RobotRenderer } from "./robot_renderer.js";

const MESH_BASE = "/models/meshes/airbot_play";
const JOINT_NAMES = ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6"];

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function cloneWithMaterial(obj, material) {
  const c = obj.clone(true);
  c.traverse((n) => {
    if (n.isMesh) {
      n.material = material;
      n.castShadow = true;
      n.receiveShadow = true;
    }
  });
  return c;
}

function jointValue(joints, index, name) {
  if (Array.isArray(joints)) return joints[index] ?? 0.0;
  if (joints && typeof joints === "object") return joints[name] ?? 0.0;
  return 0.0;
}

async function loadObj(objLoader, url) {
  return await new Promise((resolve, reject) => {
    objLoader.load(url, resolve, undefined, reject);
  });
}

export class AirbotPlayRenderer extends RobotRenderer {
  constructor() {
    super("airbot_play");
    this.root = new THREE.Group();
    this.meshRoot = new THREE.Group();
    this.root.add(this.meshRoot);

    this.armJoints = [];
    this.leftSlide = null;
    this.rightSlide = null;
    this.armCamera = null;
  }

  async load({ scene, objLoader, renderTargetSize, status }) {
    if (status) status("加载 Airbot Play mesh...");
    scene.add(this.root);

    const files = {
      arm_base_0: `${MESH_BASE}/arm_base_0.obj`,
      arm_base_1: `${MESH_BASE}/arm_base_1.obj`,
      link1: `${MESH_BASE}/link1.obj`,
      link2_0: `${MESH_BASE}/link2_0.obj`,
      link2_1: `${MESH_BASE}/link2_1.obj`,
      link3_0: `${MESH_BASE}/link3_0.obj`,
      link3_1: `${MESH_BASE}/link3_1.obj`,
      link4: `${MESH_BASE}/link4.obj`,
      link5_0: `${MESH_BASE}/link5_0.obj`,
      link5_1: `${MESH_BASE}/link5_1.obj`,
      link6: `${MESH_BASE}/link6.obj`,
      camera_stand: `${MESH_BASE}/camera_stand.obj`,
      left: `${MESH_BASE}/left.obj`,
      right: `${MESH_BASE}/right.obj`,
    };
    const entries = await Promise.all(
      Object.entries(files).map(async ([key, url]) => [key, await loadObj(objLoader, url)])
    );
    const libs = Object.fromEntries(entries);

    const meshMatDark = new THREE.MeshStandardMaterial({ color: 0x2a2e39, metalness: 0.25, roughness: 0.65 });
    const meshMatLight = new THREE.MeshStandardMaterial({ color: 0xdadce3, metalness: 0.15, roughness: 0.55 });

    const linkBase = new THREE.Group();
    this.meshRoot.add(linkBase);
    const armBase0 = cloneWithMaterial(libs.arm_base_0, meshMatDark);
    armBase0.position.set(0, 0, -0.0015);
    linkBase.add(armBase0);
    linkBase.add(cloneWithMaterial(libs.arm_base_1, meshMatLight));

    const j1Frame = new THREE.Group();
    j1Frame.position.set(0, 0, 0.1172);
    linkBase.add(j1Frame);
    const j1Rot = new THREE.Group();
    j1Frame.add(j1Rot);
    const link1 = new THREE.Group();
    j1Rot.add(link1);
    link1.add(cloneWithMaterial(libs.link1, meshMatLight));

    const j2Frame = new THREE.Group();
    j2Frame.quaternion.copy(quatFromWxyz([0.135866, 0.135867, -0.69393, 0.693932]));
    link1.add(j2Frame);
    const j2Rot = new THREE.Group();
    j2Frame.add(j2Rot);
    const link2 = new THREE.Group();
    j2Rot.add(link2);
    link2.add(cloneWithMaterial(libs.link2_0, meshMatDark));
    link2.add(cloneWithMaterial(libs.link2_1, meshMatLight));

    const j3Frame = new THREE.Group();
    j3Frame.position.set(0.27009, 0, 0);
    j3Frame.quaternion.copy(quatFromWxyz([0.192144, 0, 0, -0.981367]));
    link2.add(j3Frame);
    const j3Rot = new THREE.Group();
    j3Frame.add(j3Rot);
    const link3 = new THREE.Group();
    j3Rot.add(link3);
    link3.add(cloneWithMaterial(libs.link3_0, meshMatDark));
    link3.add(cloneWithMaterial(libs.link3_1, meshMatLight));

    const j4Frame = new THREE.Group();
    j4Frame.position.set(0.29015, 0, 0);
    j4Frame.quaternion.copy(quatFromWxyz([-2.59734e-06, 0.707105, 2.59735e-06, 0.707108]));
    link3.add(j4Frame);
    const j4Rot = new THREE.Group();
    j4Frame.add(j4Rot);
    const link4 = new THREE.Group();
    j4Rot.add(link4);
    link4.add(cloneWithMaterial(libs.link4, meshMatLight));

    const j5Frame = new THREE.Group();
    j5Frame.quaternion.copy(quatFromWxyz([0.707105, 0.707108, 0, 0]));
    link4.add(j5Frame);
    const j5Rot = new THREE.Group();
    j5Frame.add(j5Rot);
    const link5 = new THREE.Group();
    j5Rot.add(link5);
    link5.add(cloneWithMaterial(libs.link5_0, meshMatDark));
    link5.add(cloneWithMaterial(libs.link5_1, meshMatLight));

    const j6Frame = new THREE.Group();
    j6Frame.position.set(0, 0.23645, 0);
    j6Frame.quaternion.copy(quatFromWxyz([0.499998, -0.5, 0.5, 0.500002]));
    link5.add(j6Frame);
    const j6Rot = new THREE.Group();
    j6Frame.add(j6Rot);
    const link6 = new THREE.Group();
    j6Rot.add(link6);
    link6.add(cloneWithMaterial(libs.link6, meshMatDark));
    link6.add(cloneWithMaterial(libs.camera_stand, meshMatDark));

    this.leftSlide = new THREE.Group();
    link6.add(this.leftSlide);
    this.leftSlide.add(cloneWithMaterial(libs.right, meshMatLight));
    this.rightSlide = new THREE.Group();
    link6.add(this.rightSlide);
    this.rightSlide.add(cloneWithMaterial(libs.left, meshMatLight));

    const armCamBody = new THREE.Group();
    link6.add(armCamBody);
    armCamBody.position.set(-0.105, 0, -0.12);
    armCamBody.rotation.order = "XYZ";
    armCamBody.rotation.set(Math.PI, 0, Math.PI / 2);

    const width = renderTargetSize?.width ?? 320;
    const height = renderTargetSize?.height ?? 240;
    this.armCamera = new THREE.PerspectiveCamera(72.5376526571421, width / height, 0.02, 20);
    this.armCamera.up.set(0, 0, 1);
    this.armCamera.rotation.order = "XYZ";
    this.armCamera.rotation.x = -0.5236;
    armCamBody.add(this.armCamera);

    this.armJoints = [j1Rot, j2Rot, j3Rot, j4Rot, j5Rot, j6Rot];
  }

  applyState(robotState) {
    if (!robotState) return;
    applyPose(this.root, robotState.base_pose);

    const joints = robotState.joints;
    for (let i = 0; i < this.armJoints.length; i++) {
      this.armJoints[i].rotation.z = jointValue(joints, i, JOINT_NAMES[i]);
    }

    const gripper = jointValue(joints, 6, "gripper");
    if (this.leftSlide) this.leftSlide.position.y = clamp(gripper, 0.0, 0.04);
    if (this.rightSlide) this.rightSlide.position.y = clamp(-gripper, -0.04, 0.0);
  }

  getCameras() {
    return { eye_arm: this.armCamera };
  }

  getObjectFrame() {
    return this.root;
  }
}
