import * as THREE from "three";
import { applyPose, quatFromWxyz } from "../core/math.js";
import { RobotRenderer } from "./robot_renderer.js";

const MESH_BASE = "/models/meshes/universal_robots_ur5e";
const JOINT_NAMES = [
  "shoulder_pan_joint",
  "shoulder_lift_joint",
  "elbow_joint",
  "wrist_1_joint",
  "wrist_2_joint",
  "wrist_3_joint",
];

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

async function loadObj(objLoader, url) {
  return await new Promise((resolve, reject) => {
    objLoader.load(url, resolve, undefined, reject);
  });
}

function setFrameQuat(frame, wxyz) {
  frame.quaternion.copy(quatFromWxyz(wxyz).normalize());
}

function jointValue(joints, name) {
  if (joints && typeof joints === "object") return joints[name] ?? 0.0;
  return 0.0;
}

export class Ur5eRenderer extends RobotRenderer {
  constructor() {
    super("ur5e");
    this.root = new THREE.Group();
    this.armJoints = {};
    this.leftFinger = null;
    this.rightFinger = null;
  }

  async load({ scene, objLoader, status }) {
    if (status) status("加载 UR5e mesh...");
    scene.add(this.root);

    const files = {
      base_0: `${MESH_BASE}/base_0.obj`,
      base_1: `${MESH_BASE}/base_1.obj`,
      shoulder_0: `${MESH_BASE}/shoulder_0.obj`,
      shoulder_1: `${MESH_BASE}/shoulder_1.obj`,
      shoulder_2: `${MESH_BASE}/shoulder_2.obj`,
      upperarm_0: `${MESH_BASE}/upperarm_0.obj`,
      upperarm_1: `${MESH_BASE}/upperarm_1.obj`,
      upperarm_2: `${MESH_BASE}/upperarm_2.obj`,
      upperarm_3: `${MESH_BASE}/upperarm_3.obj`,
      forearm_0: `${MESH_BASE}/forearm_0.obj`,
      forearm_1: `${MESH_BASE}/forearm_1.obj`,
      forearm_2: `${MESH_BASE}/forearm_2.obj`,
      forearm_3: `${MESH_BASE}/forearm_3.obj`,
      wrist1_0: `${MESH_BASE}/wrist1_0.obj`,
      wrist1_1: `${MESH_BASE}/wrist1_1.obj`,
      wrist1_2: `${MESH_BASE}/wrist1_2.obj`,
      wrist2_0: `${MESH_BASE}/wrist2_0.obj`,
      wrist2_1: `${MESH_BASE}/wrist2_1.obj`,
      wrist2_2: `${MESH_BASE}/wrist2_2.obj`,
      wrist3: `${MESH_BASE}/wrist3.obj`,
    };

    const entries = await Promise.all(
      Object.entries(files).map(async ([key, url]) => [key, await loadObj(objLoader, url)])
    );
    const libs = Object.fromEntries(entries);

    const matBlack = new THREE.MeshStandardMaterial({ color: 0x080808, metalness: 0.2, roughness: 0.55 });
    const matJoint = new THREE.MeshStandardMaterial({ color: 0x474747, metalness: 0.15, roughness: 0.55 });
    const matLink = new THREE.MeshStandardMaterial({ color: 0xd1d1d1, metalness: 0.12, roughness: 0.5 });
    const matBlue = new THREE.MeshStandardMaterial({ color: 0x7dade0, metalness: 0.1, roughness: 0.5 });
    const matGripper = new THREE.MeshStandardMaterial({ color: 0x666666, metalness: 0.2, roughness: 0.6 });

    this.root.add(cloneWithMaterial(libs.base_0, matBlack));
    this.root.add(cloneWithMaterial(libs.base_1, matJoint));

    const shoulderFrame = new THREE.Group();
    shoulderFrame.position.set(0, 0, 0.163);
    this.root.add(shoulderFrame);
    const shoulderRot = new THREE.Group();
    shoulderFrame.add(shoulderRot);
    shoulderRot.add(cloneWithMaterial(libs.shoulder_0, matBlue));
    shoulderRot.add(cloneWithMaterial(libs.shoulder_1, matBlack));
    shoulderRot.add(cloneWithMaterial(libs.shoulder_2, matJoint));

    const upperArmFrame = new THREE.Group();
    upperArmFrame.position.set(0, 0.138, 0);
    setFrameQuat(upperArmFrame, [1, 0, 1, 0]);
    shoulderRot.add(upperArmFrame);
    const upperArmRot = new THREE.Group();
    upperArmFrame.add(upperArmRot);
    upperArmRot.add(cloneWithMaterial(libs.upperarm_0, matLink));
    upperArmRot.add(cloneWithMaterial(libs.upperarm_1, matBlack));
    upperArmRot.add(cloneWithMaterial(libs.upperarm_2, matJoint));
    upperArmRot.add(cloneWithMaterial(libs.upperarm_3, matBlue));

    const forearmFrame = new THREE.Group();
    forearmFrame.position.set(0, -0.131, 0.425);
    upperArmRot.add(forearmFrame);
    const forearmRot = new THREE.Group();
    forearmFrame.add(forearmRot);
    forearmRot.add(cloneWithMaterial(libs.forearm_0, matBlue));
    forearmRot.add(cloneWithMaterial(libs.forearm_1, matLink));
    forearmRot.add(cloneWithMaterial(libs.forearm_2, matBlack));
    forearmRot.add(cloneWithMaterial(libs.forearm_3, matJoint));

    const wrist1Frame = new THREE.Group();
    wrist1Frame.position.set(0, 0, 0.392);
    setFrameQuat(wrist1Frame, [1, 0, 1, 0]);
    forearmRot.add(wrist1Frame);
    const wrist1Rot = new THREE.Group();
    wrist1Frame.add(wrist1Rot);
    wrist1Rot.add(cloneWithMaterial(libs.wrist1_0, matBlack));
    wrist1Rot.add(cloneWithMaterial(libs.wrist1_1, matBlue));
    wrist1Rot.add(cloneWithMaterial(libs.wrist1_2, matJoint));

    const wrist2Frame = new THREE.Group();
    wrist2Frame.position.set(0, 0.127, 0);
    wrist1Rot.add(wrist2Frame);
    const wrist2Rot = new THREE.Group();
    wrist2Frame.add(wrist2Rot);
    wrist2Rot.add(cloneWithMaterial(libs.wrist2_0, matBlack));
    wrist2Rot.add(cloneWithMaterial(libs.wrist2_1, matBlue));
    wrist2Rot.add(cloneWithMaterial(libs.wrist2_2, matJoint));

    const wrist3Frame = new THREE.Group();
    wrist3Frame.position.set(0, 0, 0.1);
    wrist2Rot.add(wrist3Frame);
    const wrist3Rot = new THREE.Group();
    wrist3Frame.add(wrist3Rot);
    wrist3Rot.add(cloneWithMaterial(libs.wrist3, matLink));

    this.addSimpleGripper(wrist3Rot, matGripper);

    this.armJoints = {
      shoulder_pan_joint: { object: shoulderRot, axis: "z" },
      shoulder_lift_joint: { object: upperArmRot, axis: "y" },
      elbow_joint: { object: forearmRot, axis: "y" },
      wrist_1_joint: { object: wrist1Rot, axis: "y" },
      wrist_2_joint: { object: wrist2Rot, axis: "z" },
      wrist_3_joint: { object: wrist3Rot, axis: "y" },
    };
  }

  addSimpleGripper(parent, material) {
    const gripper = new THREE.Group();
    gripper.position.set(0, 0.0823, 0);
    setFrameQuat(gripper, [3.40583e-05, 3.4055e-05, 0.707073, 0.707141]);
    parent.add(gripper);

    const palm = new THREE.Mesh(new THREE.BoxGeometry(0.105, 0.036, 0.032), material);
    palm.position.set(0, 0, 0.018);
    gripper.add(palm);

    const railMat = new THREE.MeshStandardMaterial({ color: 0x303030, metalness: 0.25, roughness: 0.55 });
    const railLeft = new THREE.Mesh(new THREE.BoxGeometry(0.006, 0.018, 0.12), railMat);
    const railRight = railLeft.clone();
    railLeft.position.set(-0.023, 0, 0.075);
    railRight.position.set(0.023, 0, 0.075);
    gripper.add(railLeft);
    gripper.add(railRight);

    const fingerMat = new THREE.MeshStandardMaterial({ color: 0x111111, metalness: 0.15, roughness: 0.62 });
    this.leftFinger = new THREE.Group();
    this.rightFinger = new THREE.Group();

    const leftKnuckle = new THREE.Mesh(new THREE.BoxGeometry(0.018, 0.022, 0.026), material);
    const rightKnuckle = leftKnuckle.clone();
    leftKnuckle.position.set(0, 0, 0.038);
    rightKnuckle.position.set(0, 0, 0.038);
    this.leftFinger.add(leftKnuckle);
    this.rightFinger.add(rightKnuckle);

    const leftTip = new THREE.Mesh(new THREE.BoxGeometry(0.012, 0.018, 0.105), fingerMat);
    const rightTip = leftTip.clone();
    leftTip.position.set(0, 0, 0.102);
    rightTip.position.set(0, 0, 0.102);
    this.leftFinger.add(leftTip);
    this.rightFinger.add(rightTip);

    this.leftFinger.position.set(-0.03, 0, 0.012);
    this.rightFinger.position.set(0.03, 0, 0.012);
    gripper.add(this.leftFinger);
    gripper.add(this.rightFinger);
  }

  applyState(robotState) {
    if (!robotState) return;
    applyPose(this.root, robotState.base_pose);

    const joints = robotState.joints || {};
    for (const name of JOINT_NAMES) {
      const joint = this.armJoints[name];
      if (!joint) continue;
      joint.object.rotation[joint.axis] = jointValue(joints, name);
    }

    const gripper = Math.max(0.0, Math.min(0.055, jointValue(joints, "gripper")));
    if (this.leftFinger) this.leftFinger.position.x = -gripper;
    if (this.rightFinger) this.rightFinger.position.x = gripper;
  }

  getCameras() {
    return {};
  }

  getObjectFrame() {
    return this.root;
  }
}
