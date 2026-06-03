import * as THREE from "three";

export function quatFromWxyz(wxyz) {
  return new THREE.Quaternion(wxyz[1], wxyz[2], wxyz[3], wxyz[0]);
}

export function applyPose(object, pose) {
  if (!object || !pose) return;
  const p = pose.pos;
  const q = pose.quat_wxyz;
  if (Array.isArray(p) && p.length >= 3) {
    object.position.set(p[0], p[1], p[2]);
  }
  if (Array.isArray(q) && q.length >= 4) {
    object.quaternion.copy(quatFromWxyz(q));
  }
}
