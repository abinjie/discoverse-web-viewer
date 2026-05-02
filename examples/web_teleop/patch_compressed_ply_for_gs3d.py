#!/usr/bin/env python3
"""
GaussianSplats3D (@mkkellogg/gaussian-splats-3d) 的 PlayCanvas 压缩 ply 解析器会无条件读取 `sh` 元素；
SuperSplat vectorized 导出若仅有 chunk + vertex（无球谐），浏览器里会直接报错 / 无法渲染。

在 ASCII 头里、`end_header` 这一行之前插入 `element sh 0`，解析器即可跳过（零顶点），文件体积几乎不变。

用法：
  python examples/web_teleop/patch_compressed_ply_for_gs3d.py models/3dgs/scene/lab3/point_cloud.ply
  python examples/web_teleop/patch_compressed_ply_for_gs3d.py src.ply -o dst.gs3d.ply
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def _find_end_header(data: bytes) -> tuple[int, int]:
    """返回 (end_header 起始下标, header 之后二进制正文起始下标)。"""
    for marker in (b"end_header\n", b"end_header\r\n"):
        idx = data.find(marker)
        if idx != -1:
            return idx, idx + len(marker)
    raise ValueError("PLY end_header 未找到（文件损坏或非 ply）")


def needs_gs3d_sh_stub(header_ascii: str) -> bool:
    if "element chunk" not in header_ascii or "packed_position" not in header_ascii:
        return False
    for line in header_ascii.splitlines():
        stripped = line.strip()
        if stripped.startswith("element sh ") or stripped.startswith("element sh\t"):
            return False
    return True


def patch_compressed_ply_for_gs3d(src: Path, dst: Path | None = None, inplace: bool = False) -> Path:
    """
    若为目标格式且无 `element sh`，则在 end_header 行前插入 `element sh 0`。
    返回写入的路径。
    """
    data = src.read_bytes()
    eh_start, _body_start = _find_end_header(data)
    header_ascii = data[:eh_start].decode("ascii", errors="strict")

    if not needs_gs3d_sh_stub(header_ascii):
        if inplace:
            return src
        out = dst or src
        if out != src:
            shutil.copy2(src, out)
        return out

    insert = b"element sh 0\n"
    head = data[:eh_start]
    tail = data[eh_start:]  # end_header\n + 二进制正文
    new_data = head + insert + tail

    target = src if inplace else (dst or src.with_name(f"{src.stem}.gs3d{src.suffix}"))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(new_data)
    return target


def main() -> None:
    p = argparse.ArgumentParser(description="为无 sh 的 SuperSplat 压缩 ply 打 GaussianSplats3D 兼容头")
    p.add_argument("ply", type=Path, help="输入 .ply")
    p.add_argument("-o", "--output", type=Path, default=None, help="输出路径（默认：<stem>.gs3d.ply）")
    p.add_argument("--inplace", action="store_true", help="原地改写（慎用）")
    args = p.parse_args()

    out = patch_compressed_ply_for_gs3d(args.ply, dst=args.output, inplace=args.inplace)
    print(f"OK -> {out}")


if __name__ == "__main__":
    main()
