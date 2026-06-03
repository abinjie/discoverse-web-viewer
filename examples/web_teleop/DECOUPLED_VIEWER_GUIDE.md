# 浏览器渲染解耦说明

本文说明如何把“机械臂模型/任务状态”和“浏览器渲染”解耦，以及后续新增机械臂、XML 任务时应该改哪里。

## 1. 当前入口

旧入口仍保留在 `examples/web_teleop/`：

```bash
python examples/web_teleop/web_app_auto_stack.py --web-host 0.0.0.0 --web-port 8765
```

解耦后的新入口在仓库根目录 `web_viewer/`：

```bash
cd /home/ubuntu/data/discoverse-web-viewer
conda activate discoverse
pip install -e ".[web-teleop]"
python web_viewer/server.py --web-host 0.0.0.0 --web-port 8765
```

浏览器打开：

```text
http://127.0.0.1:8765/?robot=airbot_play
```

加载更多 3DGS 环境对象：

```text
http://127.0.0.1:8765/?robot=airbot_play&extras=1
```

指定环境 ply：

```text
http://127.0.0.1:8765/?robot=airbot_play&splats=/models/3dgs/scene/lab3/point_cloud.gs3d.ply
```

## 2. 解耦后的目录职责

```text
web_viewer/
  server.py                              # FastAPI 入口，负责仿真状态和静态资源服务
  static/index.html                      # 新浏览器页面
  static/js/app.js                       # 前端组装入口
  static/js/core/hybrid_viewer.js        # Three.js + 3DGS 渲染核心
  static/js/core/state_client.js         # 状态轮询与协议兼容
  static/js/core/object_renderer.js      # 方块等任务物体渲染
  static/js/core/math.js                 # 位姿/四元数工具
  static/js/robots/robot_renderer.js     # 机械臂渲染接口
  static/js/robots/airbot_play_renderer.js
  static/js/robots/registry.js           # robot 名称到 renderer 的注册表
```

核心原则：

- `HybridViewer` 不知道机械臂型号，只负责场景、3DGS、主相机、腕部相机 PiP、渲染循环。
- `RobotRenderer` 只负责某一种机械臂的 mesh、关节树、夹爪、相机。
- `StateClient` 只负责从 `/api/state` 或旧 `/state` 拉状态并归一化。
- `ObjectRenderer` 只负责任务物体，不写死在机械臂 renderer 里。
- 后端把 MuJoCo/任务内部状态转换成浏览器统一协议。

## 3. 浏览器统一状态协议

新前端优先读取：

```text
GET /api/state
```

推荐返回格式：

```json
{
  "ok": true,
  "time": 1.23,
  "robot": {
    "name": "airbot_play",
    "base_pose": {
      "pos": [0.0, 0.0, 0.0],
      "quat_wxyz": [1.0, 0.0, 0.0, 0.0]
    },
    "joints": {
      "joint1": 0.0,
      "joint2": 0.0,
      "joint3": 0.0,
      "joint4": 0.0,
      "joint5": 0.0,
      "joint6": 0.0,
      "gripper": 0.04
    },
    "joint_order": ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6", "gripper"]
  },
  "objects": {
    "block_green": {
      "pos": [0.3, 0.0, 0.02],
      "quat_wxyz": [1.0, 0.0, 0.0, 0.0]
    }
  },
  "objects_frame": "robot_base"
}
```

约定：

- `quat_wxyz` 必须是 MuJoCo 常用的 `[w, x, y, z]`。
- `robot.base_pose` 是机械臂基座在世界系下的位姿。
- `robot.joints` 使用关节名，不建议让浏览器依赖 `qpos[:N]`。
- `objects` 的位姿当前按 `robot_base` 局部坐标给出，由前端挂到 `robot.getObjectFrame()` 下。
- 如果后续需要世界系物体，可以把 `objects_frame` 改成 `world`，并在 `ObjectRenderer` 里选择父节点。

旧接口仍可兼容：

```text
GET /state
```

旧格式中的 `jq`、`arm_base_world`、`blocks` 会在 `StateClient` 里归一化。

## 4. 新增机械臂支持

假设新增机械臂名为 `ur5e`。

### 4.1 准备 MuJoCo XML

机械臂 XML 放在：

```text
models/mjcf/robot_ur5e.xml
```

可以先检查是否能被 `make_env` 组合：

```bash
cd /home/ubuntu/data/discoverse-web-viewer
conda activate discoverse
python - <<'PY'
from discoverse.envs import make_env

env = make_env("ur5e", "stack_block", "models/mjcf/tmp/ur5e_stack_block.xml")
print(env.test_mujoco_load())
PY
```

如果失败，优先检查：

```bash
ls models/mjcf/robot_ur5e.xml
ls models/mjcf/tasks_airbot_play/stack_block.xml
ls models/mjcf/tmp
```

### 4.2 准备通用任务配置

通用运行时需要机器人配置：

```text
discoverse/configs/robots/ur5e.yaml
```

关键字段：

```yaml
robot_name: "ur5e"
kinematics:
  base_link: "base"
  end_effector_site: "endpoint"
  arm_joint_names:
    - "shoulder_pan_joint"
    - "shoulder_lift_joint"
    - "elbow_joint"
    - "wrist_1_joint"
    - "wrist_2_joint"
    - "wrist_3_joint"
sensors:
  joint_pos_sensors:
    - "shoulder_pan_pos"
    - "shoulder_lift_pos"
    - "elbow_pos"
    - "wrist_1_pos"
    - "wrist_2_pos"
    - "wrist_3_pos"
    - "gripper_pos"
```

检查通用任务是否能跑：

```bash
python examples/universal_tasks/universal_task_runtime.py -r ur5e -t place_block -1 --headless
```

### 4.3 新增浏览器 robot renderer

新增文件：

```text
web_viewer/static/js/robots/ur5e_renderer.js
```

最小结构：

```js
import * as THREE from "three";
import { RobotRenderer } from "./robot_renderer.js";
import { applyPose } from "../core/math.js";

export class Ur5eRenderer extends RobotRenderer {
  constructor() {
    super("ur5e");
    this.root = new THREE.Group();
    this.armJoints = [];
  }

  async load({ scene, objLoader, renderTargetSize, status }) {
    if (status) status("加载 UR5e mesh...");
    scene.add(this.root);

    // TODO:
    // 1. 加载 /models/meshes/ur5e/*.obj 或 glTF
    // 2. 按 MuJoCo XML 的 body/joint 层级建立 THREE.Group
    // 3. 把每个可动关节的旋转 group 放入 this.armJoints
    // 4. 如有 eye_arm，相机挂到末端 link 下
  }

  applyState(robotState) {
    applyPose(this.root, robotState.base_pose);
    const joints = robotState.joints || {};
    // 示例：按关节名应用角度
    // this.armJoints[0].rotation.z = joints.shoulder_pan_joint ?? 0.0;
  }

  getCameras() {
    return {};
  }

  getObjectFrame() {
    return this.root;
  }
}
```

注册到：

```text
web_viewer/static/js/robots/registry.js
```

示例：

```js
import { Ur5eRenderer } from "./ur5e_renderer.js";

const ROBOTS = {
  airbot_play: () => new AirbotPlayRenderer(),
  ur5e: () => new Ur5eRenderer(),
};
```

运行：

```bash
python web_viewer/server.py --web-host 0.0.0.0 --web-port 8765
```

浏览器：

```text
http://127.0.0.1:8765/?robot=ur5e
```

### 4.4 后端状态适配

后端不要把浏览器绑定到 MuJoCo `qpos` 顺序。推荐为每个机器人提供状态适配器：

```python
def build_robot_state(node, robot_name):
    if robot_name == "ur5e":
        return {
            "name": "ur5e",
            "base_pose": get_base_pose(node, "base"),
            "joints": {
                "shoulder_pan_joint": float(...),
                "shoulder_lift_joint": float(...),
                "elbow_joint": float(...),
                "wrist_1_joint": float(...),
                "wrist_2_joint": float(...),
                "wrist_3_joint": float(...),
                "gripper": float(...),
            },
            "joint_order": [
                "shoulder_pan_joint",
                "shoulder_lift_joint",
                "elbow_joint",
                "wrist_1_joint",
                "wrist_2_joint",
                "wrist_3_joint",
                "gripper",
            ],
        }
    raise ValueError(f"unsupported robot: {robot_name}")
```

定位关节传感器建议使用名称，不要硬编码 `qpos[:7]`：

```python
sensor_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SENSOR, "shoulder_pan_pos")
value = float(data.sensordata[sensor_id])
```

## 5. 新增 XML 任务支持

假设新增任务名为 `pick_cube`。

### 5.1 添加任务 XML

放到：

```text
models/mjcf/tasks_airbot_play/pick_cube.xml
```

虽然目录名是 `tasks_airbot_play`，`make_env(robot_name, task_name)` 会把任务场景和目标机器人 XML 合并。

必须检查：

- 任务物体 body 名称稳定，例如 `cube_red`。
- 相机名称如果前端/记录器要用，建议保持 `eye_side`、`eye_arm`。
- 任务 XML 不要重新定义目标机械臂的同名 body，避免合并冲突。

生成并验证：

```bash
python - <<'PY'
from discoverse.envs import make_env

env = make_env("ur5e", "pick_cube", "models/mjcf/tmp/ur5e_pick_cube.xml")
print("mujoco_load:", env.test_mujoco_load())
PY
```

### 5.2 添加任务 YAML

通用运行时任务配置放到：

```text
discoverse/configs/tasks/pick_cube.yaml
```

最小结构：

```yaml
task_name: "pick_cube"
description: "抓取红色方块"

runtime_parameters:
  source_object: "cube_red"
  approach_height: 0.08
  grasp_height: 0.005
  lift_height: 0.08

states:
  - name: "approach_cube"
    primitive: "move_to_object"
    params:
      object_name: "cube_red"
      offset: [0, 0, 0.08]
    gripper_state: "open"

  - name: "move_to_grasp"
    primitive: "move_to_object"
    params:
      object_name: "cube_red"
      offset: [0, 0, 0.005]
    gripper_state: "open"

  - name: "grasp_cube"
    primitive: "grasp_object"
    params:
      object_name: "cube_red"
    gripper_state: "close"
    delay: 0.35

  - name: "lift_cube"
    primitive: "move_relative"
    params:
      offset: [0, 0, 0.08]
      keep_orientation: true
    gripper_state: "close"
```

运行：

```bash
python examples/universal_tasks/universal_task_runtime.py -r ur5e -t pick_cube -1 --headless
```

如果 `universal_task_runtime.py` 的 argparse choices 没包含新任务，需要把 `pick_cube` 加到：

```text
examples/universal_tasks/universal_task_runtime.py
```

也可以在专用脚本中直接调用：

```python
from examples.universal_tasks.universal_task_runtime import main

main("ur5e", "pick_cube", once=True, headless=True)
```

### 5.3 浏览器显示新物体

如果新任务物体不是默认方块，需要扩展：

```text
web_viewer/static/js/core/object_renderer.js
```

示例：新增 `cube_red`。

```js
const DEFAULT_OBJECTS = {
  block_red: { color: 0xff4444, size: [0.04, 0.04, 0.04] },
  block_green: { color: 0x44ff44, size: [0.04, 0.04, 0.04] },
  block_blue: { color: 0x4444ff, size: [0.04, 0.04, 0.04] },
  cube_red: { color: 0xff2222, size: [0.04, 0.04, 0.04] },
};
```

如果是杯子、抽屉、笔记本等复杂物体，建议新增 mesh object renderer，而不是用 box 占位。

## 6. 调试步骤

### 6.1 先验证 XML

```bash
python - <<'PY'
from discoverse.envs import make_env

robot = "ur5e"
task = "stack_block"
env = make_env(robot, task, f"models/mjcf/tmp/{robot}_{task}.xml")
print(env.test_mujoco_load())
PY
```

### 6.2 再验证通用任务

```bash
python examples/universal_tasks/universal_task_runtime.py -r ur5e -t stack_block -1 --headless
```

### 6.3 再验证浏览器状态接口

```bash
python web_viewer/server.py --web-host 0.0.0.0 --web-port 8765
```

另开终端：

```bash
curl http://127.0.0.1:8765/api/state
curl http://127.0.0.1:8765/state
```

检查返回：

- `ok` 是否为 `true`。
- `robot.name` 是否等于 URL 中的 `robot`。
- `robot.joints` 的关节名是否和 renderer 使用的一致。
- `objects` 的物体名是否和 `ObjectRenderer` 支持的一致。

### 6.4 最后验证浏览器渲染

```text
http://127.0.0.1:8765/?robot=ur5e
```

浏览器控制台重点看：

- mesh 资源是否 404。
- `Unknown robot renderer` 是否说明忘了注册。
- 关节方向是否反了，若反了在对应 `RobotRenderer.applyState()` 里调整轴或符号。
- 腕部相机是否挂在正确 link 下。

## 7. 推荐开发顺序

新增机械臂：

```text
1. robot XML 能被 MuJoCo 加载
2. make_env(robot, task) 能生成组合 XML
3. discoverse/configs/robots/<robot>.yaml 能驱动通用任务
4. /api/state 能返回具名 joints
5. web_viewer/static/js/robots/<robot>_renderer.js 能显示静态 mesh
6. applyState() 逐个关节联调
7. 最后接入夹爪和腕部相机
```

新增任务：

```text
1. 添加任务 XML
2. make_env("ur5e", task) 验证 XML
3. 添加 discoverse/configs/tasks/<task>.yaml
4. universal_task_runtime.py headless 单次验证
5. 后端 /api/state 暴露新物体位姿
6. ObjectRenderer 支持新物体显示
```

