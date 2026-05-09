"""FPGA external-memory cache, ordering, and tag policy profile.

Owner stories:
- I29-S04: define cache, ordering, and capability-tag policy for external memory.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import (
    capabilities as caps,
    cells,
    fpga_ddr_wrapper,
    fpga_external_memory,
    fpga_external_memory_tests,
    mmu,
)


JsonValue = Any

FPGA_EXTERNAL_MEMORY_POLICY_STORY = "I29-S04"
FPGA_EXTERNAL_MEMORY_POLICY_DOC = Path("docs/implementation/fpga-external-memory-policy.md")
FPGA_EXTERNAL_MEMORY_POLICY_TOOL = "python tools\\fpga_external_memory_policy.py --check"
FPGA_EXTERNAL_MEMORY_POLICY_STATUS = "normal_uncacheable_no_tag_sidecar"
MEMORY_LITMUS_GATE = "python -m unittest tests.litmus.test_i06_s04_memory_litmus"
TAG_INTEGRITY_GATE = "python -m unittest tests.conformance.test_i15_s02_tag_integrity"

REQUIRED_POLICY_AREAS = frozenset(
    {
        "memory_type",
        "ordering",
        "cache_maintenance",
        "tag_policy",
        "firmware_handoff",
    }
)


class ExternalMemoryPolicyFault(RuntimeError):
    def __init__(self, cause: str, address: int, detail: str) -> None:
        super().__init__(detail)
        self.cause = cause
        self.address = address
        self.detail = detail


@dataclass(frozen=True)
class FpgaExternalMemoryPolicyRule:
    name: str
    area: str
    requirement: str
    evidence: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("external-memory policy rule name must not be empty")
        if self.area not in REQUIRED_POLICY_AREAS:
            raise ValueError(f"unknown external-memory policy area {self.area!r}")
        if not self.requirement:
            raise ValueError("external-memory policy requirement must not be empty")
        if not self.evidence:
            raise ValueError("external-memory policy evidence must not be empty")

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "area": self.area,
            "requirement": self.requirement,
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class FpgaExternalMemoryPolicyFixture:
    case_id: str
    area: str
    expected: str
    observed: str
    passed: bool

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "case_id": self.case_id,
            "area": self.area,
            "expected": self.expected,
            "observed": self.observed,
            "passed": self.passed,
        }


@dataclass(frozen=True)
class FpgaExternalMemoryPolicyRun:
    story: str
    selected_memory_type: int
    selected_memory_type_name: str
    capability_tags_supported: bool
    cache_maintenance_required_for_cpu_payload: bool
    off_bram_execution_allowed: bool
    fixtures: tuple[FpgaExternalMemoryPolicyFixture, ...]

    @property
    def passed(self) -> bool:
        return all(fixture.passed for fixture in self.fixtures)

    def fixture_by_id(self, case_id: str) -> FpgaExternalMemoryPolicyFixture:
        for fixture in self.fixtures:
            if fixture.case_id == case_id:
                return fixture
        raise KeyError(case_id)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "selected_memory_type": self.selected_memory_type,
            "selected_memory_type_name": self.selected_memory_type_name,
            "capability_tags_supported": self.capability_tags_supported,
            "cache_maintenance_required_for_cpu_payload": self.cache_maintenance_required_for_cpu_payload,
            "off_bram_execution_allowed": self.off_bram_execution_allowed,
            "passed": self.passed,
            "fixtures": [fixture.as_dict() for fixture in self.fixtures],
        }


@dataclass(frozen=True)
class FpgaExternalMemoryPolicyProfile:
    story: str
    status: str
    boundary_gate: str
    ddr_wrapper_gate: str
    firmware_gate: str
    memory_litmus_gate: str
    tag_integrity_gate: str
    external_window_name: str
    external_window_base: int
    external_window_end: int
    selected_memory_type: int
    selected_memory_type_name: str
    cache_policy: str
    ordering_policy: str
    tag_policy: str
    firmware_policy: str
    rules: tuple[FpgaExternalMemoryPolicyRule, ...]
    handoffs: tuple[str, ...]
    blockers: tuple[str, ...]

    def rule_by_name(self, name: str) -> FpgaExternalMemoryPolicyRule:
        normalized = name.lower()
        for rule in self.rules:
            if rule.name.lower() == normalized:
                return rule
        raise KeyError(name)

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "status": self.status,
            "boundary_gate": self.boundary_gate,
            "ddr_wrapper_gate": self.ddr_wrapper_gate,
            "firmware_gate": self.firmware_gate,
            "memory_litmus_gate": self.memory_litmus_gate,
            "tag_integrity_gate": self.tag_integrity_gate,
            "external_window_name": self.external_window_name,
            "external_window_base": self.external_window_base,
            "external_window_end": self.external_window_end,
            "selected_memory_type": self.selected_memory_type,
            "selected_memory_type_name": self.selected_memory_type_name,
            "cache_policy": self.cache_policy,
            "ordering_policy": self.ordering_policy,
            "tag_policy": self.tag_policy,
            "firmware_policy": self.firmware_policy,
            "rules": [rule.as_dict() for rule in self.rules],
            "handoffs": list(self.handoffs),
            "blockers": list(self.blockers),
        }


def fpga_external_memory_policy_profile() -> FpgaExternalMemoryPolicyProfile:
    external_profile = fpga_external_memory.fpga_external_memory_profile()
    window = external_profile.window_by_name("external_ddr_payload")
    return FpgaExternalMemoryPolicyProfile(
        story=FPGA_EXTERNAL_MEMORY_POLICY_STORY,
        status=FPGA_EXTERNAL_MEMORY_POLICY_STATUS,
        boundary_gate=fpga_external_memory.FPGA_EXTERNAL_MEMORY_TOOL,
        ddr_wrapper_gate=fpga_ddr_wrapper.FPGA_DDR_WRAPPER_TOOL,
        firmware_gate=fpga_external_memory_tests.FPGA_EXTERNAL_MEMORY_TESTS_TOOL,
        memory_litmus_gate=MEMORY_LITMUS_GATE,
        tag_integrity_gate=TAG_INTEGRITY_GATE,
        external_window_name=window.name,
        external_window_base=window.base_cell,
        external_window_end=window.end_cell,
        selected_memory_type=mmu.MEMORY_TYPE_NORMAL_UNCACHEABLE,
        selected_memory_type_name="normal_uncacheable",
        cache_policy=(
            "External DDR is treated as normal_uncacheable for first bring-up: "
            "CPU payload LD/ST do not allocate a coherent cache line, and cache "
            "maintenance is not required for the I29-S03 CPU-only firmware tests."
        ),
        ordering_policy=(
            "CPU payload LD/ST to external DDR are observed in program order at the "
            "DDR calibration gate; no cross-core coherent sharing or external-agent "
            "ownership handoff is claimed in I29-S04."
        ),
        tag_policy=(
            "No trusted external capability-tag sidecar exists. LD48/ST48 payload "
            "traffic is allowed, CLC/CSC to external_ddr_payload raise ACCESS_FAULT, "
            "and payload or DMA-style writes cannot forge valid tags."
        ),
        firmware_policy=(
            "I29-S03 firmware remains BRAM-resident, uses external DDR only as data "
            "memory, emits debug/status progress, and preserves the first ACCESS_FAULT "
            "sample for expected alignment or controller-error cases."
        ),
        rules=_policy_rules(),
        handoffs=(
            "I29-S05 captures board evidence for the conservative normal_uncacheable/no-tag policy before any pass claim",
            "A later cacheable-DDR story must add coherent/cacheable litmus evidence before changing the selected memory type",
            "A later tag-sidecar story must prove trusted tag storage, tag clear, and non-forgery before enabling CLC/CSC",
        ),
        blockers=(
            "cpu_v01_fpga_top still lacks the external-memory decoder that will enforce this policy in RTL",
            "board DDR controller IP, CST pin overlay, timing reports, and bitstream evidence are still blocked",
            "off-BRAM instruction fetch and trusted external capability tags remain unsupported",
        ),
    )


def fpga_external_memory_policy_json(*, indent: int = 2) -> str:
    return json.dumps(
        fpga_external_memory_policy_profile().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def fpga_external_memory_policy_run_json(*, indent: int = 2) -> str:
    return json.dumps(
        run_fpga_external_memory_policy_fixtures().as_dict(),
        indent=indent,
        sort_keys=True,
    )


def run_fpga_external_memory_policy_fixtures() -> FpgaExternalMemoryPolicyRun:
    profile = fpga_external_memory_policy_profile()
    window = cells.cell_range(
        profile.external_window_base,
        profile.external_window_end - profile.external_window_base,
    )
    fixtures = (
        _memory_type_fixture(profile),
        _ordering_fixture(window),
        _cache_maintenance_fixture(window),
        _tag_policy_fixture(window),
        _firmware_handoff_fixture(),
    )
    return FpgaExternalMemoryPolicyRun(
        story=FPGA_EXTERNAL_MEMORY_POLICY_STORY,
        selected_memory_type=profile.selected_memory_type,
        selected_memory_type_name=profile.selected_memory_type_name,
        capability_tags_supported=False,
        cache_maintenance_required_for_cpu_payload=False,
        off_bram_execution_allowed=False,
        fixtures=fixtures,
    )


def render_fpga_external_memory_policy() -> str:
    profile = fpga_external_memory_policy_profile()
    lines = [
        "# FPGA External Memory Policy",
        "",
        f"Story: {profile.story}",
        f"Status: `{profile.status}`",
        f"Window: `{profile.external_window_name}` "
        f"`0x{profile.external_window_base:08X}`..`0x{profile.external_window_end:08X}`",
        f"Memory type: `{profile.selected_memory_type_name}`",
        "",
        "## Rules",
        "",
        "| Rule | Area | Requirement | Evidence |",
        "| --- | --- | --- | --- |",
    ]
    for rule in profile.rules:
        lines.append(f"| `{rule.name}` | `{rule.area}` | {rule.requirement} | {rule.evidence} |")
    lines.extend(["", "## Handoffs", ""])
    lines.extend(f"- {handoff}." for handoff in profile.handoffs)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_external_memory_policy(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    profile = fpga_external_memory_policy_profile()
    run = run_fpga_external_memory_policy_fixtures()
    issues: list[str] = []

    if profile.story != FPGA_EXTERNAL_MEMORY_POLICY_STORY or run.story != FPGA_EXTERNAL_MEMORY_POLICY_STORY:
        issues.append("FPGA external-memory policy story mismatch")
    if profile.status != FPGA_EXTERNAL_MEMORY_POLICY_STATUS:
        issues.append("FPGA external-memory policy status mismatch")
    if profile.selected_memory_type != mmu.MEMORY_TYPE_NORMAL_UNCACHEABLE:
        issues.append("external DDR policy must select normal_uncacheable for first bring-up")
    if profile.selected_memory_type_name != "normal_uncacheable":
        issues.append("external DDR policy must name normal_uncacheable")

    issues.extend(fpga_external_memory.validate_fpga_external_memory(root))
    issues.extend(fpga_ddr_wrapper.validate_fpga_ddr_wrapper(root))
    issues.extend(fpga_external_memory_tests.validate_fpga_external_memory_tests(root))

    external_window = fpga_external_memory.fpga_external_memory_profile().window_by_name(
        "external_ddr_payload"
    )
    if profile.external_window_base != external_window.base_cell:
        issues.append("external-memory policy base must match external_ddr_payload")
    if profile.external_window_end != external_window.end_cell:
        issues.append("external-memory policy end must match external_ddr_payload")
    if external_window.memory_type != mmu.MEMORY_TYPE_NORMAL_UNCACHEABLE:
        issues.append("I29-S01 external window must remain normal_uncacheable")

    areas = {rule.area for rule in profile.rules}
    for area in sorted(REQUIRED_POLICY_AREAS - areas):
        issues.append(f"missing external-memory policy area {area}")
    rule_names = {rule.name for rule in profile.rules}
    for required in (
        "select_normal_uncacheable",
        "preserve_program_order_for_payload",
        "no_cache_maintenance_for_cpu_payload",
        "fault_external_clc_csc",
        "bram_resident_firmware_only",
    ):
        if required not in rule_names:
            issues.append(f"missing external-memory policy rule {required}")

    if not run.passed:
        issues.append("external-memory policy fixtures must pass")
    if run.capability_tags_supported:
        issues.append("external-memory policy must keep capability tags unsupported")
    if run.cache_maintenance_required_for_cpu_payload:
        issues.append("I29-S03 CPU-only payload tests must not require cache maintenance")
    if run.off_bram_execution_allowed:
        issues.append("off-BRAM execution must remain disabled in I29-S04")
    if "ACCESS_FAULT" not in run.fixture_by_id("tag_policy.external_capability_ops_fault").observed:
        issues.append("tag policy fixture must observe ACCESS_FAULT for CLC/CSC")
    if "normal_uncacheable" not in run.fixture_by_id("memory_type.external_window").observed:
        issues.append("memory-type fixture must observe normal_uncacheable")

    issues.extend(_validate_doc(root))

    try:
        json.dumps(profile.as_dict(), sort_keys=True)
        json.dumps(run.as_dict(), sort_keys=True)
    except TypeError as exc:
        issues.append(f"external-memory policy objects are not JSON serializable: {exc}")

    return tuple(issues)


def _policy_rules() -> tuple[FpgaExternalMemoryPolicyRule, ...]:
    return (
        FpgaExternalMemoryPolicyRule(
            "select_normal_uncacheable",
            "memory_type",
            "The first external_ddr_payload window remains normal_uncacheable.",
            "I29-S01 window profile and I29-S04 memory-type fixture.",
        ),
        FpgaExternalMemoryPolicyRule(
            "preserve_program_order_for_payload",
            "ordering",
            "BRAM-resident firmware observes its own external DDR payload stores before later loads.",
            "I29-S04 ordering fixture and I29-S03 walking/burst firmware cases.",
        ),
        FpgaExternalMemoryPolicyRule(
            "no_cache_maintenance_for_cpu_payload",
            "cache_maintenance",
            "CPU-only LD48/ST48 payload tests require no CACHE.CLEAN, CACHE.INVAL, or CACHE.CLEANINVAL.",
            "I06-S04 memory litmus remains the cache-maintenance reference gate.",
        ),
        FpgaExternalMemoryPolicyRule(
            "fault_external_clc_csc",
            "tag_policy",
            "CLC and CSC to external_ddr_payload raise CPU-owned ACCESS_FAULT until a trusted tag sidecar exists.",
            "I29-S04 tag fixture and I15-S02 tag non-forgery gate.",
        ),
        FpgaExternalMemoryPolicyRule(
            "payload_writes_do_not_forge_tags",
            "tag_policy",
            "Integer and DMA-style payload writes into external DDR cannot create valid capability tags.",
            "I29-S04 tag fixture uses serialized capability payload bits with all tags remaining invalid.",
        ),
        FpgaExternalMemoryPolicyRule(
            "bram_resident_firmware_only",
            "firmware_handoff",
            "External-memory test firmware runs from BRAM and uses external DDR as data memory only.",
            "I29-S03 firmware profile and I29-S05 board-evidence handoff.",
        ),
    )


def _memory_type_fixture(
    profile: FpgaExternalMemoryPolicyProfile,
) -> FpgaExternalMemoryPolicyFixture:
    passed = (
        profile.selected_memory_type == mmu.MEMORY_TYPE_NORMAL_UNCACHEABLE
        and profile.selected_memory_type_name == "normal_uncacheable"
    )
    return FpgaExternalMemoryPolicyFixture(
        "memory_type.external_window",
        "memory_type",
        "external_ddr_payload uses normal_uncacheable",
        f"{profile.external_window_name} selected {profile.selected_memory_type_name}",
        passed,
    )


def _ordering_fixture(window: cells.CellRange) -> FpgaExternalMemoryPolicyFixture:
    model = _ExternalPayloadPolicyModel(window)
    address = window.base + 0x6000
    model.st48(address, 0x112233445566)
    observed = model.ld48(address)
    passed = observed == 0x112233445566
    return FpgaExternalMemoryPolicyFixture(
        "ordering.payload_store_then_load",
        "ordering",
        "a later LD48 observes the prior ST48 payload value",
        f"LD48 read 0x{observed:012X} after ST48",
        passed,
    )


def _cache_maintenance_fixture(window: cells.CellRange) -> FpgaExternalMemoryPolicyFixture:
    model = _ExternalPayloadPolicyModel(window)
    address = window.base + 0x7000
    model.st48(address, 0x00AA55AA55AA)
    clean = model.cache_maintenance(address, "CACHE.CLEAN")
    inval = model.cache_maintenance(address, "CACHE.INVAL")
    readback = model.ld48(address)
    passed = readback == 0x00AA55AA55AA and not model.capability_tag(address) and clean and inval
    return FpgaExternalMemoryPolicyFixture(
        "cache_maintenance.cpu_payload_not_required",
        "cache_maintenance",
        "CPU-only normal_uncacheable payload tests do not require cache maintenance",
        f"CACHE.CLEAN={clean}; CACHE.INVAL={inval}; readback=0x{readback:012X}; tag={model.capability_tag(address)}",
        passed,
    )


def _tag_policy_fixture(window: cells.CellRange) -> FpgaExternalMemoryPolicyFixture:
    model = _ExternalPayloadPolicyModel(window)
    address = window.base + 0x8000
    payload = caps.CapabilityPayload(
        cursor=address,
        bounds_metadata=caps.encode_bounds_metadata(window.base, window.top),
        permissions=int(caps.CapabilityPermission.LD),
        flags=int(caps.CapabilityFlag.G),
    )
    payload_cells = caps.payload_to_cells(payload)
    model.write_cells(address, payload_cells)
    tag_after_payload = model.capability_tag(address)

    faults: list[str] = []
    for opname, operation in (
        ("CLC", lambda: model.clc(address)),
        ("CSC", lambda: model.csc(address, caps.Capability.valid(payload))),
    ):
        try:
            operation()
        except ExternalMemoryPolicyFault as exc:
            faults.append(f"{opname} {exc.cause}")

    model.dma_write_cells(address, payload_cells)
    tag_after_dma = model.capability_tag(address)
    passed = faults == ["CLC ACCESS_FAULT", "CSC ACCESS_FAULT"] and not tag_after_payload and not tag_after_dma
    return FpgaExternalMemoryPolicyFixture(
        "tag_policy.external_capability_ops_fault",
        "tag_policy",
        "CLC/CSC fault and payload or DMA-style writes cannot create tags",
        f"{'; '.join(faults)}; payload_tag={tag_after_payload}; dma_tag={tag_after_dma}",
        passed,
    )


def _firmware_handoff_fixture() -> FpgaExternalMemoryPolicyFixture:
    profile = fpga_external_memory_tests.fpga_external_memory_tests_profile()
    run = fpga_external_memory_tests.run_fpga_external_memory_tests()
    categories = {case.category for case in profile.cases}
    passed = (
        profile.execution_region == "bram_resident"
        and profile.board_status == "blocked_until_board_ddr_ip"
        and fpga_external_memory_tests.REQUIRED_EXTERNAL_MEMORY_TEST_CATEGORIES <= categories
        and run.passed
    )
    return FpgaExternalMemoryPolicyFixture(
        "firmware_handoff.i29_s03_payload_only",
        "firmware_handoff",
        "I29-S03 firmware is BRAM-resident and payload-only",
        f"{profile.program_id}; categories={','.join(sorted(categories))}; run_passed={run.passed}",
        passed,
    )


class _ExternalPayloadPolicyModel:
    def __init__(self, window: cells.CellRange) -> None:
        self.window = window
        self._cells: dict[int, int] = {}

    def st48(self, address: int, value: int) -> None:
        self._require_integer_address(address)
        value &= (1 << (cells.INTEGER_OBJECT_CELLS * cells.CELL_BITS)) - 1
        self.write_cells(
            address,
            (
                value & cells.CELL_MASK,
                (value >> cells.CELL_BITS) & cells.CELL_MASK,
            ),
        )

    def ld48(self, address: int) -> int:
        self._require_integer_address(address)
        low = self._cells.get(address, 0)
        high = self._cells.get(address + 1, 0)
        return low | (high << cells.CELL_BITS)

    def write_cells(self, address: int, values: tuple[int, ...]) -> None:
        for offset, value in enumerate(values):
            cell_address = cells.require_cell_address(address + offset)
            if not self.window.contains_address(cell_address):
                raise ExternalMemoryPolicyFault(
                    "ACCESS_FAULT",
                    cell_address,
                    "external DDR payload write outside external_ddr_payload",
                )
            self._cells[cell_address] = cells.require_cell_value(value)

    def dma_write_cells(self, address: int, values: tuple[int, ...]) -> None:
        self.write_cells(address, values)

    def clc(self, address: int) -> caps.Capability:
        self._require_capability_address(address)
        raise ExternalMemoryPolicyFault(
            "ACCESS_FAULT",
            address,
            "external DDR has no trusted capability-tag sidecar",
        )

    def csc(self, address: int, capability: caps.Capability) -> None:
        if not isinstance(capability, caps.Capability):
            raise TypeError("capability must be a Capability")
        self._require_capability_address(address)
        raise ExternalMemoryPolicyFault(
            "ACCESS_FAULT",
            address,
            "external DDR has no trusted capability-tag sidecar",
        )

    def capability_tag(self, address: int) -> bool:
        self._require_capability_address(address)
        return False

    def cache_maintenance(self, address: int, operation: str) -> bool:
        if operation not in {"CACHE.CLEAN", "CACHE.INVAL", "CACHE.CLEANINVAL"}:
            raise ValueError(f"unknown cache maintenance operation {operation!r}")
        address = cells.require_cell_address(address)
        if not self.window.contains_address(address):
            raise ExternalMemoryPolicyFault(
                "ACCESS_FAULT",
                address,
                "external DDR cache maintenance outside external_ddr_payload",
            )
        return True

    def _require_integer_address(self, address: int) -> None:
        address = cells.require_cell_address(address)
        if not cells.is_aligned(address, cells.INTEGER_OBJECT_CELLS):
            raise ExternalMemoryPolicyFault(
                "ALIGN_FAULT",
                address,
                "external DDR integer payload access is misaligned",
            )
        if not self.window.contains_range(cells.cell_range(address, cells.INTEGER_OBJECT_CELLS)):
            raise ExternalMemoryPolicyFault(
                "ACCESS_FAULT",
                address,
                "external DDR integer payload access outside external_ddr_payload",
            )

    def _require_capability_address(self, address: int) -> None:
        address = cells.require_cell_address(address)
        if not cells.is_aligned(address, cells.CAPABILITY_OBJECT_CELLS):
            raise ExternalMemoryPolicyFault(
                "ALIGN_FAULT",
                address,
                "external DDR capability access is misaligned",
            )
        if not self.window.contains_range(cells.cell_range(address, cells.CAPABILITY_OBJECT_CELLS)):
            raise ExternalMemoryPolicyFault(
                "ACCESS_FAULT",
                address,
                "external DDR capability access outside external_ddr_payload",
            )


def _validate_doc(root: Path) -> tuple[str, ...]:
    doc = _read_if_exists(root / FPGA_EXTERNAL_MEMORY_POLICY_DOC)
    issues: list[str] = []
    for token in (
        "Story: I29-S04",
        FPGA_EXTERNAL_MEMORY_POLICY_TOOL,
        "python tools\\fpga_external_memory.py --check",
        "python tools\\fpga_ddr_wrapper.py --check",
        "python tools\\fpga_external_memory_tests.py --check",
        MEMORY_LITMUS_GATE,
        TAG_INTEGRITY_GATE,
        "normal_uncacheable",
        "external_ddr_payload",
        "CACHE.CLEAN",
        "CACHE.INVAL",
        "CLC",
        "CSC",
        "ACCESS_FAULT",
        "tag sidecar",
        "BRAM-resident",
        "I29-S05",
    ):
        if token not in doc:
            issues.append(f"{FPGA_EXTERNAL_MEMORY_POLICY_DOC.as_posix()} missing {token}")
    return tuple(issues)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")
