import { AirbotPlayRenderer } from "./airbot_play_renderer.js";
import { Ur5eRenderer } from "./ur5e_renderer.js";

const ROBOTS = {
  airbot_play: () => new AirbotPlayRenderer(),
  ur5e: () => new Ur5eRenderer(),
};

export function createRobotRenderer(name) {
  const key = name || "airbot_play";
  const factory = ROBOTS[key];
  if (!factory) {
    const available = Object.keys(ROBOTS).join(", ");
    throw new Error(`Unknown robot renderer "${key}". Available: ${available}`);
  }
  return factory();
}

export function listRobotRenderers() {
  return Object.keys(ROBOTS);
}
