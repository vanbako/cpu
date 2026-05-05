"""Seed-stable invariant runner for CPU v0.1.

Owner stories:
- E03-S03: monotonic capability derivation.
- E15-S04: precise exception and no-side-effect audit.
- E15-S05: capability/tag security audit.
- I16-S03: seed-stable invariant runner.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
import random

from . import capabilities as caps
from . import capability_ops, execution, invariant_cases, instructions, reset


CAPABILITY_DERIVATION_FAMILY = "capability_derivation"
INVALID_TAG_DERIVATION_FAMILY = "invalid_tag_derivation"
AVAILABLE_FAMILIES = (
    CAPABILITY_DERIVATION_FAMILY,
    INVALID_TAG_DERIVATION_FAMILY,
)

DESTINATION = 0
SOURCE = 1
AUTHORITY = 2
VALUE = 0


@dataclass(frozen=True)
class InvariantCaseResult:
    family: str
    case_id: str
    passed: bool
    detail: str = ""

    def __post_init__(self) -> None:
        if self.family not in AVAILABLE_FAMILIES:
            raise ValueError("unknown invariant family")
        if not self.case_id:
            raise ValueError("case_id must not be empty")
        if type(self.passed) is not bool:
            raise TypeError("passed must be a bool")


@dataclass(frozen=True)
class InvariantRunReport:
    seed: int
    requested_families: tuple[str, ...]
    results: tuple[InvariantCaseResult, ...]

    @property
    def case_count(self) -> int:
        return len(self.results)

    @property
    def passed_count(self) -> int:
        return sum(result.passed for result in self.results)

    @property
    def failure_count(self) -> int:
        return self.case_count - self.passed_count

    @property
    def passed(self) -> bool:
        return self.failure_count == 0

    @property
    def case_ids(self) -> tuple[str, ...]:
        return tuple(result.case_id for result in self.results)


@dataclass(frozen=True)
class _RunnableCase:
    family: str
    case_id: str
    run: Callable[[], None]


def available_families() -> tuple[str, ...]:
    return AVAILABLE_FAMILIES


def invariant_case_ids(families: Iterable[str] | None = None) -> tuple[str, ...]:
    return tuple(case.case_id for case in _runner_cases(_normalize_families(families)))


def run_invariants(
    *,
    seed: int = 0,
    families: Iterable[str] | None = None,
    case_ids: Iterable[str] | None = None,
) -> InvariantRunReport:
    if type(seed) is not int:
        raise TypeError("seed must be an int")
    requested_families = _normalize_families(families)
    cases = list(_runner_cases(requested_families))
    selected_case_ids = tuple(case_ids or ())
    if selected_case_ids:
        available = {case.case_id for case in cases}
        missing = tuple(case_id for case_id in selected_case_ids if case_id not in available)
        if missing:
            raise ValueError(f"unknown invariant case id {missing[0]}")
        selected = set(selected_case_ids)
        cases = [case for case in cases if case.case_id in selected]

    random.Random(seed).shuffle(cases)
    results: list[InvariantCaseResult] = []
    for case in cases:
        try:
            case.run()
        except Exception as exc:  # pragma: no cover - exercised by failure reproduction.
            results.append(
                InvariantCaseResult(
                    case.family,
                    case.case_id,
                    False,
                    f"{type(exc).__name__}: {exc}",
                )
            )
        else:
            results.append(InvariantCaseResult(case.family, case.case_id, True))
    return InvariantRunReport(seed, requested_families, tuple(results))


def render_report(report: InvariantRunReport) -> str:
    if not isinstance(report, InvariantRunReport):
        raise TypeError("report must be an InvariantRunReport")
    lines = [
        "Invariant Run",
        f"Seed: {report.seed}",
        f"Families: {', '.join(report.requested_families)}",
        f"Cases: {report.case_count}",
        f"Passed: {report.passed_count}",
        f"Failed: {report.failure_count}",
    ]
    for result in report.results:
        status = "PASS" if result.passed else "FAIL"
        line = f"{status} {result.case_id}"
        if result.detail:
            line = f"{line} {result.detail}"
        lines.append(line)
    return "\n".join(lines)


def _normalize_families(families: Iterable[str] | None) -> tuple[str, ...]:
    if families is None:
        return AVAILABLE_FAMILIES
    result = tuple(families)
    if not result:
        return AVAILABLE_FAMILIES
    for family in result:
        if family not in AVAILABLE_FAMILIES:
            raise ValueError(f"unknown invariant family {family!r}")
    return result


def _runner_cases(families: tuple[str, ...]) -> tuple[_RunnableCase, ...]:
    cases: list[_RunnableCase] = []
    if CAPABILITY_DERIVATION_FAMILY in families:
        cases.extend(_capability_derivation_cases())
    if INVALID_TAG_DERIVATION_FAMILY in families:
        cases.extend(_invalid_tag_derivation_cases())
    return tuple(cases)


def _capability_derivation_cases() -> tuple[_RunnableCase, ...]:
    cases: list[_RunnableCase] = []
    for case in invariant_cases.capability_derivation_cases():
        for candidate in case.candidate_addresses:
            case_id = f"{CAPABILITY_DERIVATION_FAMILY}/{case.name}/CSETADDR/address={candidate:#x}"
            cases.append(
                _RunnableCase(
                    CAPABILITY_DERIVATION_FAMILY,
                    case_id,
                    lambda case=case, candidate=candidate: _run_csetaddr(case, candidate),
                )
            )
        for offset in case.offsets:
            case_id = f"{CAPABILITY_DERIVATION_FAMILY}/{case.name}/CINCADDR/offset={_signed_hex(offset)}"
            cases.append(
                _RunnableCase(
                    CAPABILITY_DERIVATION_FAMILY,
                    case_id,
                    lambda case=case, offset=offset: _run_cincaddr(case, offset),
                )
            )
        for length in case.bounds_lengths:
            case_id = f"{CAPABILITY_DERIVATION_FAMILY}/{case.name}/CSETBOUNDS/length={length:#x}"
            cases.append(
                _RunnableCase(
                    CAPABILITY_DERIVATION_FAMILY,
                    case_id,
                    lambda case=case, length=length: _run_csetbounds(case, length),
                )
            )
        for mask in case.permission_masks:
            case_id = f"{CAPABILITY_DERIVATION_FAMILY}/{case.name}/CANDPERM/mask={mask:#x}"
            cases.append(
                _RunnableCase(
                    CAPABILITY_DERIVATION_FAMILY,
                    case_id,
                    lambda case=case, mask=mask: _run_candperm(case, mask),
                )
            )
        for otype in case.seal_object_types:
            case_id = f"{CAPABILITY_DERIVATION_FAMILY}/{case.name}/CSEAL/otype={otype:#x}"
            cases.append(
                _RunnableCase(
                    CAPABILITY_DERIVATION_FAMILY,
                    case_id,
                    lambda case=case, otype=otype: _run_cseal_cunseal(case, otype),
                )
            )
    return tuple(cases)


def _invalid_tag_derivation_cases() -> tuple[_RunnableCase, ...]:
    cases: list[_RunnableCase] = []
    derivations = (
        ("CSETADDR", (DESTINATION, SOURCE, VALUE), 0x1000),
        ("CINCADDR", (DESTINATION, SOURCE, VALUE), 0),
        ("CSETBOUNDS", (DESTINATION, SOURCE, VALUE), 1),
        ("CANDPERM", (DESTINATION, SOURCE, VALUE), 0xFF),
        ("CSEAL", (DESTINATION, SOURCE, AUTHORITY), None),
        ("CUNSEAL", (DESTINATION, SOURCE, AUTHORITY), None),
    )
    for case in invariant_cases.invalid_capability_cases():
        for mnemonic, operands, value in derivations:
            case_id = f"{INVALID_TAG_DERIVATION_FAMILY}/{case.name}/{mnemonic}"
            cases.append(
                _RunnableCase(
                    INVALID_TAG_DERIVATION_FAMILY,
                    case_id,
                    lambda case=case, mnemonic=mnemonic, operands=operands, value=value: (
                        _run_invalid_source(case, mnemonic, operands, value)
                    ),
                )
            )
    return tuple(cases)


def _run_csetaddr(case: invariant_cases.CapabilityDerivationCase, candidate: int) -> None:
    core = reset.cold_reset_core(0, 0x1000)
    core.write_c(SOURCE, case.parent)
    core.write_d(VALUE, candidate)
    result = _execute_and_commit(core, "CSETADDR", (DESTINATION, SOURCE, VALUE))
    _require(result.is_normal_retire, "CSETADDR did not retire")
    child = core.read_c(DESTINATION)
    _require(child.payload.cursor == candidate, "CSETADDR cursor mismatch")
    _require_not_wider(child, case.parent)


def _run_cincaddr(case: invariant_cases.CapabilityDerivationCase, offset: int) -> None:
    core = reset.cold_reset_core(0, 0x1000)
    core.write_c(SOURCE, case.parent)
    core.write_d(VALUE, invariant_cases.signed_48_cell(offset))
    result = _execute_and_commit(core, "CINCADDR", (DESTINATION, SOURCE, VALUE))
    _require(result.is_normal_retire, "CINCADDR did not retire")
    child = core.read_c(DESTINATION)
    _require(
        child.payload.cursor == case.parent.payload.cursor + offset,
        "CINCADDR cursor mismatch",
    )
    _require_not_wider(child, case.parent)


def _run_csetbounds(case: invariant_cases.CapabilityDerivationCase, length: int) -> None:
    core = reset.cold_reset_core(0, 0x1000)
    core.write_c(SOURCE, case.parent)
    core.write_d(VALUE, length)
    result = _execute_and_commit(core, "CSETBOUNDS", (DESTINATION, SOURCE, VALUE))
    _require(result.is_normal_retire, "CSETBOUNDS did not retire")
    child = core.read_c(DESTINATION)
    _require(child.payload.bounds.base == case.parent.payload.cursor, "bounds base mismatch")
    _require(
        child.payload.bounds.top == case.parent.payload.cursor + length,
        "bounds top mismatch",
    )
    _require_not_wider(child, case.parent)


def _run_candperm(case: invariant_cases.CapabilityDerivationCase, mask: int) -> None:
    core = reset.cold_reset_core(0, 0x1000)
    core.write_c(SOURCE, case.parent)
    core.write_d(VALUE, mask)
    result = _execute_and_commit(core, "CANDPERM", (DESTINATION, SOURCE, VALUE))
    _require(result.is_normal_retire, "CANDPERM did not retire")
    child = core.read_c(DESTINATION)
    _require(
        child.payload.permissions == case.parent.payload.permissions & (mask & 0xFF),
        "CANDPERM permission mismatch",
    )
    _require_not_wider(child, case.parent)


def _run_cseal_cunseal(case: invariant_cases.CapabilityDerivationCase, otype: int) -> None:
    core = reset.cold_reset_core(0, 0x1000)
    seal_authority = invariant_cases.capability(
        otype,
        base=0,
        top=0x1000,
        permissions=int(caps.CapabilityPermission.SEAL),
    )
    unseal_authority = invariant_cases.capability(
        otype,
        base=0,
        top=0x1000,
        permissions=int(caps.CapabilityPermission.UNSEAL),
    )
    core.write_c(SOURCE, case.parent)
    core.write_c(AUTHORITY, seal_authority)
    seal = _execute_and_commit(core, "CSEAL", (DESTINATION, SOURCE, AUTHORITY))
    _require(seal.is_normal_retire, "CSEAL did not retire")
    sealed = core.read_c(DESTINATION)
    _require(sealed.payload.otype == otype, "sealed object type mismatch")
    _require_not_wider(sealed, case.parent, allow_object_type_change=True)

    core.write_c(SOURCE, sealed)
    core.write_c(AUTHORITY, unseal_authority)
    unseal = _execute_and_commit(core, "CUNSEAL", (DESTINATION, SOURCE, AUTHORITY))
    _require(unseal.is_normal_retire, "CUNSEAL did not retire")
    unsealed = core.read_c(DESTINATION)
    _require(unsealed.is_unsealed, "CUNSEAL result remained sealed")
    _require_not_wider(unsealed, sealed, allow_object_type_change=True)
    _require_not_wider(unsealed, case.parent)


def _run_invalid_source(
    case: invariant_cases.InvalidCapabilityCase,
    mnemonic: str,
    operands: tuple[object, ...],
    value: int | None,
) -> None:
    core = reset.cold_reset_core(0, 0x1000)
    sentinel = invariant_cases.capability(0x1000, base=0x1000, top=0x2000)
    core.write_c(DESTINATION, sentinel)
    core.write_c(SOURCE, case.source)
    core.write_c(
        AUTHORITY,
        invariant_cases.capability(
            0x22,
            base=0,
            top=0x1000,
            permissions=int(
                caps.CapabilityPermission.SEAL | caps.CapabilityPermission.UNSEAL
            ),
        ),
    )
    if value is not None:
        core.write_d(VALUE, value)
    result = capability_ops.execute_capability(
        core,
        capability_ops.capability_instruction(mnemonic, operands),
    )
    _require(result.is_fault, f"{mnemonic} unexpectedly retired")
    assert result.fault_packet is not None
    _require(
        result.fault_packet.capcause == instructions.CapCause.TAG,
        f"{mnemonic} did not report tag cause",
    )
    _require(core.read_c(DESTINATION) == sentinel, f"{mnemonic} changed destination")


def _execute_and_commit(core, mnemonic: str, operands: tuple[object, ...]):
    result = capability_ops.execute_capability(
        core,
        capability_ops.capability_instruction(mnemonic, operands),
    )
    if result.is_normal_retire:
        execution.commit_normal_result(core, result)
    return result


def _require_not_wider(
    child: caps.Capability,
    parent: caps.Capability,
    *,
    allow_object_type_change: bool = False,
) -> None:
    _require(child.tag <= parent.tag, "child tag widened")
    parent_bounds = parent.payload.bounds
    child_bounds = child.payload.bounds
    _require(
        parent_bounds.contains_range(child_bounds.base, child_bounds.top),
        "child bounds widened",
    )
    _require(
        child.payload.permissions & ~parent.payload.permissions == 0,
        "child permissions widened",
    )
    _require(child.payload.flags == parent.payload.flags, "child flags changed")
    if not allow_object_type_change:
        _require(child.payload.otype == parent.payload.otype, "child object type changed")


def _signed_hex(value: int) -> str:
    if value < 0:
        return f"-{abs(value):#x}"
    return f"+{value:#x}"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
