#!/usr/bin/env python3
"""Validate and print the I36-S01 FPGA compositor framebuffer policy."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_compositor_framebuffer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the framebuffer policy")
    parser.add_argument("--json", action="store_true", help="print the policy as JSON")
    parser.add_argument("--formats", action="store_true", help="list pixel formats")
    parser.add_argument("--windows", action="store_true", help="list framebuffer windows")
    args = parser.parse_args(argv)

    profile = fpga_compositor_framebuffer.fpga_compositor_framebuffer_profile()

    if args.formats:
        for pixel_format in profile.pixel_formats:
            print(
                f"{pixel_format.name}\t{pixel_format.bytes_per_pixel}"
                f"\t{pixel_format.alpha_policy}"
            )
        return 0

    if args.windows:
        window = profile.framebuffer_window
        print(f"{window.name}\t0x{window.base_cell:08X}\t0x{window.end_cell:08X}")
        return 0

    if args.json:
        print(fpga_compositor_framebuffer.fpga_compositor_framebuffer_json())
        return 0

    issues = fpga_compositor_framebuffer.validate_fpga_compositor_framebuffer(ROOT)
    if issues:
        print("FPGA compositor framebuffer policy issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA compositor framebuffer policy issues: 0")
        return 0

    print(fpga_compositor_framebuffer.render_fpga_compositor_framebuffer_profile())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
