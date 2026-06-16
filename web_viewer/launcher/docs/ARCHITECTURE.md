# 系统架构

## 1. 设计目标

| 目标 | 方案 |
|------|------|
| 替代长 CLI 命令 | Launcher Web UI + Session 子进程 |
| 任务与机械臂组合 | `make_env(robot, task)` 动态生成 MJCF |
| 机械臂范围 | 白名单 `airbot_play`、`ur5e` |
| GS / Mesh | 用户选择；默认 Mesh |
| 仿真与渲染解耦 | Python headless MuJoCo + 浏览器 Three.js / 3DGS |

## 2. 总体架构

```
┌─────────────────────────────────────────────────────────────┐
│  python -m web_viewer.launcher  (:8080)                      │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐ │
│  │ catalog/    │  │ session/     │  │ static/launcher.*   │ │
│  │ scanner.py  │  │ manager.py   │  │ 配置表单 UI          │ │
│  └──────┬──────┘  └──────┬───────┘  └─────────────────────┘ │
│         │                │ spawn subprocess                  │
└─────────┼────────────────┼──────────────────────────────────┘
          │                ▼
          │     ┌──────────────────────────────────────────┐
          │     │  web_viewer/server.py  (:8765+)         │
          │     │  ├─ MuJoCo 仿真线程（headless）           │
          │     │  ├─ GET /api/state                       │
          │     │  └─ static/index.html + HybridViewer     │
          │     └──────────────────────────────────────────┘
          │
          ▼
   make_env + list_available_tasks
   models/mjcf/task_environments/*.xml
   models/mjcf/manipulator/robot_*.xml
```

## 3. 进程模型

- **Launcher 进程**：常驻，不跑 MuJoCo
- **Viewer 进程**：每个会话一个 `subprocess`，独立端口（8765–8799）
- **停止会话**：向 Viewer 子进程发 `SIGTERM`，释放端口

选择 subprocess 而非单进程多会话的原因：

1. 现有 `server.py` 使用全局 `STATE` 单例 + 单仿真线程
2. 子进程隔离：Viewer 崩溃不影响 Launcher
3. P0 实现成本最低

## 4. 创建会话流程

```
用户点击「启动 Viewer」
    → POST /api/sessions { robot, task, enable_gs, ... }
    → check_compatibility(robot, task)
         → make_env(robot, task, tmp/{robot}_{task}.xml)
         → env.test_mujoco_load()
    → 写入 models/mjcf/tmp/sessions/{id}.json
    → subprocess: python web_viewer/server.py --session-config ... --web-port N
    → 轮询 GET http://127.0.0.1:N/api/config 直到 200
    → 返回 viewer_url（含 ?robot=...&render=mesh 或 splats=...）
```

## 5. 仿真后端路由（server.py）

```python
runtime = _resolve_runtime(robot, task)

if runtime == "dedicated":      # airbot_play + stack_block
    _run_airbot_stack_sim()
elif runtime == "universal":    # 存在 tasks/{task}.yaml
    _run_universal_task_sim()
else:                           # static_preview
    _run_static_preview_sim()
```

| runtime | 条件 | 行为 |
|---------|------|------|
| `dedicated` | `airbot_play` + `stack_block` | 硬编码 18 状态 SimNode |
| `universal` | `discoverse/configs/tasks/{task}.yaml` 存在 | UniversalRuntimeTaskExecutor |
| `static_preview` | 仅有 MJCF，无 YAML | `mj_forward` 循环，无状态机 |

## 6. 浏览器渲染架构

| 层 | 技术 | 内容 |
|----|------|------|
| 环境 | 3DGS（可选） | lab3 背景、抽屉、碗等 PLY |
| 机械臂 | Three.js OBJ mesh | `airbot_play_renderer` / `ur5e_renderer` |
| 任务物体 | Three.js 程序化几何 | `object_renderer.js` |
| 状态同步 | 轮询 `/api/state` ~10Hz | `state_client.js` |

**Mesh 模式**：`initSplats([])` → `enableMeshOnlyMode()`，显示 grid + 桌面占位。

**GS 模式**：加载 PLY 列表，环境 GS + mesh 机械臂/物体叠加。

Python 仿真端在 web_viewer 中**不参与渲染**（`enable_render=False`）。

## 7. 目录结构

```
web_viewer/
├── server.py                 # Viewer 服务（仿真 + API + 静态页）
├── static/                   # Viewer 前端（Three.js）
│   └── js/app.js             # 读取 /api/config 决定 GS/Mesh
└── launcher/
    ├── app.py                # Launcher FastAPI
    ├── catalog/scanner.py    # Catalog + compatibility
    ├── session/
    │   ├── models.py         # SessionConfig dataclass
    │   └── manager.py        # 端口池 + subprocess
    ├── static/               # Launcher 前端
    └── docs/                 # 文档
```

## 8. 配置与资产路径

| 类型 | 路径 |
|------|------|
| 机械臂 MJCF | `models/mjcf/manipulator/robot_{name}.xml` |
| 任务 MJCF | `models/mjcf/task_environments/{task}.xml` |
| 合并输出 | `models/mjcf/tmp/{robot}_{task}.xml` |
| 会话配置 | `models/mjcf/tmp/sessions/{session_id}.json` |
| 机器人 YAML | `discoverse/configs/robots/{robot}.yaml` |
| 任务 YAML | `discoverse/configs/tasks/{task}.yaml` |
| GS 资产 | `models/3dgs/**/{*.gs3d.ply,*.webgs.ply}` |
| Mesh 资产 | `models/meshes/**` |

## 9. 扩展点

| 需求 | 修改位置 |
|------|----------|
| 新增机械臂（Launcher 可选） | `catalog/scanner.py` ROBOT_WHITELIST + `registry.js` + robot renderer |
| 新增任务（自动出现在列表） | 添加 `task_environments/{task}.xml` |
| 任务可自动运行 | 添加 `discoverse/configs/tasks/{task}.yaml` |
| 新增 GS 资产选项 | `catalog/scanner.py` GS_ASSET_DEFS |
| 任务物体 mesh 显示 | `server.py` TASK_OBJECT_NAMES + `object_renderer.js` |

## 10. 后续演进（P2+）

- 单端口多会话（in-process session 隔离）
- Launcher 反向代理 `/viewer/{id}/` 统一入口
- 按任务自动推导 GS 资产与物体列表
- `stack_two_colors_of_blocks` 等文档任务补齐 XML 后自动出现在 Catalog
