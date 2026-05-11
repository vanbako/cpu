#!/usr/bin/env python3
"""Validate and audit the I33-S05 release-candidate bundle gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import release_candidate_bundle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the release bundle profile")
    parser.add_argument("--json", action="store_true", help="print the release bundle profile as JSON")
    parser.add_argument("--manifest-template", action="store_true", help="print the bundle manifest template")
    parser.add_argument("--template", action="store_true", help="print the bundle evidence template")
    parser.add_argument(
        "--audit-evidence",
        nargs="?",
        const=str(release_candidate_bundle.RELEASE_BUNDLE_EVIDENCE),
        metavar="PATH",
        help="audit captured release-candidate bundle evidence",
    )
    args = parser.parse_args(argv)

    if args.json:
        print(release_candidate_bundle.release_bundle_json())
        return 0

    if args.manifest_template:
        print(release_candidate_bundle.release_bundle_manifest_template(), end="")
        return 0

    if args.template:
        print(release_candidate_bundle.release_bundle_template(), end="")
        return 0

    if args.audit_evidence:
        evidence_path = _repo_relative_path(Path(args.audit_evidence))
        if evidence_path is None:
            print("Release-candidate bundle audit:")
            print("- evidence path must be inside the repository")
            return 1
        audit = release_candidate_bundle.load_release_bundle_audit(
            ROOT,
            evidence_path,
        )
        print(json.dumps(audit.as_dict(), indent=2, sort_keys=True))
        return 0 if audit.accepted else 1

    issues = release_candidate_bundle.validate_release_bundle(ROOT)
    if issues:
        print("Release-candidate bundle issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("Release-candidate bundle issues: 0")
        return 0

    print(release_candidate_bundle.render_release_bundle())
    return 0


def _repo_relative_path(path: Path) -> Path | None:
    if not path.is_absolute():
        return path
    try:
        return path.relative_to(ROOT)
    except ValueError:
        return None


if __name__ == "__main__":
    raise SystemExit(main())
