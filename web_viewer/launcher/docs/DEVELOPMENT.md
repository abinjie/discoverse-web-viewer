# 开发指南

## 1. 本地环境

```bash
cd /home/ubuntu/data/discoverse-web-viewer
conda activate discoverse
pip install -e ".[web-teleop]"
```

## 2. 启动开发服务

**终端 1 — Launcher：**

```bash
python -m web_viewer.launcher --host 0.0.0.0 --port 8080 --public-host 127.0.0.1
```

**终端 2 — 单独调试 Viewer（可选）：**

```bash
python web_viewer/server.py --robot ur5e --task place_block --web-port 8765
```

## 3. 语法检查

```bash
# Python
python -m py_compile web_viewer/server.py
python -m py_compile web_viewer/launcher/app.py
python -m py_compile web_viewer/launcher/catalog/scanner.py
python -m py_compile web_viewer/launcher/session/manager.py

# Catalog 冒烟
python -c "
from web_viewer.launcher.catalog.scanner import scan_catalog, check_compatibility
c = scan_catalog()
print('robots', len(c['robots']), 'tasks', len(c['tasks']))
print(check_compatibility('ur5e', 'place_block'))
"

# 前端 ES module
node --input-type=module --check < web_viewer/static/js/app.js
node --input-type=module --check < web_viewer/static/js/core/hybrid_viewer.js
node --input-type=module --check < web_viewer/launcher/static/launcher.js
```

## 4. 模块职责

### `catalog/scanner.py`

| 符号 | 职责 |
|------|------|
| `ROBOT_WHITELIST` | Launcher 可选机械臂（2 个） |
| `TASK_LABELS` | 任务 ID → 中文名 |
| `GS_ASSET_DEFS` | GS 资产定义与文件探测 |
| `scan_catalog()` | 组装完整 Catalog |
| `check_compatibility()` | `make_env` + headless `MjModel.from_xml_path`（不创建 OpenGL Renderer） |
| `resolve_runtime()` | dedicated / universal / static_preview |

**扩展新机械臂到 Launcher：**

1. 在 `ROBOT_WHITELIST` 增加条目
2. 确保 `models/mjcf/manipulator/robot_{id}.xml` 存在
3. 确保 `discoverse/configs/robots/{id}.yaml` 存在
4. 前端 `static/js/robots/` 新增 renderer 并注册到 `registry.js`

**扩展新任务（自动）：**

- 添加 `models/mjcf/task_environments/{task}.xml` 即可被 `list_available_tasks()` 发现
- 可选：在 `TASK_LABELS` 补中文名

### `session/manager.py`

| 符号 | 职责 |
|------|------|
| `SessionManager.create_session()` | 写 JSON → spawn server.py → 健康检查 |
| `_allocate_port()` | 8765–8799 端口池 |
| `_viewer_url()` | 构造带 query 的 Viewer URL |
| `stop_session()` | SIGTERM 子进程 |

**健康检查：** 轮询 `GET http://127.0.0.1:{port}/api/config`，超时 90s。

### `session/models.py`

- `SessionConfig`：会话配置 dataclass，JSON 序列化
- `SessionRecord`：运行时记录（port、pid、status）

### `app.py`

Launcher FastAPI 路由，见 [API.md](./API.md)。

### `server.py` 改动要点

| 改动 | 说明 |
|------|------|
| `--session-config` | 从 JSON 加载 robot/task/xml/randomize/sync |
| `_resolve_runtime()` | 仿真后端路由 |
| `_run_static_preview_sim()` | 无 YAML 任务的预览模式 |
| `_static_preview_node_state()` | 从 qpos 读关节状态 |
| `/api/config` 扩展 | 返回 enable_gs、runtime、session_id |
| 移除 robot/task 硬编码限制 | 支持任意 make_env 组合 |

### 前端

| 文件 | 改动 |
|------|------|
| `static/js/app.js` | `shouldEnableGs()`、`fetchViewerConfig()` |
| `static/js/core/hybrid_viewer.js` | `enableMeshOnlyMode()` |
| `launcher/static/launcher.js` | Catalog 表单、POST /api/sessions |

## 5. 新增任务 YAML（static → universal）

以 `open_drawer` 为例：

1. 创建 `discoverse/configs/tasks/open_drawer.yaml`（可参考现有任务或模板）
2. 本地验证：

```bash
python -c "
from discoverse.envs import make_env
env = make_env('ur5e', 'open_drawer', 'models/mjcf/tmp/ur5e_open_drawer.xml')
assert env.test_mujoco_load()
"
```

3. 通过 Launcher 启动，确认 runtime 标签变为 universal
4. 在 `TASK_OBJECT_NAMES` 添加该任务涉及的 MuJoCo body 名

## 6. 调试技巧

### 查看 Session JSON

```bash
ls models/mjcf/tmp/sessions/
cat models/mjcf/tmp/sessions/<id>.json
```

### 手动用 Session 配置启动 Viewer

```bash
python web_viewer/server.py \
  --session-config models/mjcf/tmp/sessions/<id>.json \
  --web-port 8765
```

### 查看 Viewer 状态

```bash
curl -s http://127.0.0.1:8765/api/config | python -m json.tool
curl -s http://127.0.0.1:8765/api/state | python -m json.tool
```

### 子进程日志

`SessionManager` 当前将子进程 stdout 重定向到 PIPE。调试时可临时改为 `stdout=None` 让日志直接打印到终端。

### make_env 批量测试

```bash
python discoverse/envs/make_env.py --all --robot ur5e
```

## 7. 已知限制（P0）

1. **单 Launcher 多会话**：端口池 8765–8799，最多约 35 个并发 Viewer
2. **static_preview 任务**：无自动状态机，仅场景与 mesh 预览
3. **物体 mesh**：部分任务物体为程序化几何，非全部真实 STL
4. **GS 资产**：需本地存在 PLY，否则 Launcher 中显示不可用
5. **setuptools**：`web_viewer` 不在 pip 包内，需从仓库根目录运行 `python -m web_viewer.launcher`

## 8. 建议提交检查清单

- [ ] `python -m py_compile` 通过
- [ ] `scan_catalog()` 返回 2 robots、13 tasks
- [ ] `check_compatibility('ur5e','place_block')['ok'] == True`
- [ ] Launcher 页能启动 Mesh 会话并打开 Viewer
- [ ] `/api/state` 返回 ok
- [ ] 文档与代码行为一致

## 9. 相关文件索引

```
discoverse/envs/make_env.py              # make_env, list_available_*
discoverse/configs/robots/*.yaml         # 机器人配置
discoverse/configs/tasks/*.yaml          # 任务状态机
examples/universal_tasks/universal_task_runtime.py
examples/tasks_airbot_play/stack_block.py
web_viewer/server.py
web_viewer/static/js/
web_viewer/launcher/
```
