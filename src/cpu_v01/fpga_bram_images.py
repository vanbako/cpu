"""Deterministic FPGA BRAM initialization image generation.

Owner stories:
- I26-S02: generate FPGA BRAM initialization images from fixtures.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_program_manifest, fpga_smoke


JsonValue = Any

FPGA_BRAM_IMAGES_STORY = "I26-S02"
FPGA_BRAM_IMAGES_DOC = Path("docs/implementation/fpga-bram-image-generation.md")
FPGA_BRAM_IMAGES_TOOL = "python tools\\fpga_bram_images.py --check"
FPGA_BRAM_WRITE_ROOT_EXAMPLE = Path("tmp_i26_s02_bram_images")


@dataclass(frozen=True)
class FpgaBramImageArtifact:
    program_id: str
    memory_name: str
    artifact_path: Path
    format_name: str
    line_count: int
    image_sha256: str
    expected_sha256: str
    first_non_fill_cell: int | None

    @property
    def matches_manifest(self) -> bool:
        return self.image_sha256 == self.expected_sha256

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "program_id": self.program_id,
            "memory_name": self.memory_name,
            "artifact_path": self.artifact_path.as_posix(),
            "format_name": self.format_name,
            "line_count": self.line_count,
            "image_sha256": self.image_sha256,
            "expected_sha256": self.expected_sha256,
            "matches_manifest": self.matches_manifest,
            "first_non_fill_cell": self.first_non_fill_cell,
        }


@dataclass(frozen=True)
class FpgaBramImageBundle:
    program_id: str
    source_case_id: str
    manifest_image_sha256: str
    artifacts: tuple[FpgaBramImageArtifact, ...]

    @property
    def passed(self) -> bool:
        return all(artifact.matches_manifest for artifact in self.artifacts)

    def artifact_by_memory(self, memory_name: str) -> FpgaBramImageArtifact:
        for artifact in self.artifacts:
            if artifact.memory_name == memory_name:
                return artifact
        raise KeyError(memory_name)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "program_id": self.program_id,
            "source_case_id": self.source_case_id,
            "manifest_image_sha256": self.manifest_image_sha256,
            "passed": self.passed,
            "artifacts": [artifact.as_dict() for artifact in self.artifacts],
        }


@dataclass(frozen=True)
class FpgaBramWriteReport:
    output_root: Path
    bundles: tuple[FpgaBramImageBundle, ...]
    files_written: tuple[Path, ...]

    @property
    def passed(self) -> bool:
        return all(bundle.passed for bundle in self.bundles)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "output_root": self.output_root.as_posix(),
            "passed": self.passed,
            "files_written": [path.as_posix() for path in self.files_written],
            "bundles": [bundle.as_dict() for bundle in self.bundles],
        }


def fpga_bram_image_bundles(
    program_id: str | None = None,
) -> tuple[FpgaBramImageBundle, ...]:
    profile = fpga_program_manifest.fpga_program_manifest_profile()
    entries = profile.entries if program_id is None else (profile.entry_by_id(program_id),)
    return tuple(_bundle_for_entry(entry) for entry in entries)


def fpga_bram_images_json(program_id: str | None = None, *, indent: int = 2) -> str:
    return json.dumps(
        [bundle.as_dict() for bundle in fpga_bram_image_bundles(program_id)],
        indent=indent,
        sort_keys=True,
    )


def render_bram_image(program_id: str, memory_name: str) -> str:
    entry = fpga_program_manifest.fpga_program_manifest_profile().entry_by_id(program_id)
    image = entry.memory_images()
    image_by_memory = {item.memory_name: item for item in image}
    if memory_name not in image_by_memory:
        raise KeyError(memory_name)
    values = entry.materialized_cells(memory_name)
    if image_by_memory[memory_name].format_name == fpga_program_manifest.FPGA_PROGRAM_TAG_FORMAT:
        return _hex1_lines(values)
    return _hex24_lines(values)


def write_bram_images(
    output_root: Path,
    program_id: str | None = None,
) -> FpgaBramWriteReport:
    output_root = Path(output_root)
    bundles = fpga_bram_image_bundles(program_id)
    files_written: list[Path] = []
    for bundle in bundles:
        for artifact in bundle.artifacts:
            path = output_root / artifact.artifact_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(render_bram_image(bundle.program_id, artifact.memory_name), encoding="ascii")
            files_written.append(path)
    return FpgaBramWriteReport(output_root, bundles, tuple(files_written))


def verify_written_bram_images(
    output_root: Path,
    program_id: str | None = None,
) -> tuple[str, ...]:
    output_root = Path(output_root)
    issues: list[str] = []
    for bundle in fpga_bram_image_bundles(program_id):
        for artifact in bundle.artifacts:
            path = output_root / artifact.artifact_path
            if not path.exists():
                issues.append(f"missing generated image {path.as_posix()}")
                continue
            observed = path.read_text(encoding="ascii")
            expected = render_bram_image(bundle.program_id, artifact.memory_name)
            if observed != expected:
                issues.append(f"generated image drifted: {path.as_posix()}")
            if _sha256(observed) != artifact.expected_sha256:
                issues.append(f"generated image hash mismatch: {path.as_posix()}")
    return tuple(issues)


def render_fpga_bram_images() -> str:
    lines = [
        "# FPGA BRAM Images",
        "",
        f"Story: `{FPGA_BRAM_IMAGES_STORY}`",
        f"Manifest gate: `{fpga_program_manifest.FPGA_PROGRAM_MANIFEST_TOOL}`",
        f"Smoke gate: `python tools\\fpga_smoke_firmware.py --check`",
        "",
        "## Bundles",
        "",
    ]
    for bundle in fpga_bram_image_bundles():
        lines.extend(
            (
                f"### `{bundle.program_id}`",
                "",
                f"- Source case: `{bundle.source_case_id}`.",
                f"- Manifest image hash: `{bundle.manifest_image_sha256}`.",
                "- Artifacts: "
                + ", ".join(
                    f"`{artifact.memory_name}` `{artifact.artifact_path.as_posix()}`"
                    for artifact in bundle.artifacts
                )
                + ".",
                "",
            )
        )
    return "\n".join(lines)


def validate_fpga_bram_images(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    issues: list[str] = []

    issues.extend(fpga_program_manifest.validate_fpga_program_manifest(root))
    issues.extend(fpga_smoke.validate_fpga_smoke_firmware(root))

    bundles = fpga_bram_image_bundles()
    if len(bundles) < 3:
        issues.append("FPGA BRAM image generator must cover every starter manifest entry")
    for bundle in bundles:
        if not bundle.passed:
            issues.append(f"{bundle.program_id}: generated image hashes do not match the manifest")
        artifacts = {artifact.memory_name: artifact for artifact in bundle.artifacts}
        if set(artifacts) != {"instruction_rom", "data_ram", "tag_ram"}:
            issues.append(f"{bundle.program_id}: missing ROM, data, or tag image")
        for memory_name, artifact in artifacts.items():
            rendered = render_bram_image(bundle.program_id, memory_name)
            if len(rendered.splitlines()) != artifact.line_count:
                issues.append(f"{bundle.program_id}:{memory_name}: rendered line count mismatch")
            if not rendered.endswith("\n"):
                issues.append(f"{bundle.program_id}:{memory_name}: rendered image must end with newline")
            if _sha256(rendered) != artifact.expected_sha256:
                issues.append(f"{bundle.program_id}:{memory_name}: rendered hash mismatch")
            if memory_name == "tag_ram" and set(rendered.splitlines()) - {"0", "1"}:
                issues.append(f"{bundle.program_id}: tag image contains non-bit lines")

    try:
        json.dumps([bundle.as_dict() for bundle in bundles], sort_keys=True)
    except TypeError as exc:
        issues.append(f"FPGA BRAM image bundles are not JSON serializable: {exc}")

    doc = _read_if_exists(root / FPGA_BRAM_IMAGES_DOC)
    for token in (
        "Story: I26-S02",
        FPGA_BRAM_IMAGES_TOOL,
        "python tools\\fpga_program_manifest.py --check",
        "python tools\\fpga_smoke_firmware.py --check",
        "rom.mem",
        "data.mem",
        "tags.mem",
        "hex24-cells-v1",
        "hex1-tags-v1",
        "instruction_rom",
        "data_ram",
        "tag_ram",
        "image_sha256",
        "--write",
        "--print-image",
        "simulator-visible expected cells and tags",
        "I26-S03",
    ):
        if token not in doc:
            issues.append(f"{FPGA_BRAM_IMAGES_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _bundle_for_entry(
    entry: fpga_program_manifest.FpgaProgramManifestEntry,
) -> FpgaBramImageBundle:
    artifacts = tuple(_artifact_for_image(entry, image) for image in entry.memory_images())
    return FpgaBramImageBundle(
        program_id=entry.program_id,
        source_case_id=entry.source_case_id,
        manifest_image_sha256=entry.image_sha256,
        artifacts=artifacts,
    )


def _artifact_for_image(
    entry: fpga_program_manifest.FpgaProgramManifestEntry,
    image: fpga_program_manifest.FpgaProgramMemoryImage,
) -> FpgaBramImageArtifact:
    rendered = render_bram_image(entry.program_id, image.memory_name)
    values = entry.materialized_cells(image.memory_name)
    fill = image.fill_value
    first_non_fill_cell = None
    for index, value in enumerate(values):
        if value != fill:
            first_non_fill_cell = index
            break
    return FpgaBramImageArtifact(
        program_id=entry.program_id,
        memory_name=image.memory_name,
        artifact_path=image.artifact_path,
        format_name=image.format_name,
        line_count=len(values),
        image_sha256=_sha256(rendered),
        expected_sha256=image.image_sha256,
        first_non_fill_cell=first_non_fill_cell,
    )


def _hex24_lines(values: tuple[int, ...]) -> str:
    return "".join(f"{value:06x}\n" for value in values)


def _hex1_lines(values: tuple[int, ...]) -> str:
    return "".join(f"{value & 1:x}\n" for value in values)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")
