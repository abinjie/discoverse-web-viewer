#!/usr/bin/env python3
"""
将 stack_block /web 所需的 3DGS ply 下载到 DISCOVERSE_ASSETS_DIR（默认：仓库下 models/），
并生成 *.gs3d.ply（浏览器小体积）与 *.webgs.ply（标准解码）。

说明：HF 上的资源多为 SuperSplat 压缩格式（chunk + packed_*）。浏览器 GaussianSplats3D 有两种用法：
  - 小文件：生成 *.gs3d.ply（仅插入 `element sh 0` 头补丁，见 patch_compressed_ply_for_gs3d.py），可直接加载压缩 ply；
  - 高质量 / 含完整 SH：用 gaussian_renderer 解码并保存为标准 *.webgs.ply。

前置：pip install huggingface_hub && hf auth login

无显示器服务器请先：export MUJOCO_GL=egl（导入 gaussian_renderer 时需要）
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# 在导入 gaussian_renderer 之前设置（其包 __init__ 会拉 MuJoCo）
os.environ.setdefault("MUJOCO_GL", "egl")

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TELEOP = Path(__file__).resolve().parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_TELEOP) not in sys.path:
    sys.path.insert(0, str(_TELEOP))

from discoverse import DISCOVERSE_ASSETS_DIR
from patch_compressed_ply_for_gs3d import patch_compressed_ply_for_gs3d
from discoverse.utils.download_from_huggingface import download_from_huggingface

# 与 examples/tasks_airbot_play/stack_block.py 中 gs_model_dict 一致（相对 3dgs/）
REL_PATHS = [
    "scene/lab3/point_cloud.ply",
    "hinge/drawer_1.ply",
    "hinge/drawer_2.ply",
    "object/bowl_pink.ply",
]


def write_gs3d_browser_stub(rel_path: str) -> Path | None:
    """无球谐的 SuperSplat vectorized ply → *.gs3d.ply，供 GaussianSplats3D 直接加载（体积小）。"""
    src = Path(DISCOVERSE_ASSETS_DIR) / "3dgs" / rel_path
    if not src.is_file():
        return None
    out = patch_compressed_ply_for_gs3d(src)
    if out.resolve() == src.resolve():
        return None
    print(f"[gs3d-browser] {src.name} -> {out.name}")
    return out


def write_webgs_variant(rel_path: str) -> Path:
    """从原始 ply（SuperSplat 或标准）生成 models/3dgs/.../<stem>.webgs.ply，供浏览器 splat 加载。"""
    from gaussian_renderer.core.util_gau import load_ply, save_ply

    src = Path(DISCOVERSE_ASSETS_DIR) / "3dgs" / rel_path
    if not src.is_file():
        print(f"[skip] 源文件不存在: {src}")
        return src

    dst = src.parent / f"{src.stem}.webgs.ply"
    print(f"[convert] {src.name} -> {dst.name} (SH<=2, 标准 3DGS PLY)")
    gd = load_ply(str(src))
    save_ply(gd, str(dst), save_sh_degree=2)
    return dst


def main() -> None:
    parser = argparse.ArgumentParser(description="下载 stack_block 环境 ply 并生成 .gs3d.ply / .webgs.ply")
    parser.add_argument(
        "--convert-only",
        action="store_true",
        help="不下载，只对已有 ply 生成/刷新 .gs3d.ply 与 .webgs.ply",
    )
    args = parser.parse_args()

    if args.convert_only:
        for rel in REL_PATHS:
            print(f"--- convert {rel}")
            write_gs3d_browser_stub(rel)
            write_webgs_variant(rel)
        print("完成。小体积预览可用 *.gs3d.ply；高质量可用 *.webgs.ply（见 /gs 与 /hybrid）。")
        return

    for rel in REL_PATHS:
        print(f"--- download {rel}")
        download_from_huggingface(rel)
        write_gs3d_browser_stub(rel)
        write_webgs_variant(rel)

    print("完成。例如：/models/3dgs/scene/lab3/point_cloud.gs3d.ply（小）或 point_cloud.webgs.ply（标准）")


if __name__ == "__main__":
    main()
