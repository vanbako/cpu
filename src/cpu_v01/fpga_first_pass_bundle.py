"""First-pass FPGA board build evidence bundle gate.

Owner stories:
- I31-S01: prepare the first-pass board build evidence bundle.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import (
    fpga_board_identity,
    fpga_clock_profiles,
    fpga_constraints,
    fpga_first_test,
    fpga_gowin_build,
    fpga_reproducible_build,
    fpga_smoke_corpus,
    fpga_soc_loader_handoff,
    fpga_soc_top_archive,
)


JsonValue = Any

FPGA_FIRST_PASS_BUNDLE_STORY = "I31-S01"
FPGA_FIRST_PASS_BUNDLE_DOC = Path("docs/implementation/fpga-first-pass-build-bundle.md")
FPGA_FIRST_PASS_BUNDLE_TOOL = "python tools\\fpga_first_pass_bundle.py --check"
FPGA_FIRST_PASS_BUNDLE_EVIDENCE = Path(
    "docs/implementation/evidence/i31_s01_first_pass_build_bundle.txt"
)
FPGA_FIRST_PASS_BUNDLE_RESULT = "frozen_for_gowin"
FPGA_FIRST_PASS_SELECTED_CASE = "reset_pass.first_test_pause_stream"
FPGA_FIRST_PASS_SELECTED_IMAGE = "builtin.first_test_pause_stream"
FPGA_FIRST_PASS_LOADER_STATUS = "idle_disabled_for_first_pass_build"
FIRST_PASS_PROFILE_STATUS = "blocked_pending_physical_evidence"

BUNDLE_FROZEN = "frozen"
BUNDLE_BLOCKED = "blocked"
BUNDLE_INVALID = "invalid"
BUNDLE_NEEDS_FOLLOWUP = "needs_followup"


@dataclass(frozen=True)
class FirstPassBundleItem:
    name: str
    value: str
    source_gate: str
    status: str
    purpose: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "value": self.value,
            "source_gate": self.source_gate,
            "status": self.status,
            "purpose": self.purpose,
        }


@dataclass(frozen=True)
class FirstPassExpectedSignature:
    interface: str
    expected: str
    source: str
    capture_gate: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "interface": self.interface,
            "expected": self.expected,
            "source": self.source,
            "capture_gate": self.capture_gate,
        }


@dataclass(frozen=True)
class FirstPassBundleProfile:
    story: str
    status: str
    evidence_path: Path
    board: str
    device: str
    package: str
    top_module: str
    selected_image: str
    selected_case: str
    build_root: Path
    constraints_cst: Path
    constraints_sdc: Path
    clock_profile: str
    loader_status: str
    gates: tuple[str, ...]
    items: tuple[FirstPassBundleItem, ...]
    expected_signatures: tuple[FirstPassExpectedSignature, ...]
    retest_commands: tuple[str, ...]
    blockers: tuple[str, ...]

    def item_by_name(self, name: str) -> FirstPassBundleItem:
        for item in self.items:
            if item.name == name:
                return item
        raise KeyError(name)

    def signature_by_interface(self, interface: str) -> FirstPassExpectedSignature:
        for signature in self.expected_signatures:
            if signature.interface == interface:
                return signature
        raise KeyError(interface)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "status": self.status,
            "evidence_path": self.evidence_path.as_posix(),
            "board": self.board,
            "device": self.device,
            "package": self.package,
            "top_module": self.top_module,
            "selected_image": self.selected_image,
            "selected_case": self.selected_case,
            "build_root": self.build_root.as_posix(),
            "constraints_cst": self.constraints_cst.as_posix(),
            "constraints_sdc": self.constraints_sdc.as_posix(),
            "clock_profile": self.clock_profile,
            "loader_status": self.loader_status,
            "gates": list(self.gates),
            "items": [item.as_dict() for item in self.items],
            "expected_signatures": [
                signature.as_dict() for signature in self.expected_signatures
            ],
            "retest_commands": list(self.retest_commands),
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class FirstPassBundleRecord:
    fields: dict[str, str]

    def value(self, key: str) -> str:
        return self.fields.get(key, "")

    def as_dict(self) -> dict[str, JsonValue]:
        return dict(self.fields)


@dataclass(frozen=True)
class FirstPassBundleAudit:
    status: str
    message: str
    evidence_path: str
    missing_fields: tuple[str, ...]
    link_issues: tuple[str, ...]
    selection_issues: tuple[str, ...]
    blocker_issues: tuple[str, ...]
    actions: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.status == BUNDLE_FROZEN

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "status": self.status,
            "message": self.message,
            "evidence_path": self.evidence_path,
            "missing_fields": list(self.missing_fields),
            "link_issues": list(self.link_issues),
            "selection_issues": list(self.selection_issues),
            "blocker_issues": list(self.blocker_issues),
            "actions": list(self.actions),
        }


def fpga_first_pass_bundle_profile() -> FirstPassBundleProfile:
    constraints = fpga_constraints.fpga_constraints_overlay()
    repro = fpga_reproducible_build.fpga_reproducible_build_profile()
    corpus_case = fpga_smoke_corpus.fpga_smoke_corpus_profile().case_by_id(
        FPGA_FIRST_PASS_SELECTED_CASE
    )
    return FirstPassBundleProfile(
        story=FPGA_FIRST_PASS_BUNDLE_STORY,
        status=FIRST_PASS_PROFILE_STATUS,
        evidence_path=FPGA_FIRST_PASS_BUNDLE_EVIDENCE,
        board=fpga_first_test.TARGET_BOARD_NAME,
        device=fpga_first_test.TARGET_FPGA_DEVICE,
        package=fpga_first_test.TARGET_IDE_PACKAGE,
        top_module=fpga_first_test.FPGA_TOP_MODULE,
        selected_image=corpus_case.program_id,
        selected_case=corpus_case.case_id,
        build_root=repro.build_root,
        constraints_cst=constraints.cst_path,
        constraints_sdc=constraints.sdc_path,
        clock_profile=fpga_clock_profiles.DEBUG_PROFILE_ID,
        loader_status=FPGA_FIRST_PASS_LOADER_STATUS,
        gates=(
            fpga_soc_top_archive.FPGA_SOC_TOP_ARCHIVE_TOOL,
            fpga_reproducible_build.FPGA_REPRO_BUILD_TOOL,
            fpga_board_identity.FPGA_BOARD_IDENTITY_TOOL,
            fpga_constraints.FPGA_CONSTRAINTS_TOOL,
            fpga_clock_profiles.FPGA_CLOCK_PROFILES_TOOL,
            fpga_smoke_corpus.FPGA_SMOKE_CORPUS_TOOL,
            fpga_soc_loader_handoff.FPGA_SOC_LOADER_HANDOFF_TOOL,
        ),
        items=_bundle_items(repro, constraints, corpus_case),
        expected_signatures=(
            FirstPassExpectedSignature(
                interface="led",
                expected=corpus_case.expected_led_signature,
                source=corpus_case.case_id,
                capture_gate=fpga_smoke_corpus.FPGA_SMOKE_CORPUS_TOOL,
            ),
            FirstPassExpectedSignature(
                interface="uart",
                expected=corpus_case.expected_uart_signature,
                source=corpus_case.case_id,
                capture_gate=fpga_smoke_corpus.FPGA_SMOKE_CORPUS_TOOL,
            ),
            FirstPassExpectedSignature(
                interface="probe",
                expected=corpus_case.expected_probe_signature,
                source=corpus_case.case_id,
                capture_gate=fpga_smoke_corpus.FPGA_SMOKE_CORPUS_TOOL,
            ),
        ),
        retest_commands=(
            fpga_soc_top_archive.FPGA_SOC_TOP_ARCHIVE_TOOL,
            fpga_reproducible_build.FPGA_REPRO_BUILD_TOOL,
            fpga_board_identity.FPGA_BOARD_IDENTITY_TOOL,
            fpga_constraints.FPGA_CONSTRAINTS_TOOL,
            fpga_clock_profiles.FPGA_CLOCK_PROFILES_TOOL,
            fpga_smoke_corpus.FPGA_SMOKE_CORPUS_TOOL,
            fpga_gowin_build.FPGA_GOWIN_BUILD_TOOL,
        ),
        blockers=(
            "I30-S06 closure archive must be captured before the bundle can be consumed by I31-S02",
            "I24-S01 identity evidence must confirm the exact device/package before final CST use",
            "I24-S02 pin evidence must replace CST placeholders before Gowin build",
            "I28-S05 reproducible build manifest remains documented_blocker until reports and bitstream exist",
            "loader is held idle for the first-pass build; live loading remains outside this bundle",
        ),
    )


def first_pass_bundle_template(profile: FirstPassBundleProfile | None = None) -> str:
    if profile is None:
        profile = fpga_first_pass_bundle_profile()
    retest_commands = " ; ".join(profile.retest_commands)
    return "\n".join(
        (
            f"story={profile.story}",
            "prepared_at=",
            "repository_commit=",
            f"board={profile.board}",
            f"device={profile.device}",
            f"package={profile.package}",
            f"soc_top_archive={fpga_soc_top_archive.FPGA_SOC_TOP_ARCHIVE_EVIDENCE.as_posix()}",
            f"reproducible_build_manifest={fpga_reproducible_build.FPGA_REPRO_BUILD_MANIFEST.as_posix()}",
            f"board_identity={fpga_board_identity.FPGA_BOARD_IDENTITY_EVIDENCE.as_posix()}",
            f"top_module={profile.top_module}",
            f"selected_image={profile.selected_image}",
            "image_source=I23-S04 built-in PAUSE stream",
            f"constraints_cst={profile.constraints_cst.as_posix()}",
            f"constraints_sdc={profile.constraints_sdc.as_posix()}",
            f"clock_profile={profile.clock_profile}",
            f"loader_status={profile.loader_status}",
            f"expected_led_signature={profile.signature_by_interface('led').expected}",
            f"expected_uart_signature={profile.signature_by_interface('uart').expected}",
            f"expected_probe_signature={profile.signature_by_interface('probe').expected}",
            f"gowin_build_root={profile.build_root.as_posix()}",
            f"bundle_result={FPGA_FIRST_PASS_BUNDLE_RESULT}",
            "remaining_blockers=none",
            f"retest_commands={retest_commands}",
            "",
        )
    )


def parse_first_pass_bundle(text: str) -> FirstPassBundleRecord:
    fields: dict[str, str] = {}
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"line {line_number} is not key=value")
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"line {line_number} has an empty key")
        fields[key] = value.strip()
    return FirstPassBundleRecord(fields)


def audit_first_pass_bundle(
    record: FirstPassBundleRecord,
    *,
    evidence_path: str = "<inline>",
    profile: FirstPassBundleProfile | None = None,
) -> FirstPassBundleAudit:
    if profile is None:
        profile = fpga_first_pass_bundle_profile()

    required_fields = (
        "story",
        "prepared_at",
        "repository_commit",
        "board",
        "device",
        "package",
        "soc_top_archive",
        "reproducible_build_manifest",
        "board_identity",
        "top_module",
        "selected_image",
        "image_source",
        "constraints_cst",
        "constraints_sdc",
        "clock_profile",
        "loader_status",
        "expected_led_signature",
        "expected_uart_signature",
        "expected_probe_signature",
        "gowin_build_root",
        "bundle_result",
        "remaining_blockers",
        "retest_commands",
    )
    missing_fields = [field for field in required_fields if not record.value(field)]
    if record.value("story") and record.value("story") != profile.story:
        missing_fields.append("story_must_be_I31-S01")

    selection_issues: list[str] = []
    expected_values = {
        "board": profile.board,
        "device": profile.device,
        "package": profile.package,
        "top_module": profile.top_module,
        "selected_image": profile.selected_image,
        "constraints_cst": profile.constraints_cst.as_posix(),
        "constraints_sdc": profile.constraints_sdc.as_posix(),
        "clock_profile": profile.clock_profile,
        "loader_status": profile.loader_status,
        "gowin_build_root": profile.build_root.as_posix(),
    }
    for field, expected in expected_values.items():
        value = record.value(field)
        if value and value != expected:
            selection_issues.append(f"{field} must be {expected}")

    link_issues: list[str] = []
    for field in (
        "soc_top_archive",
        "reproducible_build_manifest",
        "board_identity",
        "constraints_cst",
        "constraints_sdc",
    ):
        value = record.value(field)
        if value and _is_empty_disposition(value):
            link_issues.append(f"{field} must link concrete evidence or artifact path")

    if record.value("soc_top_archive") and "i30_s06" not in record.value("soc_top_archive").lower():
        link_issues.append("soc_top_archive must reference the I30-S06 archive")
    if (
        record.value("reproducible_build_manifest")
        and "i28_s05" not in record.value("reproducible_build_manifest").lower()
    ):
        link_issues.append("reproducible_build_manifest must reference the I28-S05 manifest")
    if record.value("board_identity") and "i24_s01" not in record.value("board_identity").lower():
        link_issues.append("board_identity must reference the I24-S01 identity evidence")

    led = record.value("expected_led_signature").lower()
    uart = record.value("expected_uart_signature").lower()
    probe = record.value("expected_probe_signature").lower()
    if led and "led" not in led:
        selection_issues.append("expected_led_signature must name LED observation")
    if uart and not _mentions_any(uart, "uart", "status", "pass", "retire", "fault"):
        selection_issues.append("expected_uart_signature must name UART/status observation")
    if probe and not _mentions_any(probe, "probe", "retire", "debug", "pc"):
        selection_issues.append("expected_probe_signature must name probe/debug observation")

    blocker_issues: list[str] = []
    if record.value("bundle_result") != FPGA_FIRST_PASS_BUNDLE_RESULT:
        blocker_issues.append("bundle_result must be frozen_for_gowin")
    if not _is_empty_disposition(record.value("remaining_blockers")):
        blocker_issues.append("remaining_blockers must be none before I31-S02 handoff")
    retest_commands = record.value("retest_commands")
    for command in (
        fpga_soc_top_archive.FPGA_SOC_TOP_ARCHIVE_TOOL,
        fpga_reproducible_build.FPGA_REPRO_BUILD_TOOL,
        fpga_board_identity.FPGA_BOARD_IDENTITY_TOOL,
        fpga_constraints.FPGA_CONSTRAINTS_TOOL,
        fpga_gowin_build.FPGA_GOWIN_BUILD_TOOL,
    ):
        if retest_commands and command not in retest_commands:
            blocker_issues.append(f"retest_commands must include {command}")

    if missing_fields:
        return FirstPassBundleAudit(
            status=BUNDLE_INVALID,
            message="First-pass board build bundle is incomplete or malformed.",
            evidence_path=evidence_path,
            missing_fields=tuple(missing_fields),
            link_issues=tuple(link_issues),
            selection_issues=tuple(selection_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("complete all required bundle fields", "rerun the I31-S01 audit"),
        )
    if link_issues or selection_issues:
        return FirstPassBundleAudit(
            status=BUNDLE_INVALID,
            message="First-pass board build bundle selections or evidence links are invalid.",
            evidence_path=evidence_path,
            missing_fields=(),
            link_issues=tuple(link_issues),
            selection_issues=tuple(selection_issues),
            blocker_issues=tuple(blocker_issues),
            actions=("freeze the selected top, image, constraints, clock, and signatures again",),
        )
    if blocker_issues:
        return FirstPassBundleAudit(
            status=BUNDLE_NEEDS_FOLLOWUP,
            message="First-pass board build bundle exists but cannot be handed to Gowin yet.",
            evidence_path=evidence_path,
            missing_fields=(),
            link_issues=(),
            selection_issues=(),
            blocker_issues=tuple(blocker_issues),
            actions=("close blockers or keep the bundle out of I31-S02",),
        )
    return FirstPassBundleAudit(
        status=BUNDLE_FROZEN,
        message="First-pass board build bundle is frozen for the Gowin build handoff.",
        evidence_path=evidence_path,
        missing_fields=(),
        link_issues=(),
        selection_issues=(),
        blocker_issues=(),
        actions=("I31-S02 may consume this bundle for the Gowin build and timing audit",),
    )


def load_first_pass_bundle_audit(
    root: Path | None = None,
    evidence_path: Path | None = None,
) -> FirstPassBundleAudit:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_first_pass_bundle_profile()
    relative_path = evidence_path or profile.evidence_path
    path = root / relative_path
    if not path.exists():
        return FirstPassBundleAudit(
            status=BUNDLE_BLOCKED,
            message="No first-pass board build bundle has been captured yet.",
            evidence_path=relative_path.as_posix(),
            missing_fields=tuple(
                field
                for field in (
                    "story",
                    "prepared_at",
                    "repository_commit",
                    "board",
                    "device",
                    "package",
                    "soc_top_archive",
                    "reproducible_build_manifest",
                    "board_identity",
                    "top_module",
                    "selected_image",
                    "constraints_cst",
                    "constraints_sdc",
                    "clock_profile",
                    "loader_status",
                    "expected_led_signature",
                    "expected_uart_signature",
                    "expected_probe_signature",
                    "gowin_build_root",
                    "bundle_result",
                    "remaining_blockers",
                    "retest_commands",
                )
            ),
            link_issues=(),
            selection_issues=(),
            blocker_issues=(),
            actions=(
                f"create {relative_path.as_posix()} from the bundle template",
                "link I30-S06, I28-S05, I24-S01, constraints, clock, and expected signature evidence",
                "do not run I31-S02 until the bundle is frozen",
            ),
        )
    try:
        record = parse_first_pass_bundle(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return FirstPassBundleAudit(
            status=BUNDLE_INVALID,
            message="First-pass board build bundle could not be parsed.",
            evidence_path=relative_path.as_posix(),
            missing_fields=(str(exc),),
            link_issues=(),
            selection_issues=(),
            blocker_issues=(),
            actions=("fix the key=value bundle record", "rerun the I31-S01 audit"),
        )
    return audit_first_pass_bundle(
        record,
        evidence_path=relative_path.as_posix(),
        profile=profile,
    )


def fpga_first_pass_bundle_json(*, indent: int = 2) -> str:
    return json.dumps(
        fpga_first_pass_bundle_profile().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def render_fpga_first_pass_bundle(
    profile: FirstPassBundleProfile | None = None,
) -> str:
    if profile is None:
        profile = fpga_first_pass_bundle_profile()
    lines = [
        "# FPGA First-Pass Build Bundle",
        "",
        f"Story: {profile.story}",
        f"Status: `{profile.status}`",
        f"Evidence path: `{profile.evidence_path.as_posix()}`",
        f"Top module: `{profile.top_module}`",
        f"Selected image: `{profile.selected_image}`",
        f"Clock profile: `{profile.clock_profile}`",
        "",
        "## Bundle Items",
        "",
        "| Item | Value | Gate | Status |",
        "| --- | --- | --- | --- |",
    ]
    for item in profile.items:
        lines.append(
            f"| `{item.name}` | `{item.value}` | `{item.source_gate}` | {item.status} |"
        )
    lines.extend(["", "## Expected Signatures", ""])
    for signature in profile.expected_signatures:
        lines.append(f"- `{signature.interface}`: {signature.expected}.")
    lines.extend(["", "## Retest Commands", ""])
    lines.extend(f"- `{command}`" for command in profile.retest_commands)
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {blocker}." for blocker in profile.blockers)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_first_pass_bundle(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_first_pass_bundle_profile()
    issues: list[str] = []

    if profile.story != FPGA_FIRST_PASS_BUNDLE_STORY:
        issues.append(f"first-pass bundle story must be {FPGA_FIRST_PASS_BUNDLE_STORY}")
    if profile.status != FIRST_PASS_PROFILE_STATUS:
        issues.append("first-pass bundle must remain blocked until physical evidence is captured")
    if profile.board != fpga_first_test.TARGET_BOARD_NAME:
        issues.append("first-pass bundle board must match the first-test target")
    if profile.device != fpga_first_test.TARGET_FPGA_DEVICE:
        issues.append("first-pass bundle device must match the first-test target")
    if profile.package != fpga_first_test.TARGET_IDE_PACKAGE:
        issues.append("first-pass bundle package must match the first-test target")
    if profile.top_module != fpga_first_test.FPGA_TOP_MODULE:
        issues.append("first-pass bundle top must be cpu_v01_fpga_top")
    if profile.selected_case != FPGA_FIRST_PASS_SELECTED_CASE:
        issues.append("first-pass bundle must freeze the reset-pass smoke corpus case")
    if profile.selected_image != FPGA_FIRST_PASS_SELECTED_IMAGE:
        issues.append("first-pass bundle must freeze the built-in first-test image")
    if profile.clock_profile != fpga_clock_profiles.DEBUG_PROFILE_ID:
        issues.append("first-pass bundle must select debug_direct_25mhz")
    if profile.loader_status != FPGA_FIRST_PASS_LOADER_STATUS:
        issues.append("first-pass bundle loader status must be held idle")

    for check_issues in (
        fpga_soc_top_archive.validate_fpga_soc_top_archive(root),
        fpga_reproducible_build.validate_fpga_reproducible_build(root),
        fpga_board_identity.validate_fpga_board_identity(root),
        fpga_constraints.validate_fpga_constraints_overlay(root),
        fpga_clock_profiles.validate_fpga_clock_profiles(root),
        fpga_smoke_corpus.validate_fpga_smoke_corpus(root),
        fpga_soc_loader_handoff.validate_fpga_soc_loader_handoff(root),
    ):
        issues.extend(check_issues)

    for gate in (
        fpga_soc_top_archive.FPGA_SOC_TOP_ARCHIVE_TOOL,
        fpga_reproducible_build.FPGA_REPRO_BUILD_TOOL,
        fpga_board_identity.FPGA_BOARD_IDENTITY_TOOL,
        fpga_constraints.FPGA_CONSTRAINTS_TOOL,
        fpga_clock_profiles.FPGA_CLOCK_PROFILES_TOOL,
        fpga_smoke_corpus.FPGA_SMOKE_CORPUS_TOOL,
        fpga_soc_loader_handoff.FPGA_SOC_LOADER_HANDOFF_TOOL,
    ):
        if gate not in profile.gates:
            issues.append(f"missing first-pass bundle gate {gate}")

    items = {item.name: item for item in profile.items}
    for required in (
        "selected_top",
        "selected_image",
        "constraints_cst",
        "constraints_sdc",
        "clock_profile",
        "loader_status",
        "expected_led_signature",
        "expected_uart_signature",
        "expected_probe_signature",
    ):
        if required not in items:
            issues.append(f"missing first-pass bundle item {required}")

    signatures = {signature.interface: signature for signature in profile.expected_signatures}
    for interface in ("led", "uart", "probe"):
        if interface not in signatures:
            issues.append(f"missing first-pass expected {interface} signature")
    if signatures.get("led") and "led" not in signatures["led"].expected.lower():
        issues.append("first-pass LED signature must name LED observation")
    if signatures.get("uart") and not _mentions_any(
        signatures["uart"].expected.lower(), "uart", "status", "retire", "pass", "fault"
    ):
        issues.append("first-pass UART signature must name status observation")
    if signatures.get("probe") and not _mentions_any(
        signatures["probe"].expected.lower(), "probe", "retire", "debug", "pc"
    ):
        issues.append("first-pass probe signature must name probe observation")

    good_record = parse_first_pass_bundle(
        first_pass_bundle_template()
        .replace("prepared_at=", "prepared_at=2026-05-10T00:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
    )
    if not audit_first_pass_bundle(good_record).passed:
        issues.append("complete first-pass build bundle must audit as frozen")

    followup_record = parse_first_pass_bundle(
        first_pass_bundle_template()
        .replace("prepared_at=", "prepared_at=2026-05-10T00:00:00")
        .replace("repository_commit=", "repository_commit=0123456789abcdef")
        .replace("bundle_result=frozen_for_gowin", "bundle_result=blocked")
    )
    if audit_first_pass_bundle(followup_record).status != BUNDLE_NEEDS_FOLLOWUP:
        issues.append("non-frozen first-pass build bundle must require follow-up")

    default_audit = load_first_pass_bundle_audit(root)
    if default_audit.status != BUNDLE_BLOCKED:
        issues.append("default first-pass build bundle audit must be blocked without evidence")

    doc = _read_if_exists(root / FPGA_FIRST_PASS_BUNDLE_DOC)
    for token in (
        "Story: I31-S01",
        FPGA_FIRST_PASS_BUNDLE_TOOL,
        FPGA_FIRST_PASS_BUNDLE_EVIDENCE.as_posix(),
        fpga_soc_top_archive.FPGA_SOC_TOP_ARCHIVE_TOOL,
        fpga_reproducible_build.FPGA_REPRO_BUILD_TOOL,
        fpga_board_identity.FPGA_BOARD_IDENTITY_TOOL,
        fpga_constraints.FPGA_CONSTRAINTS_TOOL,
        "cpu_v01_fpga_top",
        FPGA_FIRST_PASS_SELECTED_IMAGE,
        "debug_direct_25mhz",
        "loader_status",
        "expected_led_signature",
        "expected_uart_signature",
        "expected_probe_signature",
        "frozen_for_gowin",
        "I31-S02",
        "Acceptance Review",
    ):
        if token not in doc:
            issues.append(f"{FPGA_FIRST_PASS_BUNDLE_DOC.as_posix()} missing {token}")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(load_first_pass_bundle_audit(root).as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"first-pass bundle objects are not JSON serializable: {exc}")

    return tuple(issues)


def _bundle_items(
    repro: fpga_reproducible_build.ReproducibleBuildProfile,
    constraints: fpga_constraints.FpgaConstraintsOverlay,
    corpus_case: fpga_smoke_corpus.FpgaSmokeCorpusCase,
) -> tuple[FirstPassBundleItem, ...]:
    return (
        FirstPassBundleItem(
            name="selected_top",
            value=fpga_first_test.FPGA_TOP_MODULE,
            source_gate=fpga_soc_top_archive.FPGA_SOC_TOP_ARCHIVE_TOOL,
            status="documented",
            purpose="freeze the RTL top consumed by the first Gowin build",
        ),
        FirstPassBundleItem(
            name="selected_image",
            value=corpus_case.program_id,
            source_gate=fpga_smoke_corpus.FPGA_SMOKE_CORPUS_TOOL,
            status="ready_for_first_test",
            purpose="select the built-in PAUSE stream expected by first-pass board observation",
        ),
        FirstPassBundleItem(
            name="constraints_cst",
            value=constraints.cst_path.as_posix(),
            source_gate=fpga_constraints.FPGA_CONSTRAINTS_TOOL,
            status="blocked_until_pin_evidence",
            purpose="name the final CST path that must be generated from verified pins",
        ),
        FirstPassBundleItem(
            name="constraints_sdc",
            value=constraints.sdc_path.as_posix(),
            source_gate=fpga_constraints.FPGA_CONSTRAINTS_TOOL,
            status="documented",
            purpose="freeze the 25 MHz board clock timing constraint",
        ),
        FirstPassBundleItem(
            name="clock_profile",
            value=fpga_clock_profiles.DEBUG_PROFILE_ID,
            source_gate=fpga_clock_profiles.FPGA_CLOCK_PROFILES_TOOL,
            status="documented",
            purpose="select the conservative debug clock profile for first-pass bring-up",
        ),
        FirstPassBundleItem(
            name="loader_status",
            value=FPGA_FIRST_PASS_LOADER_STATUS,
            source_gate=fpga_soc_loader_handoff.FPGA_SOC_LOADER_HANDOFF_TOOL,
            status="documented",
            purpose="keep the loader path idle so the first build validates the fixed image",
        ),
        FirstPassBundleItem(
            name="expected_led_signature",
            value=corpus_case.expected_led_signature,
            source_gate=fpga_smoke_corpus.FPGA_SMOKE_CORPUS_TOOL,
            status="documented",
            purpose="freeze the pass/fail/heartbeat LED expectation before Gowin",
        ),
        FirstPassBundleItem(
            name="expected_uart_signature",
            value=corpus_case.expected_uart_signature,
            source_gate=fpga_smoke_corpus.FPGA_SMOKE_CORPUS_TOOL,
            status="documented",
            purpose="freeze the UART/status expectation before board programming",
        ),
        FirstPassBundleItem(
            name="expected_probe_signature",
            value=corpus_case.expected_probe_signature,
            source_gate=fpga_smoke_corpus.FPGA_SMOKE_CORPUS_TOOL,
            status="documented",
            purpose="freeze the optional GAO/ILA probe expectation before board programming",
        ),
        FirstPassBundleItem(
            name="reproducible_build_root",
            value=repro.build_root.as_posix(),
            source_gate=fpga_reproducible_build.FPGA_REPRO_BUILD_TOOL,
            status=repro.status,
            purpose="carry the build root into I31-S02 report capture",
        ),
    )


def _is_empty_disposition(value: str) -> bool:
    return value.strip().lower() in {"", "none", "n/a", "na", "-", "blocked", "missing"}


def _mentions_any(value: str, *tokens: str) -> bool:
    return any(token in value for token in tokens)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")
