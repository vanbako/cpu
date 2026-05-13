#!/usr/bin/env python3
"""Validate and audit the I35-S05 FPGA video scanout gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_gowin_reports, fpga_video_scanout_gate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the video scanout gate")
    parser.add_argument("--json", action="store_true", help="print the gate profile as JSON")
    parser.add_argument("--summary", action="store_true", help="print the executable scanout summary")
    parser.add_argument("--plan", action="store_true", help="print Verilator command inventory")
    parser.add_argument(
        "--audit-reports",
        nargs="?",
        const="build/fpga/tang_mega_138k/first_test",
        metavar="BUILD_ROOT",
        help="parse and audit generated Gowin reports under BUILD_ROOT",
    )
    parser.add_argument(
        "--profile",
        default=fpga_gowin_reports.FPGA_GOWIN_REPORTS_DEFAULT_PROFILE,
        help="clock profile id used for timing-margin policy",
    )
    args = parser.parse_args(argv)

    profile = fpga_video_scanout_gate.fpga_video_scanout_gate_profile()

    if args.plan:
        for command in profile.verilator_commands:
            print(command)
        return 0

    if args.summary:
        print(
            json.dumps(
                fpga_video_scanout_gate.simulate_video_scanout_gate_summary().as_dict(),
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.audit_reports:
        build_root = _repo_path(Path(args.audit_reports))
        if build_root is None:
            print("FPGA video scanout gate:")
            print("- build root must be inside the repository")
            return 1
        try:
            audit = fpga_video_scanout_gate.audit_video_scanout_reports(
                ROOT / build_root,
                profile_id=args.profile,
            )
        except KeyError as exc:
            print(f"unknown FPGA clock profile: {exc}")
            return 1
        print(json.dumps(audit.as_dict(), indent=2, sort_keys=True))
        return 0 if audit.passed else 1

    if args.json:
        print(fpga_video_scanout_gate.fpga_video_scanout_gate_json())
        return 0

    issues = fpga_video_scanout_gate.validate_fpga_video_scanout_gate(ROOT)
    if issues:
        print("FPGA video scanout gate issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA video scanout gate issues: 0")
        return 0

    print(fpga_video_scanout_gate.render_fpga_video_scanout_gate())
    return 0


def _repo_path(path: Path) -> Path | None:
    if not path.is_absolute():
        return path
    try:
        return path.relative_to(ROOT)
    except ValueError:
        return None


if __name__ == "__main__":
    raise SystemExit(main())
