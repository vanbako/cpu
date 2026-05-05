"""Executable smoke fixtures for CPU v0.1 program images.

Owner stories:
- I11-S01: program-image manifest boundary.
- I11-S02: serialized cell image loading.
- I11-S03: reset-to-trap smoke execution.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import (
    assembly,
    capabilities as caps,
    control_ops,
    csrs,
    integer,
    memory_ops,
    platform,
    program as decoded_program,
    program_image,
    serialization,
    state,
    traps,
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


SMOKE_HANDLER_CELL = platform.RESET_VECTOR + 0x100
SMOKE_MAIN_SOURCE = (
    "ADD D2, D0, D1",
    "ST48 C0, D3, D2",
    "LD48 D4, C0, D3",
    "SYS",
    "PAUSE",
)
SMOKE_HANDLER_SOURCE = (
    "EPCCRD C1, D5",
    "CPY D5, D7",
    "EPCCWR C1, D5",
    "IRET",
)


class SmokeProgramError(RuntimeError):
    """Raised when the reset-to-trap smoke fixture cannot complete."""


@dataclass(frozen=True)
class ResetToTrapSmokeReport:
    image_load: program_image.ProgramImageLoadReport
    steps: int
    syscall_cause: ExceptionCause
    trap_entered: bool
    pcc_after_iret_address: int
    pcc_after_iret_slot: int
    final_pcc_address: int
    final_pcc_slot: int
    stored_value: int
    loaded_value: int
    instret: int


def reset_to_trap_smoke_manifest() -> program_image.ProgramImageManifest:
    """Return the serialized program-image manifest for the smoke fixture."""
    main_cells = assembly.assemble_program(SMOKE_MAIN_SOURCE)
    handler_cells = assembly.assemble_program(SMOKE_HANDLER_SOURCE)
    return program_image.ProgramImageManifest(
        name="reset_to_trap_smoke",
        entry_cell=platform.RESET_VECTOR,
        entry_source=program_image.EntryCapabilitySource.RESET_PCC,
        sections=(
            program_image.ProgramImageSection.from_serialized_cells(
                name="text",
                region_name="boot_rom",
                base_cell=platform.RESET_VECTOR,
                alignment_cells=2,
                payload_octets=serialization.serialize_cells(main_cells),
                kind=program_image.ProgramImageSectionKind.TEXT,
            ),
            program_image.ProgramImageSection.from_serialized_cells(
                name="trap_handler",
                region_name="boot_rom",
                base_cell=SMOKE_HANDLER_CELL,
                alignment_cells=2,
                payload_octets=serialization.serialize_cells(handler_cells),
                kind=program_image.ProgramImageSectionKind.TEXT,
            ),
        ),
    )


def reset_to_trap_smoke_decoded_program() -> decoded_program.DecodedProgram:
    """Return decoded instructions matching `reset_to_trap_smoke_manifest`."""
    reset = platform.RESET_VECTOR
    handler = SMOKE_HANDLER_CELL
    return decoded_program.DecodedProgram.from_layout(
        (
            (reset, state.SLOT_0, integer.integer_instruction("ADD", (2, 0, 1))),
            (reset + 1, state.SLOT_0, memory_ops.memory_instruction("ST48", (0, 3, 2))),
            (reset + 2, state.SLOT_0, memory_ops.memory_instruction("LD48", (4, 0, 3))),
            (reset + 3, state.SLOT_0, DecodedInstruction("SYS", InstructionSize.BITS_12)),
            (reset + 3, state.SLOT_1, DecodedInstruction("PAUSE", InstructionSize.BITS_12)),
            (handler, state.SLOT_0, control_ops.control_instruction("EPCCRD", (1, 5))),
            (handler + 1, state.SLOT_0, integer.integer_instruction("CPY", (5, 7))),
            (handler + 2, state.SLOT_0, control_ops.control_instruction("EPCCWR", (1, 5))),
            (handler + 3, state.SLOT_0, control_ops.control_instruction("IRET")),
        )
    )


def run_reset_to_trap_smoke_program() -> ResetToTrapSmokeReport:
    """Load and execute the serialized reset-to-trap smoke fixture."""
    memory = TaggedMemory()
    manifest = reset_to_trap_smoke_manifest()
    load_report = program_image.load_program_image(manifest, memory)
    core = platform.cold_reset_cores()[0]
    decoded = reset_to_trap_smoke_decoded_program()
    _install_smoke_authority(core)

    steps = 0
    executor = lambda core, instruction: _execute_smoke_instruction(core, memory, instruction)

    for expected in ("ADD", "ST48", "LD48"):
        result = decoded.step(core, executor, memory=memory)
        _require_normal(result, expected)
        steps += 1

    syscall = decoded.step(core, executor, memory=memory)
    if not syscall.is_fault or syscall.fault_packet.cause is not ExceptionCause.SYSCALL_TRAP:
        raise SmokeProgramError("smoke program did not raise the expected SYS trap")
    trap_result = traps.enter_trap_from_result(core, syscall)
    if not trap_result.entered:
        raise SmokeProgramError("smoke SYS trap could not enter TVC")

    for expected in ("EPCCRD", "CPY", "EPCCWR", "IRET"):
        result = decoded.step(core, executor, memory=memory)
        _require_normal(result, expected)
        steps += 1

    pcc_after_iret = core.pcc
    pause = decoded.step(core, executor, memory=memory)
    _require_normal(pause, "PAUSE")
    steps += 1

    return ResetToTrapSmokeReport(
        image_load=load_report,
        steps=steps,
        syscall_cause=syscall.fault_packet.cause,
        trap_entered=trap_result.entered,
        pcc_after_iret_address=pcc_after_iret.payload.cursor,
        pcc_after_iret_slot=pcc_after_iret.slot,
        final_pcc_address=core.pcc.payload.cursor,
        final_pcc_slot=core.pcc.slot,
        stored_value=memory.ld48(platform.RAM_BASE),
        loaded_value=core.read_d(4),
        instret=core.read_csr(csrs.CSR_INSTRET),
    )


def _execute_smoke_instruction(
    core: state.CoreState,
    memory: TaggedMemory,
    instruction: DecodedInstruction,
) -> ExecutionResult:
    if instruction.mnemonic in integer.MANDATORY_INTEGER_MNEMONICS:
        return integer.execute_integer(core, instruction)
    if instruction.mnemonic in memory_ops.MEMORY_MNEMONICS:
        return memory_ops.execute_memory(core, memory, instruction)
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


def _install_smoke_authority(core: state.CoreState) -> None:
    ram = platform.TEST_PLATFORM_PROFILE.region_by_name("main_ram")
    rom = platform.TEST_PLATFORM_PROFILE.region_by_name("boot_rom")
    data_payload = caps.CapabilityPayload(
        cursor=platform.RAM_BASE,
        bounds_metadata=caps.encode_bounds_metadata(ram.base, ram.end),
        permissions=int(caps.CapabilityPermission.LD | caps.CapabilityPermission.ST),
        flags=int(caps.CapabilityFlag.G),
    )
    tvc_payload = caps.CapabilityPayload(
        cursor=SMOKE_HANDLER_CELL,
        bounds_metadata=caps.encode_bounds_metadata(rom.base, rom.end),
        permissions=int(caps.CapabilityPermission.EX),
        flags=int(caps.CapabilityFlag.G),
    )
    core.write_c(0, caps.Capability.valid(data_payload))
    core.write_ccsr(
        state.SPECIAL_NAME_TO_CCSR_INDEX["TVC"],
        caps.Capability.valid(tvc_payload),
    )
    core.write_d(0, 0x10)
    core.write_d(1, 0x20)
    core.write_d(3, 0)
    core.write_d(7, state.SLOT_1)


def _require_normal(result: ExecutionResult, mnemonic: str) -> None:
    if not result.is_normal_retire or result.instruction.mnemonic != mnemonic:
        raise SmokeProgramError(f"expected normal retire for {mnemonic}")

