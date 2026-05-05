"""Invariant registry for CPU v0.1 conformance coverage.

Owner stories:
- E15-S01: audit matrix and story traceability.
- E15-S04: precise exception and no-side-effect audit.
- E15-S05: capability/tag security audit.
- I16-S01: formal invariant registry and coverage matrix.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re


STORY_RE = re.compile(r"^[EI]\d{2}-S\d{2}$")


class InvariantArea(Enum):
    AUTHORITY = "AUTHORITY"
    TAG_INTEGRITY = "TAG_INTEGRITY"
    PRECISE_EFFECTS = "PRECISE_EFFECTS"
    MEMORY_MODEL = "MEMORY_MODEL"
    SOFTWARE_CONTRACT = "SOFTWARE_CONTRACT"


@dataclass(frozen=True)
class InvariantCheck:
    key: str
    area: InvariantArea
    summary: str
    implementation_story: str
    owner_stories: tuple[str, ...]
    e15_coverage: tuple[str, ...]
    artifacts: tuple[str, ...]
    surfaces: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.key or not self.key.replace("_", "").isalnum():
            raise ValueError("invariant key must be non-empty snake-like text")
        object.__setattr__(self, "area", InvariantArea(self.area))
        if not self.summary:
            raise ValueError("invariant summary must not be empty")
        _require_story_id(self.implementation_story, "implementation_story")
        _require_non_empty_story_tuple(self.owner_stories, "owner_stories")
        _require_non_empty_story_tuple(self.e15_coverage, "e15_coverage")
        if not all(story.startswith("E15-") for story in self.e15_coverage):
            raise ValueError("e15_coverage must only contain E15 stories")
        _require_non_empty_text_tuple(self.artifacts, "artifacts")
        _require_non_empty_text_tuple(self.surfaces, "surfaces")


def _require_story_id(story: str, name: str) -> None:
    if not isinstance(story, str) or not STORY_RE.match(story):
        raise ValueError(f"{name} must be a story id")


def _require_non_empty_story_tuple(values: tuple[str, ...], name: str) -> None:
    if not values:
        raise ValueError(f"{name} must not be empty")
    for value in values:
        _require_story_id(value, name)


def _require_non_empty_text_tuple(values: tuple[str, ...], name: str) -> None:
    if not values or not all(isinstance(value, str) and value for value in values):
        raise ValueError(f"{name} must contain non-empty strings")


INVARIANT_CHECKS: tuple[InvariantCheck, ...] = (
    InvariantCheck(
        key="capability_monotonicity",
        area=InvariantArea.AUTHORITY,
        summary="Capability derivation cannot widen authority or synthesize valid tags.",
        implementation_story="I15-S01",
        owner_stories=("E03-S03", "E04-S05"),
        e15_coverage=("E15-S01", "E15-S05"),
        artifacts=(
            "tests\\conformance\\test_i15_s01_capability_monotonicity.py",
            "docs\\implementation\\capability-monotonicity-properties.md",
        ),
        surfaces=(
            "CSETADDR",
            "CINCADDR",
            "CSETBOUNDS",
            "CANDPERM",
            "CSEAL",
            "CUNSEAL",
        ),
    ),
    InvariantCheck(
        key="tag_non_forgery",
        area=InvariantArea.TAG_INTEGRITY,
        summary="Payload movement, stores, DMA, CCSRs, and debug views cannot forge tags.",
        implementation_story="I15-S02",
        owner_stories=(
            "E03-S04",
            "E04-S03",
            "E10-S03",
            "E10-S04",
            "E10-S05",
            "E12-S03",
        ),
        e15_coverage=("E15-S01", "E15-S05", "E15-S06"),
        artifacts=(
            "tests\\conformance\\test_i15_s02_tag_integrity.py",
            "docs\\implementation\\tag-integrity-properties.md",
        ),
        surfaces=(
            "ST48",
            "CLC",
            "CSC",
            "serialization",
            "cache/DMA",
            "CCSR",
            "debug",
        ),
    ),
    InvariantCheck(
        key="precise_fault_effects",
        area=InvariantArea.PRECISE_EFFECTS,
        summary="Faulting operations suppress partial register, memory, tag, TLB, and protected-stack effects.",
        implementation_story="I15-S03",
        owner_stories=(
            "E07-S03",
            "E07-S04",
            "E09-S02",
            "E09-S07",
            "E15-S04",
        ),
        e15_coverage=("E15-S01", "E15-S04", "E15-S05"),
        artifacts=(
            "tests\\conformance\\test_i15_s03_precise_fault_effects.py",
            "docs\\implementation\\precise-fault-properties.md",
        ),
        surfaces=(
            "fault packets",
            "RADIX4",
            "SFENCE.VM",
            "LL/SC",
            "trap entry",
            "protected return stack",
        ),
    ),
    InvariantCheck(
        key="commit_boundary_atomicity",
        area=InvariantArea.PRECISE_EFFECTS,
        summary="Normal retire effects are represented as one atomic commit packet for RTL handoff.",
        implementation_story="I10-S01",
        owner_stories=("E07-S03", "E13-S01", "E15-S07"),
        e15_coverage=("E15-S03", "E15-S04", "E15-S05", "E15-S07"),
        artifacts=(
            "tests\\conformance\\test_i10_s01_rtl_handoff.py",
            "docs\\implementation\\rtl-handoff.md",
        ),
        surfaces=(
            "integer registers",
            "capability registers",
            "CSR/CCSR",
            "memory effects",
            "TLB effects",
            "reservation effects",
        ),
    ),
    InvariantCheck(
        key="software_visible_capability_contracts",
        area=InvariantArea.SOFTWARE_CONTRACT,
        summary="ABI/debug contracts preserve capability payload, tag, slot, and protected-stack visibility rules.",
        implementation_story="I09-S04",
        owner_stories=("E05-S04", "E12-S01", "E12-S03", "E15-S06"),
        e15_coverage=("E15-S03", "E15-S06"),
        artifacts=(
            "tests\\conformance\\test_i09_s04_debug_abi.py",
            "docs\\implementation\\debugger-abi.md",
        ),
        surfaces=(
            "debug register view",
            "protected unwind",
            "capability tags",
            "PCC/EPCC slots",
        ),
    ),
)


def invariant_checks(
    area: InvariantArea | str | None = None,
) -> tuple[InvariantCheck, ...]:
    if area is None:
        return INVARIANT_CHECKS
    selected = InvariantArea(area)
    return tuple(check for check in INVARIANT_CHECKS if check.area is selected)


def invariant_keys() -> tuple[str, ...]:
    return tuple(check.key for check in INVARIANT_CHECKS)


def invariant_coverage_by_story() -> dict[str, tuple[InvariantCheck, ...]]:
    by_story: dict[str, list[InvariantCheck]] = {}
    for check in INVARIANT_CHECKS:
        by_story.setdefault(check.implementation_story, []).append(check)
        for story in check.owner_stories:
            by_story.setdefault(story, []).append(check)
        for story in check.e15_coverage:
            by_story.setdefault(story, []).append(check)
    return {
        story: tuple(items)
        for story, items in sorted(by_story.items())
    }


def validate_invariant_registry() -> tuple[str, ...]:
    issues: list[str] = []
    keys = invariant_keys()
    if len(keys) != len(set(keys)):
        issues.append("invariant keys must be unique")
    required_i15 = {"I15-S01", "I15-S02", "I15-S03"}
    implemented = {check.implementation_story for check in INVARIANT_CHECKS}
    for story in sorted(required_i15 - implemented):
        issues.append(f"missing invariant coverage for {story}")
    for area in (
        InvariantArea.AUTHORITY,
        InvariantArea.TAG_INTEGRITY,
        InvariantArea.PRECISE_EFFECTS,
    ):
        if not invariant_checks(area):
            issues.append(f"missing invariant area {area.value}")
    for check in INVARIANT_CHECKS:
        if not any(path.startswith("tests\\conformance\\") for path in check.artifacts):
            issues.append(f"{check.key} has no conformance test artifact")
        if not any(path.startswith("docs\\implementation\\") for path in check.artifacts):
            issues.append(f"{check.key} has no implementation doc artifact")
    return tuple(issues)
