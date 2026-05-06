"""User/kernel syscall round-trip fixtures for CPU v0.1.

Owner stories:
- E04-S04: `SYS` trap and `IRET` return sequencing.
- E05-S01/E05-S02: syscall integer and capability argument windows.
- E07-S06: software trap frames and slot-aware return.
- I09-S03: syscall ABI supplement.
- I14-S02: minimal syscall handler fixture.
- I18-S01/I18-S02: user entry context and VM mappings.
- I18-S03: syscall demo across the user/kernel boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import IntEnum

from . import (
    abi,
    capabilities as caps,
    csrs,
    firmware,
    kernel,
    memory_ops,
    platform,
    program,
    state,
    traps,
    user_process,
    vm,
)
from .cells import INTEGER_OBJECT_CELLS
from .instructions import ExecutionResult, FaultPacket, InstructionSize
from .memory import TaggedMemory


SYSCALL_DEMO_SERVICE = 0x18_03
SYSCALL_DEMO_ARG0 = 7
SYSCALL_DEMO_ARG1 = 11
SYSCALL_DEMO_USER_VALUE = 0x18_0300
SYSCALL_DEMO_MAX_ARGUMENT = 0xFFFF

SYSCALL_POINTER_REGISTER = 0
SYSCALL_TEMP_DEST_REGISTER = 11
SYSCALL_TEMP_OFFSET_REGISTER = 12


class SyscallDemoStatus(IntEnum):
    OK = 0
    BAD_SERVICE = 1
    BAD_ARGUMENT = 2
    BAD_USER_POINTER = 3


@dataclass(frozen=True)
class SyscallDemoFixture:
    core: state.CoreState
    memory: TaggedMemory
    context: user_process.UserEntryContext
    tables: vm.VmPageTables
    mapping: vm.VmMapping
    user_pointer: caps.Capability

    def __post_init__(self) -> None:
        if not isinstance(self.core, state.CoreState):
            raise TypeError("core must be a CoreState")
        if not isinstance(self.memory, TaggedMemory):
            raise TypeError("memory must be a TaggedMemory")
        if not isinstance(self.context, user_process.UserEntryContext):
            raise TypeError("context must be a UserEntryContext")
        if not isinstance(self.tables, vm.VmPageTables):
            raise TypeError("tables must be VmPageTables")
        if not isinstance(self.mapping, vm.VmMapping):
            raise TypeError("mapping must be VmMapping")
        if not isinstance(self.user_pointer, caps.Capability):
            raise TypeError("user_pointer must be a Capability")


@dataclass(frozen=True)
class UserPointerLoad:
    result: ExecutionResult
    value: int | None

    def __post_init__(self) -> None:
        if not isinstance(self.result, ExecutionResult):
            raise TypeError("result must be an ExecutionResult")
        if self.value is not None:
            object.__setattr__(
                self,
                "value",
                csrs.require_uint(self.value, csrs.CSR_BITS, "value"),
            )

    @property
    def accepted(self) -> bool:
        return self.result.is_normal_retire


@dataclass(frozen=True)
class SyscallDemoReport:
    trap_entry: traps.TrapEntryResult
    saved_frame: kernel.SoftwareTrapFrame
    return_frame: kernel.SoftwareTrapFrame
    service_number: int
    integer_arguments: tuple[int, int]
    status: SyscallDemoStatus
    pointer_load: UserPointerLoad | None
    pointer_fault: FaultPacket | None
    loaded_user_value: int | None
    return_d0: int
    return_d1: int
    return_c0: caps.Capability
    final_pcc: state.SlottedCapability
    final_sr: int
    iret_result: ExecutionResult

    def __post_init__(self) -> None:
        if not isinstance(self.trap_entry, traps.TrapEntryResult):
            raise TypeError("trap_entry must be a TrapEntryResult")
        if not isinstance(self.saved_frame, kernel.SoftwareTrapFrame):
            raise TypeError("saved_frame must be a SoftwareTrapFrame")
        if not isinstance(self.return_frame, kernel.SoftwareTrapFrame):
            raise TypeError("return_frame must be a SoftwareTrapFrame")
        object.__setattr__(
            self,
            "service_number",
            csrs.require_uint(self.service_number, csrs.CSR_BITS, "service_number"),
        )
        if len(self.integer_arguments) != 2:
            raise ValueError("integer_arguments must contain D1 and D2")
        object.__setattr__(
            self,
            "integer_arguments",
            tuple(
                csrs.require_uint(value, csrs.CSR_BITS, f"integer_arguments[{index}]")
                for index, value in enumerate(self.integer_arguments)
            ),
        )
        object.__setattr__(self, "status", SyscallDemoStatus(self.status))
        if self.pointer_load is not None and not isinstance(self.pointer_load, UserPointerLoad):
            raise TypeError("pointer_load must be UserPointerLoad or None")
        if self.pointer_fault is not None and not isinstance(self.pointer_fault, FaultPacket):
            raise TypeError("pointer_fault must be FaultPacket or None")
        if self.loaded_user_value is not None:
            object.__setattr__(
                self,
                "loaded_user_value",
                csrs.require_uint(
                    self.loaded_user_value,
                    csrs.CSR_BITS,
                    "loaded_user_value",
                ),
            )
        object.__setattr__(
            self,
            "return_d0",
            csrs.require_uint(self.return_d0, csrs.CSR_BITS, "return_d0"),
        )
        object.__setattr__(
            self,
            "return_d1",
            csrs.require_uint(self.return_d1, csrs.CSR_BITS, "return_d1"),
        )
        if not isinstance(self.return_c0, caps.Capability):
            raise TypeError("return_c0 must be a Capability")
        if not isinstance(self.final_pcc, state.SlottedCapability):
            raise TypeError("final_pcc must be a SlottedCapability")
        object.__setattr__(
            self,
            "final_sr",
            csrs.require_uint(self.final_sr, csrs.CSR_BITS, "final_sr"),
        )
        if not isinstance(self.iret_result, ExecutionResult):
            raise TypeError("iret_result must be an ExecutionResult")

    @property
    def accepted(self) -> bool:
        return self.status is SyscallDemoStatus.OK

    @property
    def final_user_mode(self) -> bool:
        return not bool(self.final_sr & (1 << csrs.SR_PRIV_BIT))


def prepare_syscall_demo_fixture(
    *,
    service_number: int = SYSCALL_DEMO_SERVICE,
    arg0: int = SYSCALL_DEMO_ARG0,
    arg1: int = SYSCALL_DEMO_ARG1,
    user_pointer: caps.Capability | None = None,
    mapping: vm.VmMapping | None = None,
    tables: vm.VmPageTables | None = None,
) -> SyscallDemoFixture:
    """Build a user process ready to execute the syscall demo service."""
    if tables is None:
        tables = vm.VmPageTables()
    if not isinstance(tables, vm.VmPageTables):
        raise TypeError("tables must be VmPageTables")
    if mapping is None:
        mapping = vm.VmMapping()
    if not isinstance(mapping, vm.VmMapping):
        raise TypeError("mapping must be VmMapping")
    if user_pointer is None:
        user_pointer = vm.virtual_authority(
            mapping.virtual_address(),
            permissions=caps.CapabilityPermission.LD,
        )
    if not isinstance(user_pointer, caps.Capability):
        raise TypeError("user_pointer must be a Capability")

    core = platform.cold_reset_cores()[0]
    memory = TaggedMemory()
    _install_demo_tvc(core)
    context = replace(
        vm.default_vm_entry_context(tables),
        integer_arguments=(service_number, arg0, arg1),
        capability_arguments=(user_pointer,),
    )

    vm.install_user_process_identity_mappings(memory, tables)
    vm.install_page_mapping(memory, mapping, tables)
    user_process.load_user_process_image(context, memory)
    memory.st48(mapping.physical_address(), SYSCALL_DEMO_USER_VALUE)
    user_process.enter_user_process_context(core, context, memory)
    return SyscallDemoFixture(core, memory, context, tables, mapping, user_pointer)


def run_syscall_demo(
    fixture: SyscallDemoFixture | None = None,
    *,
    syscall_size: InstructionSize = InstructionSize.BITS_12,
) -> SyscallDemoReport:
    """Run the user `SYS` trap, minimal handler, and `IRET` return path."""
    if fixture is None:
        fixture = prepare_syscall_demo_fixture()
    if not isinstance(fixture, SyscallDemoFixture):
        raise TypeError("fixture must be a SyscallDemoFixture")
    core = fixture.core
    memory = fixture.memory

    trap_entry = kernel.enter_syscall_from_current_pcc(core, size=syscall_size)
    if not trap_entry.entered:
        raise RuntimeError("SYS trap did not enter TVC")
    saved_frame = kernel.save_trap_frame(core)
    service_number = core.read_d(abi.SYSCALL_SERVICE_REGISTER)
    integer_arguments = (core.read_d(1), core.read_d(2))

    status = SyscallDemoStatus.OK
    return_d1 = 0
    return_c0 = caps.Capability.invalid()
    pointer_load: UserPointerLoad | None = None
    pointer_fault: FaultPacket | None = None
    loaded_user_value: int | None = None

    if service_number != SYSCALL_DEMO_SERVICE:
        status = SyscallDemoStatus.BAD_SERVICE
        return_d1 = service_number
    elif max(integer_arguments) > SYSCALL_DEMO_MAX_ARGUMENT:
        status = SyscallDemoStatus.BAD_ARGUMENT
        return_d1 = max(integer_arguments)
    else:
        pointer_load = load_user_word(core, memory, SYSCALL_POINTER_REGISTER)
        if not pointer_load.accepted:
            status = SyscallDemoStatus.BAD_USER_POINTER
            assert pointer_load.result.fault_packet is not None
            pointer_fault = pointer_load.result.fault_packet
            return_d1 = int(pointer_fault.cause)
        else:
            assert pointer_load.value is not None
            loaded_user_value = pointer_load.value
            return_d1 = sum((*integer_arguments, loaded_user_value)) & csrs.CSR_MASK
            return_c0 = core.read_c(SYSCALL_POINTER_REGISTER).with_cursor(
                core.read_c(SYSCALL_POINTER_REGISTER).payload.cursor
                + INTEGER_OBJECT_CELLS
            )

    core.write_d(0, int(status))
    core.write_d(1, return_d1)
    core.write_c(0, return_c0)
    return_frame = replace(
        saved_frame,
        epcc=program.sequential_pcc(saved_frame.epcc, syscall_size),
    )
    kernel.restore_frame_for_iret(core, return_frame)
    iret_result = kernel.execute_iret(core)
    return SyscallDemoReport(
        trap_entry=trap_entry,
        saved_frame=saved_frame,
        return_frame=return_frame,
        service_number=service_number,
        integer_arguments=integer_arguments,
        status=status,
        pointer_load=pointer_load,
        pointer_fault=pointer_fault,
        loaded_user_value=loaded_user_value,
        return_d0=core.read_d(0),
        return_d1=core.read_d(1),
        return_c0=core.read_c(0),
        final_pcc=core.pcc,
        final_sr=core.read_csr(csrs.CSR_SR),
        iret_result=iret_result,
    )


def load_user_word(
    core: state.CoreState,
    memory: TaggedMemory,
    pointer_register: int = SYSCALL_POINTER_REGISTER,
) -> UserPointerLoad:
    """Validate and read a user `LD48` pointer through the existing memory path."""
    if not isinstance(core, state.CoreState):
        raise TypeError("core must be a CoreState")
    if not isinstance(memory, TaggedMemory):
        raise TypeError("memory must be a TaggedMemory")
    old_offset = core.read_d(SYSCALL_TEMP_OFFSET_REGISTER)
    core.write_d(SYSCALL_TEMP_OFFSET_REGISTER, 0)
    try:
        result = memory_ops.execute_memory(
            core,
            memory,
            memory_ops.memory_instruction(
                "LD48",
                (
                    SYSCALL_TEMP_DEST_REGISTER,
                    pointer_register,
                    SYSCALL_TEMP_OFFSET_REGISTER,
                ),
            ),
        )
    finally:
        core.write_d(SYSCALL_TEMP_OFFSET_REGISTER, old_offset)
    if result.is_fault:
        return UserPointerLoad(result, None)
    assert result.normal is not None
    values = {
        index: value
        for index, value in result.normal.effects.integer_writes
    }
    return UserPointerLoad(result, values[SYSCALL_TEMP_DEST_REGISTER])


def _install_demo_tvc(core: state.CoreState) -> None:
    rom = platform.TEST_PLATFORM_PROFILE.reset_rom_region
    payload = caps.CapabilityPayload(
        cursor=firmware.ROM_TRAP_VECTOR_CELL,
        permissions=int(caps.CapabilityPermission.EX),
        flags=int(caps.CapabilityFlag.G),
    ).with_bounds(rom.base, rom.end)
    core.write_ccsr(
        state.SPECIAL_NAME_TO_CCSR_INDEX["TVC"],
        caps.Capability.valid(payload),
    )
