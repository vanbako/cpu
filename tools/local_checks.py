#!/usr/bin/env python3
"""Run the CPU v0.1 local implementation checks.

Owner stories:
- I01-S02: local test commands and baseline CI-style checks.
- I12-S01: one-command full local check runner.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class LocalCheck:
    label: str
    command: tuple[str, ...]

    @property
    def display(self) -> str:
        return " ".join(self.command)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def local_checks(python: str | None = None) -> tuple[LocalCheck, ...]:
    if python is None:
        python = sys.executable
    return (
        LocalCheck("spec references", (python, "tools/spec_reference_check.py")),
        LocalCheck("constants model", (python, "tools/spec_constants_model.py")),
        LocalCheck("story coverage drift", (python, "tools/story_coverage.py", "--check-drift")),
        LocalCheck("toolchain corpus", (python, "tools/toolchain_corpus.py", "--check")),
        LocalCheck(
            "verilator regression gate",
            (python, "tools/verilator_diff_harness.py", "--suite", "fast"),
        ),
        LocalCheck(
            "conformance tests",
            (
                python,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests/conformance",
                "-p",
                "test_*.py",
            ),
        ),
        LocalCheck(
            "litmus tests",
            (
                python,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests/litmus",
                "-p",
                "test_*.py",
            ),
        ),
        LocalCheck("whitespace", ("git", "diff", "--check")),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--list",
        action="store_true",
        help="print the planned checks without running them",
    )
    args = parser.parse_args(argv)

    checks = local_checks()
    if args.list:
        for check in checks:
            print(f"{check.label}: {check.display}")
        return 0

    root = repo_root()
    for check in checks:
        print(f"==> {check.label}", flush=True)
        result = subprocess.run(check.command, cwd=root, check=False)
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
