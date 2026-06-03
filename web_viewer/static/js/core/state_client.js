const DEFAULT_JOINT_NAMES = ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6"];

function normalizeLegacyState(state) {
  if (!state || state.robot) return state;

  const jq = state.jq || [];
  const joints = {};
  for (let i = 0; i < DEFAULT_JOINT_NAMES.length; i++) {
    joints[DEFAULT_JOINT_NAMES[i]] = jq[i] ?? 0.0;
  }
  joints.gripper = jq[6] ?? 0.0;

  return {
    ok: state.ok,
    error: state.error,
    time: state.time,
    robot: {
      name: state.robot_name || "airbot_play",
      base_pose: state.arm_base_world,
      joints,
    },
    objects: state.objects || state.blocks || {},
    objects_frame: "robot_base",
  };
}

export class StateClient {
  constructor({ url = "/api/state", legacyUrl = "/state", pollMs = 100, onState, onError }) {
    this.url = url;
    this.legacyUrl = legacyUrl;
    this.pollMs = pollMs;
    this.onState = onState;
    this.onError = onError;
    this.timer = null;
    this.inFlight = false;
  }

  start() {
    if (this.timer) return;
    this.sync();
    this.timer = window.setInterval(() => this.sync(), this.pollMs);
  }

  stop() {
    if (!this.timer) return;
    window.clearInterval(this.timer);
    this.timer = null;
  }

  async fetchJson(url) {
    const r = await fetch(url, { cache: "no-store" });
    if (!r.ok) throw new Error(`${url} returned HTTP ${r.status}`);
    return await r.json();
  }

  async sync() {
    if (this.inFlight) return;
    this.inFlight = true;
    try {
      let state;
      try {
        state = await this.fetchJson(this.url);
      } catch (err) {
        if (!this.legacyUrl) throw err;
        state = await this.fetchJson(this.legacyUrl);
      }
      if (this.onState) this.onState(normalizeLegacyState(state));
    } catch (err) {
      if (this.onError) this.onError(err);
    } finally {
      this.inFlight = false;
    }
  }
}
