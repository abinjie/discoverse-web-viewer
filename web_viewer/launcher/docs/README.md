# DISCOVERSE Web Viewer Launcher 文档

本目录包含 **Launcher（配置页 + 会话调度）** 的完整开发与使用文档。

Launcher 用于替代手动执行 `python web_viewer/server.py --robot ... --task ...`，通过浏览器表单选择机械臂、任务、渲染模式后一键启动 Viewer。

## 文档索引

| 文档 | 说明 |
|------|------|
| [USER_GUIDE.md](./USER_GUIDE.md) | 安装、启动、远程访问、常见问题 |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 系统架构、模块职责、数据流 |
| [API.md](./API.md) | Launcher REST API 与 Viewer `/api/config` 扩展 |
| [RUNTIME_MATRIX.md](./RUNTIME_MATRIX.md) | 机械臂 × 任务 × 仿真后端能力矩阵 |
| [DEVELOPMENT.md](./DEVELOPMENT.md) | 本地开发、扩展、调试、目录结构 |

## 快速开始

```bash
cd /home/ubuntu/data/discoverse-web-viewer
conda activate discoverse
pip install -e ".[web-teleop]"

# 远程浏览器访问时替换为本机 IP
python -m web_viewer.launcher --host 0.0.0.0 --port 8080 --public-host 127.0.0.1
```

浏览器打开：`http://<IP>:8080/launcher`

## 与 make_env 的关系

- **任务列表**来自 `discoverse.envs.list_available_tasks()`，扫描 `models/mjcf/task_environments/*.xml`
- **机械臂**Launcher 白名单：`airbot_play`、`ur5e`（与前端 mesh renderer 一致）
- **MJCF 生成**在创建会话时调用 `make_env(robot, task, xml_path)` 并执行 `test_mujoco_load()`

详见 [discoverse/doc/envs/make_env_usage_zh.md](../../../discoverse/doc/envs/make_env_usage_zh.md)。

## 代码入口

```
web_viewer/launcher/
├── __main__.py          # python -m web_viewer.launcher
├── app.py               # Launcher FastAPI 应用
├── catalog/scanner.py   # 资源扫描与兼容性检查
├── session/manager.py   # 子进程 Viewer 会话管理
├── static/              # Launcher 前端
└── docs/                # 本目录
```
