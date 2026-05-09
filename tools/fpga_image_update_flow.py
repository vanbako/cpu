#!/usr/bin/env python3
"""Validate and audit the I26-S03 FPGA image update flow."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_image_update_flow


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the image update flow")
    parser.add_argument("--json", action="store_true", help="print image update profile JSON")
    parser.add_argument("--plan", action="store_true", help="print command plan rows")
    parser.add_argument(
        "--template",
        nargs="?",
        const="",
        metavar="PROGRAM_ID",
        help="print an I26-S03 evidence template",
    )
    parser.add_argument(
        "--audit-evidence",
        nargs="?",
        const=str(fpga_image_update_flow.FPGA_IMAGE_UPDATE_EVIDENCE),
        metavar="PATH",
        help="audit captured image update evidence",
    )
    parser.add_argument(
        "--gowin-build-root",
        metavar="PATH",
        help="optional I24-S03 build root for evidence audit",
    )
    args = parser.parse_args(argv)

    if args.json:
        print(fpga_image_update_flow.fpga_image_update_json())
        return 0

    if args.plan:
        for plan in fpga_image_update_flow.fpga_image_update_profile().plans:
            print(f"{plan.program_id}\t{plan.default_mode}\t{plan.image_sha256}")
            for command in plan.rebuild_commands:
                print(f"  {command}")
        return 0

    if args.template is not None:
        program_id = args.template or None
        try:
            print(fpga_image_update_flow.image_update_evidence_template(program_id), end="")
        except KeyError as exc:
            print(f"unknown FPGA program manifest entry: {exc}")
            return 1
        return 0

    if args.audit_evidence:
        evidence_path = _repo_path(Path(args.audit_evidence))
        build_root = _optional_repo_path(args.gowin_build_root)
        if evidence_path is None or build_root is False:
            print("FPGA image update audit:")
            print("- paths must be inside the repository")
            return 1
        audit = fpga_image_update_flow.load_image_update_audit(ROOT, evidence_path, build_root)
        print(json.dumps(audit.as_dict(), indent=2, sort_keys=True))
        return 0 if audit.passed else 1

    issues = fpga_image_update_flow.validate_fpga_image_update_flow(ROOT)
    if issues:
        print("FPGA image update issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA image update issues: 0")
        return 0

    print(fpga_image_update_flow.render_fpga_image_update_flow())
    return 0


def _repo_path(path: Path) -> Path | None:
    if not path.is_absolute():
        return path
    try:
        return path.relative_to(ROOT)
    except ValueError:
        return None


def _optional_repo_path(raw: str | None) -> Path | None | bool:
    if raw is None:
        return None
    return _repo_path(Path(raw)) or False


if __name__ == "__main__":
    raise SystemExit(main())
