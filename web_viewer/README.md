# Web Viewer 使用文档

`web_viewer` 是解耦后的浏览器渲染入口，用来把 MuJoCo/任务状态通过 `/api/state` 输出给浏览器，再由 Three.js + 3DGS 渲染环境、机械臂和任务物体。

## 推荐启动方式：Launcher

通过 Web 配置页选择机械臂、任务、Mesh/GS 渲染，无需手写 CLI：

```bash
cd /home/ubuntu/data/discoverse-web-viewer
conda activate discoverse
python -m web_viewer.launcher --host 0.0.0.0 --port 8080 --public-host 127.0.0.1
```

浏览器打开 `http://<IP>:8080/launcher`。完整文档见 [launcher/docs/README.md](./launcher/docs/README.md)。

当前支持机械臂：`airbot_play`、`ur5e`。任务列表来自 `make_env`（13 个 task_environments）。

## 直接 CLI 启动（仍可用）

当前支持任意 `make_env` 组合（不再限制 ur5e 只能 place_block）：

- `airbot_play + stack_block` → 专用 SimNode 后端
- 有 task YAML 的组合 → Universal 后端
- 无 YAML 的组合 → 静态场景预览

## 1. 环境准备

```bash
cd /home/ubuntu/data/discoverse-web-viewer
conda activate discoverse
pip install -e ".[web-teleop]"
```

如果只做前端静态语法检查，不需要启动仿真；如果要运行 MuJoCo 任务，必须在 `discoverse` 环境里执行。

## 2. 启动 Airbot Play

默认机器人是 `airbot_play`，默认任务是 `stack_block`。

```bash
cd /home/ubuntu/data/discoverse-web-viewer
conda activate discoverse
python web_viewer/server.py \
  --robot airbot_play \
  --task stack_block \
  --web-host 0.0.0.0 \
  --web-port 8765
```

浏览器打开：

```text
http://127.0.0.1:8765/
```

也可以显式指定：

```text
http://127.0.0.1:8765/?robot=airbot_play
```

## 3. 启动 UR5e Place Block

使用已有 XML：

```bash
cd /home/ubuntu/data/discoverse-web-viewer
conda activate discoverse
python web_viewer/server.py \
  --robot ur5e \
  --task place_block \
  --xml /home/ubuntu/data/discoverse-web-viewer/models/mjcf/tmp/ur5e_place_block.xml \
  --web-host 0.0.0.0 \
  --web-port 8765
```

浏览器打开：

```text
http://127.0.0.1:8765/
```

如果不传 `--xml`，后端会调用 `make_env("ur5e", "place_block")` 生成 XML：

```bash
python web_viewer/server.py --robot ur5e --task place_block --web-port 8765
```

## 4. URL 参数

默认只加载 `lab3` 环境 3DGS：

```text
http://127.0.0.1:8765/
```

加载更多环境对象：

```text
http://127.0.0.1:8765/?extras=1
```

指定 3DGS ply：

```text
http://127.0.0.1:8765/?splats=/models/3dgs/scene/lab3/point_cloud.gs3d.ply
```

显式指定机器人 renderer：

```text
http://127.0.0.1:8765/?robot=ur5e
```

调整 3DGS 环境整体高度，例如整体下移 2cm：

```text
http://127.0.0.1:8765/?robot=ur5e&gsZ=-0.02
```

调整 3DGS 环境完整平移：

```text
http://127.0.0.1:8765/?robot=ur5e&gsOffset=0,0,-0.02
```

调试建议从小步长开始：

```text
?gsZ=-0.01
?gsZ=-0.02
?gsZ=-0.03
```

如果 URL 没有 `robot` 参数，前端会读取：

```text
GET /api/config
```

并自动使用服务器当前 `--robot`。

## 5. API

### `/api/config`

查看当前服务器配置：

```bash
curl http://127.0.0.1:8765/api/config
```

示例返回：

```json
{
  "robot": "ur5e",
  "task": "place_block"
}
```

### `/api/state`

浏览器主状态接口：

```bash
curl http://127.0.0.1:8765/api/state
```

核心字段：

```json
{
  "ok": true,
  "time": 1.23,
  "robot": {
    "name": "ur5e",
    "base_pose": {
      "pos": [0.3, 1.0, 0.71],
      "quat_wxyz": [0.0, 0.0, 0.0, 1.0]
    },
    "joints": {
      "shoulder_pan_joint": 0.0,
      "shoulder_lift_joint": -1.57,
      "elbow_joint": 1.57,
      "wrist_1_joint": -1.57,
      "wrist_2_joint": -1.57,
      "wrist_3_joint": 0.0,
      "gripper": 0.0
    }
  },
  "objects": {
    "block_green": {
      "pos": [0.0, -0.15, 0.004],
      "quat_wxyz": [1.0, 0.0, 0.0, 0.0]
    }
  },
  "objects_frame": "robot_base"
}
```

### `/state`

兼容旧页面的接口。新代码优先使用 `/api/state`。

## 6. 前端模块说明

```text
web_viewer/static/index.html
web_viewer/static/js/app.js
web_viewer/static/js/core/hybrid_viewer.js
web_viewer/static/js/core/state_client.js
web_viewer/static/js/core/object_renderer.js
web_viewer/static/js/core/math.js
web_viewer/static/js/robots/robot_renderer.js
web_viewer/static/js/robots/registry.js
web_viewer/static/js/robots/airbot_play_renderer.js
web_viewer/static/js/robots/ur5e_renderer.js
```

职责：

- `app.js`：前端组装入口，创建 viewer、robot renderer、object renderer、state client。
- `hybrid_viewer.js`：Three.js、3DGS、主相机、PiP、渲染循环。
- `state_client.js`：轮询 `/api/state`，并兼容旧 `/state`。
- `object_renderer.js`：显示任务物体，例如方块、粉色碗。
- `robot_renderer.js`：机械臂 renderer 基类。
- `registry.js`：注册可用机器人。
- `airbot_play_renderer.js`：Airbot Play mesh、关节、腕部相机。
- `ur5e_renderer.js`：UR5e mesh、关节、简化夹爪。

## 7. 后端参数

```bash
python web_viewer/server.py --help
```

主要参数：

```text
--robot      当前支持 airbot_play / ur5e
--task       airbot_play 支持 stack_block；ur5e 支持 place_block
--xml        可选，直接加载已生成 MuJoCo XML
--randomize  默认关闭随机化；显式打开任务随机化
--no-random  关闭随机化（默认）
--web-host   默认 0.0.0.0
--web-port   默认 8765
```

Web Viewer 默认关闭随机化，避免无纹理资源时出现：

```text
Warning: TEXTURE_1K_PATH not found
```

如果确实需要纹理/光照/物体随机化：

```bash
python web_viewer/server.py --robot ur5e --task place_block --randomize
```

## 8. 常见问题

### 8.1 `gladLoadGL error`

原因：无显示器环境下创建了 MuJoCo OpenGL Renderer。

当前 `web_viewer` 的 UR5e 后端已经使用 headless 执行器，不会创建 `mujoco.Renderer`。如果又看到这个错误，说明启动的不是最新 `web_viewer/server.py`，或其他代码路径仍创建了 `mujoco.Renderer`。

排查：

```bash
rg "mujoco.Renderer" web_viewer examples/universal_tasks
```

### 8.2 夹爪看起来不完全真实

当前仓库里没有 UR5e WSG50 夹爪的实际 STL/OBJ mesh：

```bash
ls models/meshes/universal_robots_ur5e
```

所以 `ur5e_renderer.js` 使用了程序化简化夹爪。要完全真实，需要补齐 `WSG50_110`、`GUIDE_WSG50_110`、`WSG-FMF` 等 mesh，并在前端接入相应加载器。

### 8.3 碗不是完全真实 mesh

`bowl_pink.xml` 引用了 `object/bowl/part_*.STL`，但当前工作区没有这些 STL 文件，所以前端使用程序化开口碗形状。

检查：

```bash
ls models/meshes/object/bowl
```

如果补齐 STL，可以在 `object_renderer.js` 里接 `STLLoader` 加载真实碗。

### 8.4 页面一直请求 `/api/state`

这是正常行为。前端默认约 10Hz 轮询状态：

```text
web_viewer/static/js/core/state_client.js
```

如果日志太多，可以降低轮询频率：

```js
new StateClient({ pollMs: 200, ... })
```

## 9. 新增机器人

新增机器人需要三步：

1. 后端能输出统一 `/api/state`。
2. 前端新增 robot renderer。
3. 注册到 `registry.js`。

示例文件：

```text
web_viewer/static/js/robots/my_robot_renderer.js
```

最小结构：

```js
import * as THREE from "three";
import { RobotRenderer } from "./robot_renderer.js";
import { applyPose } from "../core/math.js";

export class MyRobotRenderer extends RobotRenderer {
  constructor() {
    super("my_robot");
    this.root = new THREE.Group();
  }

  async load({ scene, objLoader, status }) {
    if (status) status("加载 my_robot mesh...");
    scene.add(this.root);
  }

  applyState(robotState) {
    applyPose(this.root, robotState.base_pose);
  }

  getObjectFrame() {
    return this.root;
  }
}
```

注册：

```js
import { MyRobotRenderer } from "./my_robot_renderer.js";

const ROBOTS = {
  airbot_play: () => new AirbotPlayRenderer(),
  ur5e: () => new Ur5eRenderer(),
  my_robot: () => new MyRobotRenderer(),
};
```

## 10. 新增任务

新增 XML 任务建议先验证 `make_env`：

```bash
python - <<'PY'
from discoverse.envs import make_env

env = make_env("ur5e", "my_task", "models/mjcf/tmp/ur5e_my_task.xml")
print(env.test_mujoco_load())
PY
```

然后补：

```text
discoverse/configs/tasks/my_task.yaml
```

如果任务物体不在默认列表里，需要在：

```text
web_viewer/static/js/core/object_renderer.js
```

新增显示逻辑，并在后端：

```text
web_viewer/server.py
```

的 `TASK_OBJECT_NAMES` 中加入任务物体名。

## 11. 检查命令

Python 语法：

```bash
python -m py_compile web_viewer/server.py
```

前端 ES module 语法：

```bash
for f in \
  web_viewer/static/js/app.js \
  web_viewer/static/js/core/hybrid_viewer.js \
  web_viewer/static/js/core/object_renderer.js \
  web_viewer/static/js/robots/registry.js \
  web_viewer/static/js/robots/ur5e_renderer.js
do
  node --input-type=module --check < "$f" || exit 1
done
```

