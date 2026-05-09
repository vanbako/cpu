#!/usr/bin/env python3
"""Generate and validate I26-S02 FPGA BRAM initialization images."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_bram_images


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the BRAM image generator")
    parser.add_argument("--json", action="store_true", help="print generated image metadata as JSON")
    parser.add_argument("--list", action="store_true", help="list generated BRAM image bundles")
    parser.add_argument("--program", metavar="PROGRAM_ID", help="restrict output to one program ID")
    parser.add_argument(
        "--print-image",
        nargs=2,
        metavar=("PROGRAM_ID", "MEMORY"),
        help="print one rendered .mem image to stdout",
    )
    parser.add_argument("--write", action="store_true", help="write .mem files under --out-dir")
    parser.add_argument("--out-dir", metavar="PATH", help="output root for --write")
    parser.add_argument("--verify", metavar="PATH", help="verify generated .mem files under PATH")
    args = parser.parse_args(argv)

    if args.print_image:
        program_id, memory_name = args.print_image
        try:
            print(fpga_bram_images.render_bram_image(program_id, memory_name), end="")
        except KeyError as exc:
            print(f"unknown FPGA BRAM image selector: {exc}")
            return 1
        return 0

    if args.list:
        try:
            bundles = fpga_bram_images.fpga_bram_image_bundles(args.program)
        except KeyError as exc:
            print(f"unknown FPGA program manifest entry: {exc}")
            return 1
        for bundle in bundles:
            artifacts = ",".join(artifact.memory_name for artifact in bundle.artifacts)
            print(f"{bundle.program_id}\t{bundle.source_case_id}\t{artifacts}")
        return 0

    if args.json:
        try:
            print(fpga_bram_images.fpga_bram_images_json(args.program))
        except KeyError as exc:
            print(f"unknown FPGA program manifest entry: {exc}")
            return 1
        return 0

    if args.write:
        if not args.out_dir:
            print("--write requires --out-dir")
            return 1
        out_dir = _repo_path(Path(args.out_dir))
        if out_dir is None:
            print("--out-dir must be inside the repository")
            return 1
        try:
            report = fpga_bram_images.write_bram_images(ROOT / out_dir, args.program)
        except KeyError as exc:
            print(f"unknown FPGA program manifest entry: {exc}")
            return 1
        print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
        return 0 if report.passed else 1

    if args.verify:
        verify_root = _repo_path(Path(args.verify))
        if verify_root is None:
            print("--verify path must be inside the repository")
            return 1
        try:
            issues = fpga_bram_images.verify_written_bram_images(ROOT / verify_root, args.program)
        except KeyError as exc:
            print(f"unknown FPGA program manifest entry: {exc}")
            return 1
        if issues:
            print("FPGA BRAM image verification issues:")
            for issue in issues:
                print(f"- {issue}")
            return 1
        print("FPGA BRAM image verification issues: 0")
        return 0

    issues = fpga_bram_images.validate_fpga_bram_images(ROOT)
    if issues:
        print("FPGA BRAM image issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA BRAM image issues: 0")
        return 0

    print(fpga_bram_images.render_fpga_bram_images())
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
