#!/usr/bin/env python3
"""Utility for running post-`gd` automation hooks.

This script locates executable hook files stored under ``scripts/gd_hooks``
and runs them sequentially after the developer triggers their ``gd`` command
(e.g., ``git diff``). The hooks can encapsulate database migrations, data
refreshes, or any additional automation needed to keep the environment in sync.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable

# Default relative directory containing hook scripts.
DEFAULT_HOOKS_DIR = Path("scripts/gd_hooks")


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for the post-`gd` runner."""

    parser = argparse.ArgumentParser(
        description=(
            "Run executable hooks after invoking the developer's `gd` command. "
            "By default, hooks are searched inside scripts/gd_hooks."
        )
    )
    parser.add_argument(
        "hooks",
        nargs="?",
        default=str(DEFAULT_HOOKS_DIR),
        help=(
            "Directory that contains executable hook files to run. "
            "Defaults to scripts/gd_hooks."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List hooks without executing them.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help=(
            "Continue running remaining hooks even if a hook exits with a non-zero "
            "status. By default, execution stops on the first failure."
        ),
    )
    return parser.parse_args(argv)


def collect_hooks(hooks_dir: Path) -> list[Path]:
    """Return an ordered list of executable hook files."""

    if not hooks_dir.exists():
        return []

    hooks: list[Path] = []
    for candidate in sorted(hooks_dir.iterdir()):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            hooks.append(candidate)
    return hooks


def run_hook(hook: Path) -> int:
    """Execute a single hook and return its exit code."""

    # For Python hooks without an executable bit, developers can set the bit or
    # add an appropriate shebang. Here we assume executability has already been
    # configured.
    process = subprocess.run([str(hook)], check=False)
    return process.returncode


def main(argv: Iterable[str] | None = None) -> int:
    """Entry-point coordinating hook discovery and execution."""

    args = parse_args(argv)
    hooks_dir = Path(args.hooks).resolve()

    hooks = collect_hooks(hooks_dir)
    if not hooks:
        print(f"[post-gd] No executable hooks found in {hooks_dir}.")
        return 0

    print(f"[post-gd] Running {len(hooks)} hook(s) from {hooks_dir}...")

    for hook in hooks:
        print(f"[post-gd] → Executing {hook.name}")
        if args.dry_run:
            continue

        exit_code = run_hook(hook)
        if exit_code != 0:
            print(f"[post-gd] ✗ Hook {hook.name} failed with exit code {exit_code}.")
            if not args.continue_on_error:
                return exit_code
        else:
            print(f"[post-gd] ✓ Hook {hook.name} completed successfully.")

    if args.dry_run:
        print("[post-gd] Dry run complete. No hooks were executed.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
