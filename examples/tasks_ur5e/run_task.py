#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UR5e 通用任务入口。

这些任务复用 discoverse.envs.make_env 生成的 UR5e + task MJCF，
并通过 examples/universal_tasks/universal_task_runtime.py 执行。
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Sequence

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
UNIVERSAL_TASKS_DIR = os.path.join(REPO_ROOT, "examples", "universal_tasks")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if UNIVERSAL_TASKS_DIR not in sys.path:
    sys.path.insert(0, UNIVERSAL_TASKS_DIR)

from universal_task_runtime import main as run_universal_task

ROBOT_NAME = "ur5e"
TASKS = (
    "place_block",
    "stack_block",
    "cover_cup",
    "place_kiwi_fruit",
    "place_coffeecup",
    "close_laptop",
)


def run_task(task_name: str, *, sync: bool = False, once: bool = False, headless: bool = False) -> None:
    if task_name not in TASKS:
        raise ValueError(f"不支持的 UR5e 任务: {task_name}; 可选: {', '.join(TASKS)}")
    run_universal_task(ROBOT_NAME, task_name, sync=sync, once=once, headless=headless)


def parse_args(argv: Sequence[str] | None = None, default_task: str = "place_block") -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="运行 UR5e 通用任务")
    parser.add_argument("-t", "--task", choices=TASKS, default=default_task, help="任务名称")
    parser.add_argument("-s", "--sync", action="store_true", help="启用实时同步")
    parser.add_argument("-1", "--once", action="store_true", help="单次执行后退出")
    parser.add_argument("--headless", action="store_true", help="无 GUI 模式运行")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    run_task(args.task, sync=args.sync, once=args.once, headless=args.headless)


def run_fixed_task(task_name: str, argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv, default_task=task_name)
    run_task(args.task, sync=args.sync, once=args.once, headless=args.headless)


if __name__ == "__main__":
    main()
