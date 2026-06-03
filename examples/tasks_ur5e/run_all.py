#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量运行 UR5e 通用任务。"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

from run_task import TASKS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="批量运行 UR5e 任务")
    parser.add_argument("--headless", action="store_true", help="无 GUI 模式运行")
    parser.add_argument("-s", "--sync", action="store_true", help="启用实时同步")
    parser.add_argument("--continue-on-error", action="store_true", help="单个任务失败后继续运行后续任务")
    parser.add_argument("tasks", nargs="*", choices=TASKS, help="不指定时运行全部任务")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tasks = args.tasks or TASKS
    script = os.path.join(os.path.dirname(__file__), "run_task.py")

    for task in tasks:
        cmd = [sys.executable, script, "-t", task, "-1"]
        if args.headless:
            cmd.append("--headless")
        if args.sync:
            cmd.append("--sync")

        print(f"\n=== 运行 UR5e 任务: {task} ===")
        result = subprocess.run(cmd, cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
        if result.returncode != 0 and not args.continue_on_error:
            raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
