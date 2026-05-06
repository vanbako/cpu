"""Deterministic golden retire trace corpus for first RTL comparison.

Owner stories:
- E07-S03: precise retire result packets.
- E13-S01: pipeline trace and retire vocabulary.
- I20-S02: semantic golden retire trace corpus.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from . import (
    call_ops,
    capability_ops,
    capabilities as caps,
    control_ops,
    csrs,
    integer,
    memory_ops,
    opcodes,
    pipeline,
    program,
    reset,
    return_ops,
    state,
)
from .instructions import (
    DecodedInstruction,
    ExceptionCause,
    ExecutionResult,
    FaultPacket,
    InstructionLocation,
    InstructionSize,
)
from .memory import TaggedMemory


JsonValue = Any

REQUIRED_GOLDEN_TRACE_CATEGORIES = frozenset(
    {
        "reset_smoke",
        "integer_ops",
        "capability_derivation",
        "memory_tag_ops",
        "traps",
        "calls_returns",
        "fault_cases",
    }
)


@dataclass(frozen=True)
class GoldenTraceCase:
    case_id: str
    category: str
    description: str
    packets: tuple[dict[str, JsonValue], ...]
    final_observations: dict[str, JsonValue]

    def __post_init__(self) -> None:
        if not isinstance(self.case_id, str) or not self.case_id:
            raise ValueError("case_id must be a nonempty str")
        if not isinstance(self.category, str) or not self.category:
            raise ValueError("category must be a nonempty str")
        if not isinstance(self.description, str) or not self.description:
            raise ValueError("description must be a nonempty str")
        object.__setattr__(self, "packets", tuple(dict(packet) for packet in self.packets))
        object.__setattr__(self, "final_observations", dict(self.final_observations))

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "case_id": self.case_id,
            "category": self.category,
            "description": self.description,
            "packets": [dict(packet) for packet in self.packets],
            "final_observations": dict(self.final_observations),
        }


def golden_trace_corpus() -> tuple[GoldenTraceCase, ...]:
    """Return the deterministic semantic retire trace corpus."""
    return (
        _reset_smoke_case(),
        _integer_ops_case(),
        _capability_move_getaddr_case(),
        _capability_derivation_case(),
        _memory_tag_ops_case(),
        _trap_case(),
        _trap_iret_case(),
        _call_return_case(),
        _divide_by_zero_fault_case(),
        _invalid_tag_fault_case(),
        _placement_fault_case(),
    )


def golden_trace_corpus_as_dicts() -> tuple[dict[str, JsonValue], ...]:
    return tuple(case.as_dict() for case in golden_trace_corpus())


def golden_trace_corpus_json(*, indent: int = 2) -> str:
    return json.dumps(golden_trace_corpus_as_dicts(), indent=indent, sort_keys=True)


def golden_trace_case_by_id(case_id: str) -> GoldenTraceCase:
    for case in golden_trace_corpus():
        if case.case_id == case_id:
            return case
    raise KeyError(case_id)


def validate_golden_trace_corpus(
    cases: tuple[GoldenTraceCase, ...] | None = None,
) -> tuple[str, ...]:
    if cases is None:
        cases = golden_trace_corpus()

    issues: list[str] = []
    case_ids = [case.case_id for case in cases]
    if len(case_ids) != len(set(case_ids)):
        issues.append("golden trace case IDs are not unique")

    categories = {case.category for case in cases}
    missing_categories = REQUIRED_GOLDEN_TRACE_CATEGORIES - categories
    for category in sorted(missing_categories):
        issues.append(f"missing golden trace category {category}")

    for case in cases:
        if not case.packets:
            issues.append(f"{case.case_id}: no retire packets")
            continue
        for expected_sequence, packet in enumerate(case.packets):
            if packet.get("sequence") != expected_sequence:
                issues.append(f"{case.case_id}: noncontiguous packet sequence")
            if packet.get("valid") is not True:
                issues.append(f"{case.case_id}: retire packet is not valid")
            selected = sum(
                packet.get(name) is not None
                for name in ("normal_effects", "fault_packet", "redirect_packet")
            )
            if selected != 1:
                issues.append(f"{case.case_id}: retire packet does not select exactly one outcome")
            for field in (
                "pc_cell",
                "slot",
                "instruction_length",
                "mnemonic",
                "result_kind",
                "result_stage",
            ):
                if field not in packet:
                    issues.append(f"{case.case_id}: retire packet missing {field}")

    try:
        json.dumps(tuple(case.as_dict() for case in cases), sort_keys=True)
    except TypeError as exc:
        issues.append(f"golden trace corpus is not JSON serializable: {exc}")

    return tuple(issues)


def _reset_smoke_case() -> GoldenTraceCase:
    core = reset.cold_reset_core(0, 0x1000)
    core.write_d(0, 0x10)
    core.write_d(1, 0x20)
    decoded = program.DecodedProgram.from_layout(
        ((0x1000, state.SLOT_0, integer.integer_instruction("ADD", (2, 0, 1))),)
    )
    return _run_case(
        "reset_smoke.add_slot0",
        "reset_smoke",
        "Cold-reset core 0 retires the first slot-0 integer instruction.",
        core,
        decoded,
        steps=1,
        observe_d=(2,),
    )


def _integer_ops_case() -> GoldenTraceCase:
    core = _core_at(0x1100)
    core.write_d(0, 6)
    core.write_d(1, 7)
    core.write_d(3, 5)
    decoded = program.DecodedProgram.from_layout(
        (
            (0x1100, state.SLOT_0, integer.integer_instruction("ADD", (2, 0, 1))),
            (0x1101, state.SLOT_0, integer.integer_instruction("MUL", (4, 2, 3))),
        )
    )
    return _run_case(
        "integer_ops.add_mul",
        "integer_ops",
        "Straight-line integer ADD/MUL retire packets and register writes.",
        core,
        decoded,
        steps=2,
        observe_d=(2, 4),
    )


def _capability_derivation_case() -> GoldenTraceCase:
    core = _core_at(0x1200)
    core.write_c(1, _data_capability(cursor=0x2000))
    core.write_d(0, 0x2080)
    core.write_d(1, int(caps.CapabilityPermission.LD))
    decoded = program.DecodedProgram.from_layout(
        (
            (0x1200, state.SLOT_0, capability_ops.capability_instruction("CSETADDR", (2, 1, 0))),
            (0x1202, state.SLOT_0, capability_ops.capability_instruction("CANDPERM", (3, 2, 1))),
        )
    )
    return _run_case(
        "capability_derivation.csetaddr_candperm",
        "capability_derivation",
        "Capability cursor narrowing and permission masking retire packets.",
        core,
        decoded,
        steps=2,
        observe_c=(2, 3),
    )


def _capability_move_getaddr_case() -> GoldenTraceCase:
    core = _core_at(0x1250)
    core.write_c(1, _data_capability(cursor=0x2200))
    decoded = program.DecodedProgram.from_layout(
        (
            (0x1250, state.SLOT_0, capability_ops.capability_instruction("CMOVE", (2, 1))),
            (0x1252, state.SLOT_0, capability_ops.capability_instruction("CGETADDR", (3, 2))),
        )
    )
    return _run_case(
        "capability_derivation.cmove_cgetaddr",
        "capability_derivation",
        "Capability payload/tag move followed by cursor extraction.",
        core,
        decoded,
        steps=2,
        observe_d=(3,),
        observe_c=(2,),
    )


def _memory_tag_ops_case() -> GoldenTraceCase:
    core = _core_at(0x1300)
    core.write_c(
        1,
        _data_capability(
            cursor=0x2000,
            permissions=int(
                caps.CapabilityPermission.LD
                | caps.CapabilityPermission.ST
                | caps.CapabilityPermission.LC
                | caps.CapabilityPermission.SC
            ),
        ),
    )
    core.write_c(2, _data_capability(cursor=0x2100))
    core.write_d(0, 0)
    core.write_d(4, 0x123456789ABC)
    memory = TaggedMemory()
    decoded = program.DecodedProgram.from_layout(
        (
            (0x1300, state.SLOT_0, memory_ops.memory_instruction("CSC", (1, 0, 2))),
            (0x1301, state.SLOT_0, memory_ops.memory_instruction("CLC", (3, 1, 0))),
            (0x1302, state.SLOT_0, memory_ops.memory_instruction("ST48", (1, 0, 4))),
            (0x1303, state.SLOT_0, memory_ops.memory_instruction("LD48", (5, 1, 0))),
        )
    )
    return _run_case(
        "memory_tag_ops.csc_clc_st48_ld48",
        "memory_tag_ops",
        "Capability store/load followed by integer store tag clear and integer load.",
        core,
        decoded,
        steps=4,
        memory=memory,
        observe_d=(5,),
        observe_c=(3,),
        observe_cells=(0x2000, 0x2001),
        observe_tags=(0x2000,),
    )


def _trap_case() -> GoldenTraceCase:
    core = _core_at(0x1400)
    core.write_ccsr(state.SPECIAL_NAME_TO_CCSR_INDEX["TVC"], _executable_capability(0x9000))
    decoded = program.DecodedProgram.from_layout(
        ((0x1400, state.SLOT_0, DecodedInstruction("SYS", InstructionSize.BITS_12)),)
    )
    return _run_case(
        "traps.sys_to_tvc",
        "traps",
        "Synchronous SYS fault retires precisely and enters TVC.",
        core,
        decoded,
        steps=1,
        enter_traps=True,
        observe_csrs=(csrs.CSR_CAUSE, csrs.CSR_TVAL, csrs.CSR_CAPCAUSE, csrs.CSR_FAULTCAPIDX),
    )


def _trap_iret_case() -> GoldenTraceCase:
    core = _core_at(0x1750)
    core.write_ccsr(state.SPECIAL_NAME_TO_CCSR_INDEX["TVC"], _executable_capability(0x9000))
    decoded = program.DecodedProgram.from_layout(
        (
            (0x1750, state.SLOT_0, DecodedInstruction("SYS", InstructionSize.BITS_12)),
            (0x9000, state.SLOT_0, control_ops.control_instruction("IRET")),
        )
    )
    return _run_case(
        "traps.sys_iret_return",
        "traps",
        "Synchronous SYS trap enters TVC and IRET restores EPCC.",
        core,
        decoded,
        steps=2,
        enter_traps=True,
        observe_csrs=(csrs.CSR_CAUSE, csrs.CSR_SR),
    )


def _call_return_case() -> GoldenTraceCase:
    core = _core_at(0x1500)
    return_stack = _return_stack_capability(cursor=0x3004)
    core.write_ccsr(state.SPECIAL_NAME_TO_CCSR_INDEX["RSC"], return_stack)
    memory = TaggedMemory()
    memory.protect_range(0x3000, 8)
    decoded = program.DecodedProgram.from_layout(
        (
            (0x1500, state.SLOT_0, call_ops.call_instruction("CALL", (0x1510,))),
            (0x1510, state.SLOT_0, return_ops.return_instruction()),
        )
    )
    return _run_case(
        "calls_returns.direct_call_ret",
        "calls_returns",
        "Direct CALL pushes a protected return capability and RET restores it.",
        core,
        decoded,
        steps=2,
        memory=memory,
        observe_tags=(0x3000,),
        observe_ccsrs=("RSC",),
    )


def _divide_by_zero_fault_case() -> GoldenTraceCase:
    core = _core_at(0x1600)
    core.write_d(0, 42)
    core.write_d(1, 0)
    decoded = program.DecodedProgram.from_layout(
        ((0x1600, state.SLOT_0, integer.integer_instruction("DIV", (2, 0, 1))),)
    )
    return _run_case(
        "fault_cases.divide_by_zero",
        "fault_cases",
        "Integer divide by zero produces a precise fault packet with no D2 write.",
        core,
        decoded,
        steps=1,
        observe_d=(2,),
    )


def _invalid_tag_fault_case() -> GoldenTraceCase:
    core = _core_at(0x1650)
    core.write_c(1, _data_capability(cursor=0x2000, tag=False))
    core.write_d(0, 0x2080)
    decoded = program.DecodedProgram.from_layout(
        ((0x1650, state.SLOT_0, capability_ops.capability_instruction("CSETADDR", (2, 1, 0))),)
    )
    return _run_case(
        "fault_cases.invalid_tag_csetaddr",
        "fault_cases",
        "Invalid capability tag faults before CSETADDR writes its destination.",
        core,
        decoded,
        steps=1,
        observe_c=(2,),
    )


def _placement_fault_case() -> GoldenTraceCase:
    core = _core_at(0x1700)
    core.install_pcc(
        state.SlottedCapability.from_capability(_executable_capability(0x1700), state.SLOT_1)
    )
    decoded = program.DecodedProgram.from_layout(
        ((0x1700, state.SLOT_1, capability_ops.capability_instruction("CGETADDR", (0, 1))),)
    )
    return _run_case(
        "fault_cases.slot1_48bit_placement",
        "fault_cases",
        "A 48-bit instruction starting in slot 1 faults before execute.",
        core,
        decoded,
        steps=1,
        observe_d=(0,),
    )


def _run_case(
    case_id: str,
    category: str,
    description: str,
    core: state.CoreState,
    decoded: program.DecodedProgram,
    *,
    steps: int,
    memory: TaggedMemory | None = None,
    enter_traps: bool = False,
    observe_d: tuple[int, ...] = (),
    observe_c: tuple[int, ...] = (),
    observe_csrs: tuple[int, ...] = (),
    observe_ccsrs: tuple[str, ...] = (),
    observe_cells: tuple[int, ...] = (),
    observe_tags: tuple[int, ...] = (),
) -> GoldenTraceCase:
    trace_model = pipeline.SingleIssuePipeline(
        decoded,
        lambda core, instruction: _execute_fixture_instruction(core, memory, instruction),
        memory=memory,
        enter_traps=enter_traps,
    )
    packets = []
    for _ in range(steps):
        trace = trace_model.step(core)
        packets.append(_retire_packet(trace))
    return GoldenTraceCase(
        case_id,
        category,
        description,
        tuple(packets),
        _observations(
            core,
            memory,
            observe_d=observe_d,
            observe_c=observe_c,
            observe_csrs=observe_csrs,
            observe_ccsrs=observe_ccsrs,
            observe_cells=observe_cells,
            observe_tags=observe_tags,
        ),
    )


def _execute_fixture_instruction(
    core: state.CoreState,
    memory: TaggedMemory | None,
    instruction: DecodedInstruction,
) -> ExecutionResult:
    if instruction.mnemonic in integer.MANDATORY_INTEGER_MNEMONICS:
        return integer.execute_integer(core, instruction)
    if instruction.mnemonic in capability_ops.REGISTER_DERIVATION_MNEMONICS:
        return capability_ops.execute_capability(core, instruction)
    if instruction.mnemonic in memory_ops.MEMORY_MNEMONICS:
        assert memory is not None
        return memory_ops.execute_memory(core, memory, instruction)
    if instruction.mnemonic in call_ops.CALL_MNEMONICS:
        assert memory is not None
        return call_ops.execute_call(core, memory, instruction)
    if instruction.mnemonic in return_ops.RET_MNEMONICS:
        assert memory is not None
        return return_ops.execute_return(core, memory, instruction)
    if instruction.mnemonic in control_ops.TRAP_RETURN_MNEMONICS:
        return control_ops.execute_control(core, instruction)
    if instruction.mnemonic == "SYS":
        return instruction.fault(
            FaultPacket(
                ExceptionCause.SYSCALL_TRAP,
                instruction.location or InstructionLocation(core.pcc),
            )
        )
    if instruction.mnemonic == "PAUSE":
        return instruction.normal_retire()
    return instruction.fault(
        FaultPacket(
            ExceptionCause.ILLEGAL_INSTRUCTION,
            instruction.location or InstructionLocation(core.pcc),
        )
    )


def _retire_packet(trace: pipeline.PipelineStepTrace) -> dict[str, JsonValue]:
    result = trace.result
    instruction = result.instruction
    if instruction.location is None:
        raise ValueError("golden retire packets require instruction locations")
    result_stage = next(
        event.stage.value for event in trace.events if event.pending_result_kind is not None
    )
    return {
        "valid": True,
        "sequence": trace.sequence,
        "pc_cell": instruction.location.address,
        "slot": instruction.location.slot,
        "instruction_length": instruction.length_cells,
        "mnemonic": instruction.mnemonic,
        "opcode_id": _opcode_id(instruction.mnemonic),
        "result_kind": result.kind.value,
        "result_stage": result_stage,
        "normal_effects": _normal_effects(result) if result.is_normal_retire else None,
        "fault_packet": _fault_packet(result) if result.is_fault else None,
        "redirect_packet": _redirect_packet(result) if result.is_redirect else None,
        "trap_entry": _trap_entry(trace),
    }


def _opcode_id(mnemonic: str) -> int | None:
    rows = opcodes.all_opcode_forms()
    canonical = opcodes.canonical_mnemonic(mnemonic)
    matching = sorted(row.opcode_id for row in rows if row.mnemonic == canonical)
    return matching[0] if matching else None


def _normal_effects(result: ExecutionResult) -> dict[str, JsonValue]:
    assert result.normal is not None
    effects = result.normal.effects
    return {
        "integer_writes": [
            {"register": f"D{index}", "value": value}
            for index, value in effects.integer_writes
        ],
        "capability_writes": [
            {"register": f"C{index}", "capability": _capability(capability)}
            for index, capability in effects.capability_writes
        ],
        "csr_writes": [
            {"register": _csr_name(number), "number": number, "value": value}
            for number, value in effects.csr_writes
        ],
        "ccsr_writes": [
            {
                "register": _ccsr_name(index),
                "number": index,
                "capability": _capability(capability),
            }
            for index, capability in effects.ccsr_writes
        ],
        "memory_effects": [_memory_effect(effect) for effect in effects.memory_effects],
        "tlb_effects": [_effect_name(effect) for effect in effects.tlb_effects],
        "reservation_effects": [_effect_name(effect) for effect in effects.reservation_effects],
        "pcc_update": _slotted_capability(effects.pcc_update),
        "epcc_update": _slotted_capability(effects.epcc_update),
    }


def _fault_packet(result: ExecutionResult) -> dict[str, JsonValue]:
    assert result.fault_packet is not None
    packet = result.fault_packet
    return {
        "cause": packet.cause.name,
        "cause_value": int(packet.cause),
        "faulting_location": _location(packet.faulting_location),
        "tval": packet.tval,
        "capcause": packet.capcause.name,
        "capcause_value": int(packet.capcause),
        "fault_cap_idx": packet.fault_cap_idx.name,
        "fault_cap_idx_value": int(packet.fault_cap_idx),
    }


def _redirect_packet(result: ExecutionResult) -> dict[str, JsonValue]:
    assert result.redirect_packet is not None
    packet = result.redirect_packet
    return {
        "kind": packet.kind.value,
        "target": _slotted_capability(packet.target),
        "flush_younger": packet.flush_younger,
    }


def _trap_entry(trace: pipeline.PipelineStepTrace) -> dict[str, JsonValue] | None:
    if trace.trap_entry is None:
        return None
    entry = trace.trap_entry
    failure = None
    if entry.failure is not None:
        failure = {
            "capcause": entry.failure.capcause.name,
            "fault_cap_idx": entry.failure.fault_cap_idx.name,
            "tval": entry.failure.tval,
        }
    return {
        "kind": entry.kind.value,
        "entered": entry.entered,
        "fatal": entry.fatal,
        "failure": failure,
    }


def _memory_effect(effect: object) -> dict[str, JsonValue]:
    if isinstance(effect, memory_ops.St48Effect):
        return {
            "kind": "ST48",
            "address": effect.address,
            "value": effect.value,
            "length_cells": effect.length_cells,
        }
    if isinstance(effect, memory_ops.CscEffect):
        return {
            "kind": "CSC",
            "address": effect.address,
            "capability": _capability(effect.capability),
            "length_cells": effect.length_cells,
        }
    if isinstance(effect, call_ops.ReturnStackPushEffect):
        return {
            "kind": "RETURN_STACK_PUSH",
            "address": effect.address,
            "capability": _capability(effect.capability),
            "length_cells": 4,
        }
    return {"kind": _effect_name(effect)}


def _observations(
    core: state.CoreState,
    memory: TaggedMemory | None,
    *,
    observe_d: tuple[int, ...],
    observe_c: tuple[int, ...],
    observe_csrs: tuple[int, ...],
    observe_ccsrs: tuple[str, ...],
    observe_cells: tuple[int, ...],
    observe_tags: tuple[int, ...],
) -> dict[str, JsonValue]:
    observations: dict[str, JsonValue] = {
        "pcc": _slotted_capability(core.pcc),
        "epcc": _slotted_capability(core.epcc),
        "integer_registers": {f"D{index}": core.read_d(index) for index in observe_d},
        "capability_registers": {
            f"C{index}": _capability(core.read_c(index)) for index in observe_c
        },
        "csrs": {
            _csr_name(number): core.read_csr(number) for number in observe_csrs
        },
        "ccsrs": {
            name: _capability(core.special_capabilities.read(name))
            for name in observe_ccsrs
        },
    }
    if memory is not None:
        observations["memory_cells"] = {
            f"{address:#x}": memory.read_cell(address) for address in observe_cells
        }
        observations["memory_tags"] = {
            f"{address:#x}": memory.capability_tag(address) for address in observe_tags
        }
    return observations


def _core_at(reset_vector: int) -> state.CoreState:
    core = reset.cold_reset_core(0, reset_vector)
    core.install_pcc(
        state.SlottedCapability.from_capability(_executable_capability(reset_vector), state.SLOT_0)
    )
    return core


def _executable_capability(cursor: int) -> caps.Capability:
    return _capability_with(
        cursor=cursor,
        base=0,
        top=1 << 48,
        permissions=int(caps.CapabilityPermission.EX),
    )


def _data_capability(
    *,
    cursor: int,
    permissions: int = int(
        caps.CapabilityPermission.LD
        | caps.CapabilityPermission.ST
        | caps.CapabilityPermission.LC
        | caps.CapabilityPermission.SC
    ),
    tag: bool = True,
) -> caps.Capability:
    return _capability_with(
        cursor=cursor,
        base=0x2000,
        top=0x3000,
        permissions=permissions,
        tag=tag,
    )


def _return_stack_capability(cursor: int) -> caps.Capability:
    return _capability_with(
        cursor=cursor,
        base=0x3000,
        top=0x3008,
        permissions=int(
            caps.CapabilityPermission.LD
            | caps.CapabilityPermission.ST
            | caps.CapabilityPermission.LC
            | caps.CapabilityPermission.SC
            | caps.CapabilityPermission.SL
        ),
    )


def _capability_with(
    *,
    cursor: int,
    base: int,
    top: int,
    permissions: int,
    tag: bool = True,
    otype: int = caps.OTYPE_UNSEALED,
    flags: int = int(caps.CapabilityFlag.G),
) -> caps.Capability:
    payload = caps.CapabilityPayload(
        cursor=cursor,
        bounds_metadata=caps.encode_bounds_metadata(base, top),
        permissions=permissions,
        otype=otype,
        flags=flags,
    )
    return caps.Capability(payload, tag)


def _capability(capability: object) -> dict[str, JsonValue]:
    if capability is None:
        raise TypeError("capability cannot be None")
    if not isinstance(capability, caps.Capability):
        raise TypeError("expected Capability")
    return {
        "tag": capability.tag,
        "payload": {
            "cursor": capability.payload.cursor,
            "bounds_metadata": capability.payload.bounds_metadata,
            "permissions": capability.payload.permissions,
            "otype": capability.payload.otype,
            "flags": capability.payload.flags,
        },
        "payload_cells": list(caps.payload_to_cells(capability.payload)),
    }


def _slotted_capability(value: object) -> dict[str, JsonValue] | None:
    if value is None:
        return None
    if not isinstance(value, state.SlottedCapability):
        raise TypeError("expected SlottedCapability")
    serialized = _capability(value.without_slot())
    serialized["slot"] = value.slot
    return serialized


def _location(location: InstructionLocation) -> dict[str, JsonValue]:
    return {
        "pc_cell": location.address,
        "slot": location.slot,
        "pcc": _slotted_capability(location.pcc),
    }


def _csr_name(number: int) -> str:
    return csrs.ASSIGNED_CSR_NUMBER_TO_NAME.get(number, f"CSR_{number:#x}")


def _ccsr_name(index: int) -> str:
    return state.CCSR_INDEX_TO_SPECIAL_NAME.get(index, f"CCSR_{index:#x}")


def _effect_name(effect: object) -> str:
    return type(effect).__name__
