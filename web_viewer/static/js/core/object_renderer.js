import * as THREE from "three";
import { applyPose } from "./math.js";

const DEFAULT_OBJECTS = {
  block_red: { color: 0xff4444, size: [0.04, 0.04, 0.04] },
  block_green: { color: 0x44ff44, size: [0.04, 0.04, 0.04] },
  block_blue: { color: 0x4444ff, size: [0.04, 0.04, 0.04] },
  bowl_pink: { color: 0xdb8088, type: "bowl" },
};

function createBowlObject(cfg) {
  const group = new THREE.Group();
  const material = new THREE.MeshStandardMaterial({
    color: cfg.color ?? 0xff9ac8,
    roughness: 0.72,
    metalness: 0.03,
    side: THREE.DoubleSide,
  });

  const profile = [
    new THREE.Vector2(0.024, -0.018),
    new THREE.Vector2(0.042, -0.012),
    new THREE.Vector2(0.058, 0.004),
    new THREE.Vector2(0.068, 0.026),
  ];
  const body = new THREE.Mesh(new THREE.LatheGeometry(profile, 48), material);
  body.geometry.rotateX(Math.PI / 2);
  group.add(body);

  const rim = new THREE.Mesh(new THREE.TorusGeometry(0.068, 0.0045, 10, 48), material);
  rim.position.z = 0.026;
  group.add(rim);

  const base = new THREE.Mesh(new THREE.CylinderGeometry(0.026, 0.03, 0.006, 32), material);
  base.geometry.rotateX(Math.PI / 2);
  base.position.z = -0.021;
  group.add(base);

  return group;
}

function createObject(cfg) {
  if (cfg.type === "bowl") {
    return createBowlObject(cfg);
  }
  const material = new THREE.MeshStandardMaterial({ color: cfg.color ?? 0xffffff });
  const size = cfg.size ?? [0.04, 0.04, 0.04];
  return new THREE.Mesh(new THREE.BoxGeometry(size[0], size[1], size[2]), material);
}

export class ObjectRenderer {
  constructor({ parent, objectConfigs = DEFAULT_OBJECTS }) {
    this.group = new THREE.Group();
    this.objects = {};
    parent.add(this.group);

    for (const [name, cfg] of Object.entries(objectConfigs)) {
      const object = createObject(cfg);
      object.position.set(0, 0, -10);
      this.group.add(object);
      this.objects[name] = object;
    }
  }

  applyState(objects) {
    if (!objects) return;
    for (const [name, pose] of Object.entries(objects)) {
      const object = this.objects[name];
      if (!object) continue;
      applyPose(object, pose);
    }
  }
}
