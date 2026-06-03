export class RobotRenderer {
  constructor(name) {
    this.name = name;
  }

  async load(_context) {
    throw new Error(`${this.name} renderer does not implement load()`);
  }

  applyState(_robotState) {
    throw new Error(`${this.name} renderer does not implement applyState()`);
  }

  getName() {
    return this.name;
  }

  getCameras() {
    return {};
  }

  getObjectFrame() {
    return null;
  }
}
