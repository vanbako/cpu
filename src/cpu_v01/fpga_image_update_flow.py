"""FPGA program-image rebuild and memory-update flow.

Owner stories:
- I26-S03: document and automate bitstream rebuild or memory-update path.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_bram_images, fpga_gowin_build, fpga_program_manifest


JsonValue = Any

FPGA_IMAGE_UPDATE_STORY = "I26-S03"
FPGA_IMAGE_UPDATE_DOC = Path("docs/implementation/fpga-image-update-flow.md")
FPGA_IMAGE_UPDATE_TOOL = "python tools\\fpga_image_update_flow.py --check"
FPGA_IMAGE_UPDATE_EVIDENCE = Path("docs/implementation/evidence/i26_s03_image_update.txt")
UPDATE_MODE_GOWIN_REBUILD = "gowin_rebuild"
UPDATE_MODE_MEMORY_UPDATE = "memory_update"
UPDATE_PASSED = "passed"
UPDATE_BLOCKED = "blocked"
UPDATE_FAILED = "failed"


@dataclass(frozen=True)
class ImageUpdatePlan:
    program_id: str
    image_sha256: str
    default_mode: str
    memory_update_status: str
    required_artifacts: tuple[str, ...]
    rebuild_commands: tuple[str, ...]
    evidence_fields: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "program_id": self.program_id,
            "image_sha256": self.image_sha256,
            "default_mode": self.default_mode,
            "memory_update_status": self.memory_update_status,
            "required_artifacts": list(self.required_artifacts),
            "rebuild_commands": list(self.rebuild_commands),
            "evidence_fields": list(self.evidence_fields),
        }


@dataclass(frozen=True)
class ImageUpdateProfile:
    story: str
    bram_image_gate: str
    gowin_build_gate: str
    evidence_path: Path
    supported_modes: tuple[str, ...]
    plans: tuple[ImageUpdatePlan, ...]
    blockers: tuple[str, ...]

    def plan_by_program_id(self, program_id: str) -> ImageUpdatePlan:
        for plan in self.plans:
            if plan.program_id == program_id:
                return plan
        raise KeyError(program_id)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "bram_image_gate": self.bram_image_gate,
            "gowin_build_gate": self.gowin_build_gate,
            "evidence_path": self.evidence_path.as_posix(),
            "supported_modes": list(self.supported_modes),
            "plans": [plan.as_dict() for plan in self.plans],
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class ImageUpdateEvidenceRecord:
    fields: dict[str, str]

    def value(self, key: str) -> str:
        return self.fields.get(key, "")

    def as_dict(self) -> dict[str, JsonValue]:
        return dict(self.fields)


@dataclass(frozen=True)
class ImageUpdateAudit:
    status: str
    message: str
    program_id: str
    update_mode: str
    gowin_status: str
    missing_fields: tuple[str, ...]
    artifact_issues: tuple[str, ...]
    identity_issues: tuple[str, ...]
    actions: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.status == UPDATE_PASSED

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "status": self.status,
            "message": self.message,
            "program_id": self.program_id,
            "update_mode": self.update_mode,
            "gowin_status": self.gowin_status,
            "missing_fields": list(self.missing_fields),
            "artifact_issues": list(self.artifact_issues),
            "identity_issues": list(self.identity_issues),
            "actions": list(self.actions),
        }


def fpga_image_update_profile() -> ImageUpdateProfile:
    bundles = fpga_bram_images.fpga_bram_image_bundles()
    return ImageUpdateProfile(
        story=FPGA_IMAGE_UPDATE_STORY,
        bram_image_gate=fpga_bram_images.FPGA_BRAM_IMAGES_TOOL,
        gowin_build_gate=fpga_gowin_build.FPGA_GOWIN_BUILD_TOOL,
        evidence_path=FPGA_IMAGE_UPDATE_EVIDENCE,
        supported_modes=(UPDATE_MODE_GOWIN_REBUILD, UPDATE_MODE_MEMORY_UPDATE),
        plans=tuple(_plan_for_bundle(bundle) for bundle in bundles),
        blockers=(
            "Gowin report audit must pass before a rebuilt bitstream can be handed to programming",
            "memory-update mode is blocked until the Gowin or programmer flow is verified for GW5AST BRAM init replacement",
            "every board evidence record must include the manifest image_sha256 and bitstream_sha256",
        ),
    )


def fpga_image_update_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_image_update_profile().as_dict(), indent=indent, sort_keys=True)


def image_update_evidence_template(program_id: str | None = None) -> str:
    profile = fpga_image_update_profile()
    plan = profile.plans[0] if program_id is None else profile.plan_by_program_id(program_id)
    return "\n".join(
        (
            f"story={FPGA_IMAGE_UPDATE_STORY}",
            f"program_id={plan.program_id}",
            f"image_sha256={plan.image_sha256}",
            f"update_mode={UPDATE_MODE_GOWIN_REBUILD}",
            "bram_images_verified=",
            "generated_artifacts=",
            "gowin_build_root=build/fpga/tang_mega_138k/first_test",
            "gowin_audit_status=",
            "bitstream_path=",
            "bitstream_sha256=",
            "memory_update_support_verified=no",
            "memory_update_tool=none",
            "memory_update_log=none",
            "image_identity_recorded=",
            "report_path=",
            "recorded_at=",
            "",
        )
    )


def parse_image_update_evidence(text: str) -> ImageUpdateEvidenceRecord:
    fields: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        fields[key.strip()] = value.strip()
    return ImageUpdateEvidenceRecord(fields)


def audit_image_update(
    record: ImageUpdateEvidenceRecord,
    *,
    gowin_audit: fpga_gowin_build.GowinReportAudit | None = None,
) -> ImageUpdateAudit:
    profile = fpga_image_update_profile()
    required = (
        "story",
        "program_id",
        "image_sha256",
        "update_mode",
        "bram_images_verified",
        "generated_artifacts",
        "image_identity_recorded",
        "report_path",
        "recorded_at",
    )
    missing = [field for field in required if not record.value(field)]
    identity_issues: list[str] = []
    artifact_issues: list[str] = []

    program_id = record.value("program_id")
    update_mode = record.value("update_mode")
    try:
        plan = profile.plan_by_program_id(program_id)
    except KeyError:
        plan = None
        identity_issues.append("program_id is not in the I26-S01 manifest")

    if record.value("story") and record.value("story") != FPGA_IMAGE_UPDATE_STORY:
        identity_issues.append("story must be I26-S03")
    if plan is not None and record.value("image_sha256") != plan.image_sha256:
        identity_issues.append("image_sha256 does not match the selected manifest entry")
    if update_mode not in profile.supported_modes:
        identity_issues.append("update_mode must be gowin_rebuild or memory_update")

    artifacts = _artifact_set(record.value("generated_artifacts"))
    required_artifacts = set(plan.required_artifacts if plan is not None else ())
    for artifact in sorted(required_artifacts - artifacts):
        artifact_issues.append(f"missing generated artifact {artifact}")
    if record.value("bram_images_verified").lower() != "yes":
        artifact_issues.append("BRAM images must be verified before updating the bitstream")

    gowin_status = record.value("gowin_audit_status")
    if gowin_audit is not None:
        gowin_status = gowin_audit.status

    if update_mode == UPDATE_MODE_GOWIN_REBUILD:
        for field in ("gowin_build_root", "gowin_audit_status", "bitstream_path", "bitstream_sha256"):
            if not record.value(field):
                missing.append(field)
        if gowin_audit is not None and not gowin_audit.passed:
            artifact_issues.append("Gowin report audit must pass for rebuild mode")
        elif gowin_audit is None and record.value("gowin_audit_status") != fpga_gowin_build.GOWIN_AUDIT_PASSED:
            artifact_issues.append("gowin_audit_status must be passed for rebuild mode")
        if record.value("bitstream_sha256") and len(record.value("bitstream_sha256")) != 64:
            artifact_issues.append("bitstream_sha256 must be a 64-character SHA-256 hex digest")

    if update_mode == UPDATE_MODE_MEMORY_UPDATE:
        if record.value("memory_update_support_verified").lower() != "yes":
            artifact_issues.append("memory-update mode is blocked until tool support is verified")
        for field in ("memory_update_tool", "memory_update_log", "bitstream_sha256"):
            if not record.value(field) or record.value(field) == "none":
                artifact_issues.append(f"{field} is required for memory-update mode")

    if record.value("image_identity_recorded").lower() != "yes":
        identity_issues.append("image identity must be recorded in build and board evidence")

    missing_tuple = tuple(sorted(set(missing)))
    artifact_tuple = tuple(artifact_issues)
    identity_tuple = tuple(identity_issues)
    if missing_tuple or identity_tuple:
        return ImageUpdateAudit(
            status=UPDATE_FAILED,
            message="FPGA image update evidence is incomplete or names the wrong image.",
            program_id=program_id,
            update_mode=update_mode,
            gowin_status=gowin_status,
            missing_fields=missing_tuple,
            artifact_issues=artifact_tuple,
            identity_issues=identity_tuple,
            actions=("regenerate BRAM images and record the selected manifest image hash",),
        )
    if artifact_tuple:
        return ImageUpdateAudit(
            status=UPDATE_BLOCKED,
            message="FPGA image update is blocked until generated artifacts and tool reports pass.",
            program_id=program_id,
            update_mode=update_mode,
            gowin_status=gowin_status,
            missing_fields=(),
            artifact_issues=artifact_tuple,
            identity_issues=(),
            actions=("complete the Gowin rebuild audit or verify the memory-update tool path",),
        )
    return ImageUpdateAudit(
        status=UPDATE_PASSED,
        message="FPGA image update evidence is complete for the selected program image.",
        program_id=program_id,
        update_mode=update_mode,
        gowin_status=gowin_status,
        missing_fields=(),
        artifact_issues=(),
        identity_issues=(),
        actions=("hand the image identity and bitstream evidence to board programming",),
    )


def load_image_update_audit(
    root: Path,
    evidence_path: Path | None = None,
    gowin_build_root: Path | None = None,
) -> ImageUpdateAudit:
    if evidence_path is None:
        evidence_path = FPGA_IMAGE_UPDATE_EVIDENCE
    path = root / evidence_path
    if not path.exists():
        return ImageUpdateAudit(
            status=UPDATE_BLOCKED,
            message="FPGA image update evidence file is missing.",
            program_id="",
            update_mode="",
            gowin_status="",
            missing_fields=("evidence_file",),
            artifact_issues=(),
            identity_issues=(),
            actions=("capture I26-S03 image update evidence",),
        )
    gowin_audit = None
    if gowin_build_root is not None:
        gowin_audit = fpga_gowin_build.audit_gowin_report_bundle(root / gowin_build_root)
    return audit_image_update(parse_image_update_evidence(path.read_text(encoding="utf-8")), gowin_audit=gowin_audit)


def render_fpga_image_update_flow() -> str:
    profile = fpga_image_update_profile()
    lines = [
        "# FPGA Image Update Flow",
        "",
        f"Story: `{profile.story}`",
        f"BRAM image gate: `{profile.bram_image_gate}`",
        f"Gowin build gate: `{profile.gowin_build_gate}`",
        "",
        "## Plans",
        "",
    ]
    for plan in profile.plans:
        lines.extend(
            (
                f"### `{plan.program_id}`",
                "",
                f"- Image hash: `{plan.image_sha256}`.",
                f"- Default mode: `{plan.default_mode}`.",
                f"- Memory-update status: `{plan.memory_update_status}`.",
                "- Required artifacts: " + ", ".join(f"`{item}`" for item in plan.required_artifacts) + ".",
                "",
            )
        )
    return "\n".join(lines)


def validate_fpga_image_update_flow(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    issues: list[str] = []
    profile = fpga_image_update_profile()

    if profile.story != FPGA_IMAGE_UPDATE_STORY:
        issues.append("FPGA image update story mismatch")
    issues.extend(fpga_bram_images.validate_fpga_bram_images(root))
    issues.extend(fpga_gowin_build.validate_fpga_gowin_build(root))

    if set(profile.supported_modes) != {UPDATE_MODE_GOWIN_REBUILD, UPDATE_MODE_MEMORY_UPDATE}:
        issues.append("FPGA image update modes must include rebuild and memory-update")
    for plan in profile.plans:
        if plan.default_mode != UPDATE_MODE_GOWIN_REBUILD:
            issues.append(f"{plan.program_id}: default mode must be Gowin rebuild")
        if plan.memory_update_status != "blocked_until_tool_support_verified":
            issues.append(f"{plan.program_id}: memory-update status must be blocked")
        for artifact in ("rom.mem", "data.mem", "tags.mem"):
            if artifact not in plan.required_artifacts:
                issues.append(f"{plan.program_id}: missing required artifact {artifact}")
        if len(plan.image_sha256) != 64:
            issues.append(f"{plan.program_id}: image hash must be SHA-256")

    default_audit = audit_image_update(parse_image_update_evidence(image_update_evidence_template()))
    if default_audit.status != UPDATE_FAILED:
        issues.append("default image update template must not audit as passed")

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"FPGA image update profile is not JSON serializable: {exc}")

    doc = _read_if_exists(root / FPGA_IMAGE_UPDATE_DOC)
    for token in (
        "Story: I26-S03",
        FPGA_IMAGE_UPDATE_TOOL,
        "python tools\\fpga_bram_images.py --check",
        "python tools\\fpga_gowin_build.py --check",
        "gowin_rebuild",
        "memory_update",
        "rom.mem",
        "data.mem",
        "tags.mem",
        "image_sha256",
        "bitstream_sha256",
        "python tools\\fpga_image_update_flow.py --template",
        "python tools\\fpga_image_update_flow.py --audit-evidence",
        "I26-S04",
        "I24-S04",
    ):
        if token not in doc:
            issues.append(f"{FPGA_IMAGE_UPDATE_DOC.as_posix()} missing {token}")
    return tuple(issues)


def _plan_for_bundle(bundle: fpga_bram_images.FpgaBramImageBundle) -> ImageUpdatePlan:
    artifacts = tuple(Path(artifact.artifact_path).name for artifact in bundle.artifacts)
    return ImageUpdatePlan(
        program_id=bundle.program_id,
        image_sha256=bundle.manifest_image_sha256,
        default_mode=UPDATE_MODE_GOWIN_REBUILD,
        memory_update_status="blocked_until_tool_support_verified",
        required_artifacts=artifacts,
        rebuild_commands=(
            f"python tools\\fpga_bram_images.py --write --out-dir . --program {bundle.program_id}",
            "python tools\\fpga_synthesis_gate.py --gowin-tcl",
            "gw_sh build/fpga/tang_mega_138k/first_test/run_gowin.tcl",
            "python tools\\fpga_gowin_build.py --audit-reports build\\fpga\\tang_mega_138k\\first_test",
        ),
        evidence_fields=(
            "program_id",
            "image_sha256",
            "update_mode",
            "generated_artifacts",
            "gowin_audit_status",
            "bitstream_path",
            "bitstream_sha256",
            "image_identity_recorded",
        ),
    )


def _artifact_set(raw: str) -> set[str]:
    return {Path(part.strip()).name for part in raw.replace(";", ",").split(",") if part.strip()}


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")
