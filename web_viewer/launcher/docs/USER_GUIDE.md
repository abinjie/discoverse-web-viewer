# 用户指南

## 1. 环境要求

- Python 3.10+（与 `discoverse` conda 环境一致）
- 已安装 DISCOVERSE 及 web 依赖：

```bash
cd /home/ubuntu/data/discoverse-web-viewer
conda activate discoverse
pip install -e ".[web-teleop]"
```

- `DISCOVERSE_ASSETS_DIR` 指向包含 `mjcf/`、`meshes/`、`3dgs/` 的 `models` 目录（默认仓库内 `models/`）
- GS 渲染可选：需存在 `models/3dgs/**/*.gs3d.ply` 或 `.webgs.ply`（可用 `examples/web_teleop/download_gs_assets_for_web.py` 准备）

## 2. 启动 Launcher

### 本机访问

```bash
python -m web_viewer.launcher --host 0.0.0.0 --port 8080
```

打开：`http://127.0.0.1:8080/launcher`

### 远程 / 云服务器访问

Viewer 子进程绑定 `0.0.0.0`，但返回的链接默认用 `127.0.0.1`。远程浏览器需指定 `--public-host`：

```bash
python -m web_viewer.launcher \
  --host 0.0.0.0 \
  --port 8080 \
  --public-host 192.168.1.100 \
  --viewer-bind-host 0.0.0.0
```

将 `192.168.1.100` 换成你的机器 IP 或域名。

### 命令行参数

| 参数 | 默认 | 说明 |
|------|------|------|
| `--host` | `0.0.0.0` | Launcher 监听地址 |
| `--port` | `8080` | Launcher 端口 |
| `--public-host` | `127.0.0.1` | 写入 `viewer_url` 的主机名 |
| `--viewer-bind-host` | `0.0.0.0` | Viewer 子进程绑定地址 |

## 3. 使用 Launcher 页面

1. **选择机械臂**：AirBot Play 或 UR5e
2. **选择任务**：来自 `make_env` 的 13 个任务场景
3. **渲染模式**：
   - **Mesh（默认）**：不加载 3DGS，显示 grid + 桌面占位 + 机械臂/物体 mesh
   - **GS**：加载所选 GS 背景与数字资产
4. 点击 **启动 Viewer**，新标签页打开仿真页面
5. 在 **活跃会话** 面板可再次打开或停止会话

### 任务运行状态提示

| 页面提示 | 含义 |
|----------|------|
| 可自动运行（Universal 任务状态机） | 有 `discoverse/configs/tasks/{task}.yaml`，机械臂会自动执行任务 |
| 可自动运行（AirBot 专用后端） | `airbot_play + stack_block` 专用 18 状态逻辑 |
| 仅场景预览 | MJCF 可加载，但无任务 YAML，机械臂保持初始姿态，仅用于场景/渲染预览 |

## 4. 仍可直接使用 CLI（不经过 Launcher）

```bash
# AirBot 叠方块
python web_viewer/server.py --robot airbot_play --task stack_block --web-port 8765

# UR5e 放方块
python web_viewer/server.py --robot ur5e --task place_block --web-port 8765
```

Launcher 启动的 Viewer 等价于：

```bash
python web_viewer/server.py \
  --session-config models/mjcf/tmp/sessions/<session_id>.json \
  --web-port <allocated_port>
```

## 5. Viewer URL 参数（Mesh / GS）

Launcher 会自动附加参数；手动访问时可使用：

| 参数 | 说明 |
|------|------|
| `?render=mesh` | 强制 Mesh，不加载 GS |
| `?render=gs` 或 `?gs=1` | 强制尝试加载 GS |
| `?splats=url1,url2` | 指定 GS PLY URL 列表 |
| `?gsOffset=x,y,z` | GS 环境平移 |
| `?robot=ur5e` | 指定前端 robot renderer |

## 6. 常见问题

### 6.1 启动 Viewer 超时

**原因**：MuJoCo 加载 XML 失败、端口被占用、或 conda 环境未激活。

**排查**：

```bash
# 手动测试组合
python -c "
from discoverse.envs import make_env
env = make_env('ur5e', 'place_block', 'models/mjcf/tmp/test.xml')
print('ok', env.test_mujoco_load())
"

# 检查端口
ss -tlnp | grep 876
```

### 6.2 GS 资产灰色不可选

**原因**：对应 PLY 文件不存在。

**解决**：

```bash
python examples/web_teleop/download_gs_assets_for_web.py
```

### 6.3 远程打开 Viewer 连不上

**原因**：`viewer_url` 使用了 `127.0.0.1`。

**解决**：Launcher 加 `--public-host <服务器IP>`，并确保安全组/防火墙放行 Viewer 端口（8765–8799）。

### 6.4 任务无自动动作

**原因**：该任务属于「仅场景预览」，尚未提供 `discoverse/configs/tasks/{task}.yaml`。

**解决**：参考 [DEVELOPMENT.md](./DEVELOPMENT.md) 新增任务 YAML，或先用有 YAML 的任务（如 `place_block`、`stack_block`）。
