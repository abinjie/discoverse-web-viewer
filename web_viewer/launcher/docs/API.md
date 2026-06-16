# Launcher API 参考

Base URL：`http://<host>:8080`（默认端口 8080）

Content-Type：JSON

---

## Catalog

### `GET /api/catalog`

返回 Launcher 可选资源全量目录。

**响应示例：**

```json
{
  "robots": [
    {
      "id": "airbot_play",
      "label": "AirBot Play",
      "description": "AirBot Play 6-DOF 桌面协作机械臂",
      "has_mesh_renderer": true
    },
    {
      "id": "ur5e",
      "label": "Universal Robots UR5e",
      "description": "Universal Robots UR5e 6-DOF 工业机械臂",
      "has_mesh_renderer": true
    }
  ],
  "tasks": [
    {
      "id": "place_block",
      "label": "放置积木",
      "has_yaml": true,
      "runtime": "universal",
      "runtime_label": "可自动运行（Universal 任务状态机）",
      "gs_hints": ["bowl_pink"]
    }
  ],
  "gs_assets": [
    {
      "id": "lab3",
      "group": "scene",
      "label": "Lab3 背景场景",
      "url": "/models/3dgs/scene/lab3/point_cloud.gs3d.ply",
      "available": true,
      "default_for_gs": true
    }
  ],
  "defaults": {
    "robot": "airbot_play",
    "task": "stack_block",
    "enable_gs": false,
    "gs_scene": "lab3"
  }
}
```

---

### `GET /api/catalog/compatibility`

检查 `robot + task` 能否通过 `make_env` 生成并加载 MJCF。

**Query 参数：**

| 参数 | 必填 | 说明 |
|------|------|------|
| `robot` | 是 | `airbot_play` 或 `ur5e` |
| `task` | 是 | 任务 ID |

**示例：**

```bash
curl "http://127.0.0.1:8080/api/catalog/compatibility?robot=ur5e&task=place_block"
```

**成功响应：**

```json
{
  "ok": true,
  "robot": "ur5e",
  "task": "place_block",
  "mjcf_ok": true,
  "xml_path": "/path/to/models/mjcf/tmp/ur5e_place_block.xml",
  "runtime": "universal",
  "runtime_label": "可自动运行（Universal 任务状态机）",
  "mesh_renderer": true,
  "gs_hints": ["bowl_pink"],
  "error": null
}
```

**失败响应（组合不可用）：**

```json
{
  "ok": false,
  "robot": "ur5e",
  "task": "invalid_task",
  "error": "未知任务: invalid_task"
}
```

---

## Sessions

### `POST /api/sessions`

创建 Viewer 会话并启动子进程。

**请求体：**

```json
{
  "robot": "ur5e",
  "task": "place_block",
  "enable_gs": false,
  "gs_scene": "lab3",
  "gs_assets": ["bowl_pink"],
  "gs_offset": [0, 0, -0.02],
  "randomize": false,
  "sync": false
}
```

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `robot` | string | 必填 | `airbot_play` \| `ur5e` |
| `task` | string | 必填 | `list_available_tasks()` 中的 ID |
| `enable_gs` | bool | `false` | 是否启用 GS 环境渲染 |
| `gs_scene` | string | `lab3` | GS 背景场景 ID |
| `gs_assets` | string[] | `[]` | 额外 GS 物体 ID（非 scene 组） |
| `gs_offset` | float[3] | `[0,0,0]` | GS 平移，写入 viewer URL |
| `randomize` | bool | `false` | Universal 任务 reset 随机化 |
| `sync` | bool | `false` | 仿真步长同步墙钟 |

**成功响应 `201`（实际返回 200）：**

```json
{
  "session_id": "a1b2c3d4",
  "status": "running",
  "port": 8765,
  "pid": 12345,
  "viewer_url": "http://127.0.0.1:8765/?robot=ur5e&render=mesh",
  "created_at": 1718534400.0,
  "config": {
    "robot": "ur5e",
    "task": "place_block",
    "enable_gs": false,
    "runtime": "universal",
    "xml_path": "..."
  }
}
```

**错误：**

- `400`：`make_env` 或兼容性检查失败
- `500`：端口耗尽或 Viewer 健康检查超时（90s）

---

### `GET /api/sessions`

列出活跃会话（`starting` / `running`）。

```bash
curl http://127.0.0.1:8080/api/sessions
```

---

### `GET /api/sessions/{session_id}`

获取单个会话详情。

---

### `DELETE /api/sessions/{session_id}`

停止指定 Viewer 子进程。

```bash
curl -X DELETE http://127.0.0.1:8080/api/sessions/a1b2c3d4
```

---

### `DELETE /api/sessions`

停止全部会话。

---

## Viewer API 扩展（server.py）

Launcher 启动的 Viewer 在原有 API 基础上扩展 `/api/config`：

### `GET /api/config`

```json
{
  "robot": "ur5e",
  "task": "place_block",
  "enable_gs": false,
  "gs_assets": ["lab3"],
  "gs_offset": [0, 0, 0],
  "runtime": "universal",
  "session_id": "a1b2c3d4"
}
```

前端 `app.js` 读取此配置决定：

- `enable_gs` → 是否调用 `initSplats`
- URL 参数 `render=mesh` / `gs=0` 优先级高于 config

### `GET /api/state`

不变，见 [web_viewer/README.md](../../README.md)。

---

## Session 配置文件格式

路径：`models/mjcf/tmp/sessions/{session_id}.json`

由 Launcher 写入，`server.py --session-config` 读取：

```json
{
  "robot": "ur5e",
  "task": "place_block",
  "enable_gs": false,
  "gs_scene": "lab3",
  "gs_assets": [],
  "gs_offset": [0, 0, 0],
  "randomize": false,
  "sync": false,
  "xml_path": "/abs/path/to/models/mjcf/tmp/ur5e_place_block.xml",
  "session_id": "a1b2c3d4",
  "runtime": "universal"
}
```
