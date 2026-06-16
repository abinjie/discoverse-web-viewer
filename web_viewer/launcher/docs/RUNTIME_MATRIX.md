# 运行时能力矩阵

机械臂固定为 **AirBot Play**（`airbot_play`）与 **UR5e**（`ur5e`）。

任务来自 `list_available_tasks()`（`models/mjcf/task_environments/*.xml`）。

## 1. 仿真后端分类

| runtime | 说明 | 机械臂是否自动动 |
|---------|------|------------------|
| `dedicated` | 仅 `airbot_play + stack_block` | 是（18 状态硬编码） |
| `universal` | 存在 `discoverse/configs/tasks/{task}.yaml` | 是（YAML 状态机） |
| `static_preview` | MJCF 可加载，无任务 YAML | 否（初始姿态预览） |

## 2. 任务 × 后端（两机械臂相同逻辑）

| 任务 ID | 中文 | runtime | 有 task YAML |
|---------|------|---------|--------------|
| `stack_block` | 堆叠积木 | airbot→`dedicated`；ur5e→`universal` | 是 |
| `place_block` | 放置积木 | `universal` | 是 |
| `place_coffeecup` | 放置咖啡杯 | `universal` | 是 |
| `place_kiwi_fruit` | 放置猕猴桃 | `universal` | 是 |
| `cover_cup` | 盖杯子 | `universal` | 是 |
| `block_bridge_place` | 积木桥放置 | `static_preview` | 否 |
| `close_laptop` | 关闭笔记本电脑 | `static_preview` | 否 |
| `open_drawer` | 开抽屉 | `static_preview` | 否 |
| `pick_jujube` | 拾取枣子 | `static_preview` | 否 |
| `place_jujube` | 放置枣子 | `static_preview` | 否 |
| `place_jujube_coffeecup` | 枣子放咖啡杯 | `static_preview` | 否 |
| `push_mouse` | 推鼠标 | `static_preview` | 否 |
| `peg_in_hole` | 轴孔装配 | `static_preview` | 否 |

> 注：文档中的 `stack_two_colors_of_blocks` 当前仓库**无**对应 XML，不会出现在 Launcher 列表。

## 3. 特殊组合说明

### airbot_play + stack_block

- **不走** Universal，使用 `examples/tasks_airbot_play/stack_block.py` 的 `SimNode`
- 状态 API 返回 `block_red`、`block_green`、`block_blue`

### ur5e + stack_block

- 使用 `discoverse/configs/tasks/stack_block.yaml` + Universal 执行器
- 与 airbot 专用逻辑独立

## 4. 前端 Mesh Renderer

| 机械臂 | registry.js | mesh 路径 |
|--------|-------------|-----------|
| `airbot_play` | 已注册 | `models/meshes/airbot_play/*.obj` |
| `ur5e` | 已注册 | `models/meshes/universal_robots_ur5e/*.obj`（夹爪程序化） |

两机械臂在 Launcher 中 `has_mesh_renderer: true`。

## 5. 任务物体（/api/state objects）

当前 `server.py` 的 `TASK_OBJECT_NAMES` 覆盖：

| 任务 | 物体 body 名 |
|------|--------------|
| `stack_block` | `block_red`, `block_green`, `block_blue` |
| `place_block` | `block_green`, `bowl_pink` |
| `cover_cup` | `cup`, `lid` |
| `place_coffeecup` | `coffeecup`, `plate_white` |
| `place_kiwi_fruit` | `kiwi_fruit`, `bowl_flower` |

其他任务的物体需在 `object_renderer.js` 中扩展才会在浏览器显示。

## 6. GS 资产推荐（gs_hints）

| 任务 | 推荐 GS 资产 ID |
|------|-----------------|
| `place_block` | `bowl_pink` |
| `open_drawer` | `drawer_1`, `drawer_2` |
| `stack_block` | `drawer_1`, `drawer_2` |

Launcher 选择任务后会自动勾选对应 hint（若资产文件存在）。

## 7. 如何让 static_preview 升级为 universal

1. 在 `discoverse/configs/tasks/` 新增 `{task}.yaml`（可参考 `place_block.yaml` 继承 `templates/place_object.yaml`）
2. 确认 `UniversalRuntimeTaskExecutor` 能加载并执行
3. 更新 `TASK_OBJECT_NAMES` 与 `object_renderer.js`
4. 重新打开 Launcher，任务 runtime 标签会自动变为「可自动运行」

验证命令：

```bash
python examples/universal_tasks/universal_task_runtime.py -r ur5e -t place_block --headless --once
```
