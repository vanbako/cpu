"""Minimal timer-driven scheduler fixtures for CPU v0.1.

Owner stories:
- E05-S01/E05-S02: integer and capability context-switch save sets.
- E07-S05: timer interrupt delivery.
- E07-S06: trap-frame restore and `IRET`.
- E08-S02: LL/SC reservation clear on context switch.
- E09-S02: SATP and ASID task context.
- I18-S01/I18-S02/I18-S03: user entry, VM, and syscall fixtures.
- I18-S04: minimal scheduler and context-switch fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import (
    abi,
    capabilities as caps,
    csrs,
    firmware,
    kernel,
    platform,
    state,
    user_process,
    vm,
)
from .instructions import ExecutionResult
from .memory import TaggedMemory
from .mmu import MEMORY_TYPE_NORMAL_COHERENT


TASK0_ID = 0
TASK1_ID = 1
TASK0_ASID = 0x31
TASK1_ASID = 0x32
TASK_REGISTER_BASE = 0x18_0400
TASK_TIMER_NOW = 100
TASK_TIMER_DEADLINE = 100
TASK1_TABLES = vm.VmPageTables(
    root=platform.RAM_BASE + 0x5000,
    l1=platform.RAM_BASE + 0x5800,
    l2=platform.RAM_BASE + 0x6000,
    l3=platform.RAM_BASE + 0x6800,
)


@dataclass(frozen=True)
class TaskContext:
    task_id: int
    integer_registers: tuple[int, ...]
    capability_registers: tuple[caps.Capability, ...]
    pcc: state.SlottedCapability
    trap_frame: kernel.SoftwareTrapFrame
    dsc: caps.Capability
    rsc: caps.Capability
    ddc: caps.Capability
    tvc: caps.Capability
    ksc: caps.Capability
    krc: caps.Capability
    satp: int
    asid: int

    def __post_init__(self) -> None:
        if type(self.task_id) is not int:
            raise TypeError("task_id must be an int")
        if self.task_id < 0:
            raise ValueError("task_id must be nonnegative")
        if len(self.integer_registers) != state.INTEGER_REGISTER_COUNT:
            raise ValueError("integer_registers must cover D0-D15")
        object.__setattr__(
            self,
            "integer_registers",
            tuple(
                csrs.require_uint(value, csrs.CSR_BITS, f"D{index}")
                for index, value in enumerate(self.integer_registers)
            ),
        )
        if len(self.capability_registers) != state.GENERAL_CAPABILITY_REGISTER_COUNT:
            raise ValueError("capability_registers must cover C0-C7")
        for capability in self.capability_registers:
            if not isinstance(capability, caps.Capability):
                raise TypeError("capability_registers must contain Capability values")
        object.__setattr__(self, "capability_registers", tuple(self.capability_registers))
        if not isinstance(self.pcc, state.SlottedCapability):
            raise TypeError("pcc must be a SlottedCapability")
        if not isinstance(self.trap_frame, kernel.SoftwareTrapFrame):
            raise TypeError("trap_frame must be a SoftwareTrapFrame")
        for name in ("dsc", "rsc", "ddc", "tvc", "ksc", "krc"):
            if not isinstance(getattr(self, name), caps.Capability):
                raise TypeError(f"{name} must be a Capability")
        object.__setattr__(self, "satp", csrs.validate_satp_value(self.satp))
        object.__setattr__(self, "asid", csrs.validate_asid_value(self.asid))
        if csrs.satp_asid(self.satp) != self.asid:
            raise ValueError("task ASID must match SATP.ASID")
        if self.trap_frame.epcc != self.pcc:
            raise ValueError("trap_frame EPCC must match saved task PCC")

    @property
    def capability_tags(self) -> tuple[bool, ...]:
        return tuple(capability.is_valid for capability in self.capability_registers)


@dataclass(frozen=True)
class SchedulerFixture:
    memory: TaggedMemory
    running_core: state.CoreState
    task0_context: TaskContext
    task1_context: TaskContext

    def __post_init__(self) -> None:
        if not isinstance(self.memory, TaggedMemory):
            raise TypeError("memory must be a TaggedMemory")
        if not isinstance(self.running_core, state.CoreState):
            raise TypeError("running_core must be a CoreState")
        if not isinstance(self.task0_context, TaskContext):
            raise TypeError("task0_context must be a TaskContext")
        if not isinstance(self.task1_context, TaskContext):
            raise TypeError("task1_context must be a TaskContext")


@dataclass(frozen=True)
class SchedulerSwitchReport:
    timer_entry: kernel.InterruptEntryResult
    saved_frame: kernel.SoftwareTrapFrame
    saved_task0: TaskContext
    restored_task1: TaskContext
    iret_result: ExecutionResult
    switch_from_task: int
    switch_to_task: int
    reservation_valid_before_timer: bool
    reservation_valid_after_timer: bool
    reservation_valid_before_switch: bool
    reservation_valid_after_switch: bool
    final_pcc: state.SlottedCapability
    final_sr: int
    final_satp: int
    final_asid: int
    final_integer_registers: tuple[int, ...]
    final_capability_tags: tuple[bool, ...]

    @property
    def final_user_mode(self) -> bool:
        return not bool(self.final_sr & (1 << csrs.SR_PRIV_BIT))


def prepare_scheduler_fixture() -> SchedulerFixture:
    """Prepare task 0 running on core 0 and task 1 as runnable context."""
    memory = TaggedMemory()
    task1_core = _prepare_user_task_core(
        memory,
        TASK1_ID,
        TASK1_ASID,
        TASK1_TABLES,
    )
    _preempt_with_timer(task1_core)
    task1_frame = kernel.save_trap_frame(task1_core)
    task1_context = capture_task_context(TASK1_ID, task1_core, task1_frame)

    task0_core = _prepare_user_task_core(
        memory,
        TASK0_ID,
        TASK0_ASID,
        vm.VmPageTables(),
    )
    task0_placeholder = capture_running_task_context(TASK0_ID, task0_core)
    return SchedulerFixture(memory, task0_core, task0_placeholder, task1_context)


def run_scheduler_fixture() -> SchedulerSwitchReport:
    """Preempt task 0 with a timer interrupt and switch to task 1 via `IRET`."""
    fixture = prepare_scheduler_fixture()
    core = fixture.running_core
    core.reservation.reserve_word(vm.USER_VM_PHYSICAL_PAGE_A, MEMORY_TYPE_NORMAL_COHERENT)
    reservation_valid_before_timer = core.reservation.valid

    timer_entry = _preempt_with_timer(core)
    reservation_valid_after_timer = core.reservation.valid
    saved_frame = kernel.save_trap_frame(core)
    saved_task0 = capture_task_context(TASK0_ID, core, saved_frame)

    core.reservation.reserve_word(vm.USER_VM_PHYSICAL_PAGE_A, MEMORY_TYPE_NORMAL_COHERENT)
    reservation_valid_before_switch = core.reservation.valid
    iret_result = switch_to_task_for_iret(core, fixture.task1_context)
    reservation_valid_after_switch = core.reservation.valid

    return SchedulerSwitchReport(
        timer_entry=timer_entry,
        saved_frame=saved_frame,
        saved_task0=saved_task0,
        restored_task1=fixture.task1_context,
        iret_result=iret_result,
        switch_from_task=TASK0_ID,
        switch_to_task=TASK1_ID,
        reservation_valid_before_timer=reservation_valid_before_timer,
        reservation_valid_after_timer=reservation_valid_after_timer,
        reservation_valid_before_switch=reservation_valid_before_switch,
        reservation_valid_after_switch=reservation_valid_after_switch,
        final_pcc=core.pcc,
        final_sr=core.read_csr(csrs.CSR_SR),
        final_satp=core.read_csr(csrs.CSR_SATP),
        final_asid=core.read_csr(csrs.CSR_ASID),
        final_integer_registers=core.integer_registers.as_tuple(),
        final_capability_tags=tuple(
            capability.is_valid for capability in core.general_capabilities
        ),
    )


def capture_running_task_context(task_id: int, core: state.CoreState) -> TaskContext:
    """Capture a user task that is not currently inside a trap handler."""
    if not isinstance(core, state.CoreState):
        raise TypeError("core must be a CoreState")
    frame = kernel.SoftwareTrapFrame(
        epcc=core.pcc,
        sr=_trap_sr_for_user_sr(core.read_csr(csrs.CSR_SR)),
        cause=0,
        tval=0,
        capcause=0,
        fault_cap_idx=0,
    )
    return capture_task_context(task_id, core, frame)


def capture_task_context(
    task_id: int,
    core: state.CoreState,
    frame: kernel.SoftwareTrapFrame,
) -> TaskContext:
    """Save all ABI registers, capability tags, trap frame, SATP, and ASID."""
    if not isinstance(core, state.CoreState):
        raise TypeError("core must be a CoreState")
    if not isinstance(frame, kernel.SoftwareTrapFrame):
        raise TypeError("frame must be a SoftwareTrapFrame")
    return TaskContext(
        task_id=task_id,
        integer_registers=core.integer_registers.as_tuple(),
        capability_registers=core.general_capabilities.as_tuple(),
        pcc=frame.epcc,
        trap_frame=frame,
        dsc=core.special_capabilities.read("DSC"),
        rsc=core.special_capabilities.read("RSC"),
        ddc=core.special_capabilities.read("DDC"),
        tvc=core.special_capabilities.read("TVC"),
        ksc=core.special_capabilities.read("KSC"),
        krc=core.special_capabilities.read("KRC"),
        satp=core.read_csr(csrs.CSR_SATP),
        asid=core.read_csr(csrs.CSR_ASID),
    )


def switch_to_task_for_iret(
    core: state.CoreState,
    task: TaskContext,
) -> ExecutionResult:
    """Restore a runnable task context and resume it through `IRET`."""
    if not isinstance(core, state.CoreState):
        raise TypeError("core must be a CoreState")
    if not isinstance(task, TaskContext):
        raise TypeError("task must be a TaskContext")
    for index, value in enumerate(task.integer_registers):
        core.write_d(index, value)
    for index, capability in enumerate(task.capability_registers):
        core.write_c(index, capability)
    _write_special(core, "DSC", task.dsc)
    _write_special(core, "RSC", task.rsc)
    _write_special(core, "DDC", task.ddc)
    _write_special(core, "TVC", task.tvc)
    _write_special(core, "KSC", task.ksc)
    _write_special(core, "KRC", task.krc)
    core.write_csr_raw(csrs.CSR_SATP, task.satp)
    core.write_csr_raw(csrs.CSR_ASID, task.asid)
    kernel.restore_frame_for_iret(core, task.trap_frame)
    core.reservation.clear()
    return kernel.execute_iret(core)


def _prepare_user_task_core(
    memory: TaggedMemory,
    task_id: int,
    asid: int,
    tables: vm.VmPageTables,
) -> state.CoreState:
    core = platform.cold_reset_cores()[0]
    _install_scheduler_tvc(core)
    vm.install_user_process_identity_mappings(memory, tables)
    user_context = vm.default_vm_entry_context(tables, asid=asid)
    user_process.load_user_process_image(user_context, memory)
    user_process.enter_user_process_context(core, user_context, memory)
    _install_task_register_pattern(core, task_id)
    return core


def _install_task_register_pattern(core: state.CoreState, task_id: int) -> None:
    base = TASK_REGISTER_BASE + (task_id << 8)
    for index in abi.CONTEXT_SWITCH_INTEGER_REGS:
        core.write_d(index, base + index)
    for index in abi.CONTEXT_SWITCH_CAPABILITY_REGS:
        if index % 2:
            core.write_c(index, caps.Capability.invalid())
            continue
        core.write_c(
            index,
            vm.virtual_authority(
                vm.USER_VM_ADDRESS + (task_id * 0x20) + index,
                permissions=caps.CapabilityPermission.LD | caps.CapabilityPermission.ST,
            ),
        )


def _preempt_with_timer(core: state.CoreState) -> kernel.InterruptEntryResult:
    core.write_csr_raw(csrs.CSR_TIMER, TASK_TIMER_NOW)
    core.write_csr_raw(csrs.CSR_TIMECMP, TASK_TIMER_DEADLINE)
    core.write_csr_raw(csrs.CSR_IENABLE, 1 << kernel.InterruptSource.TIMER.bit)
    entry = kernel.enter_pending_interrupt(core)
    if not entry.entered:
        raise RuntimeError("timer interrupt did not preempt task")
    return entry


def _install_scheduler_tvc(core: state.CoreState) -> None:
    rom = platform.TEST_PLATFORM_PROFILE.reset_rom_region
    payload = caps.CapabilityPayload(
        cursor=firmware.ROM_TRAP_VECTOR_CELL,
        permissions=int(caps.CapabilityPermission.EX),
        flags=int(caps.CapabilityFlag.G),
    ).with_bounds(rom.base, rom.end)
    _write_special(core, "TVC", caps.Capability.valid(payload))


def _trap_sr_for_user_sr(user_sr: int) -> int:
    value = user_sr
    value = _set_sr_bit(value, csrs.SR_PIE_BIT, _sr_bit(user_sr, csrs.SR_IE_BIT))
    value = _set_sr_bit(value, csrs.SR_IE_BIT, False)
    value = _set_sr_bit(value, csrs.SR_PPRIV_BIT, _sr_bit(user_sr, csrs.SR_PRIV_BIT))
    value = _set_sr_bit(value, csrs.SR_PRIV_BIT, True)
    value = _set_sr_bit(value, csrs.SR_EXL_BIT, True)
    return value


def _set_sr_bit(value: int, bit: int, enabled: bool) -> int:
    mask = 1 << bit
    if enabled:
        return value | mask
    return value & ~mask


def _sr_bit(value: int, bit: int) -> bool:
    return bool(value & (1 << bit))


def _write_special(core: state.CoreState, name: str, capability: caps.Capability) -> None:
    core.write_ccsr(state.SPECIAL_NAME_TO_CCSR_INDEX[name], capability.copy())
