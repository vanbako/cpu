"""Decoded instruction and execution-result protocol for CPU v0.1.

Owner stories:
- E04-S01: instruction-size and fetch-group placement rules.
- E07-S02: exception cause names and values.
- E07-S03: precise retire result packets.
- E13-S01: trace-stage and pending-packet vocabulary.
- I03-S01: decoded instruction representation and execution-result protocol.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum
from types import MappingProxyType
from typing import Any, Mapping

from .capabilities import require_uint
from .cells import CELL_BITS, FETCH_GROUP_CELLS, is_aligned, require_cell_address
from .state import SLOT_0, SlottedCapability, require_slot


class InstructionSize(IntEnum):
    """Architectural instruction encoding sizes."""

    BITS_12 = 12
    BITS_24 = 24
    BITS_48 = 48

    @property
    def bits(self) -> int:
        return int(self)

    @property
    def cells(self) -> int:
        return 2 if self is InstructionSize.BITS_48 else 1

    def is_legal_start(self, address: int, slot: int) -> bool:
        address = require_cell_address(address)
        slot = require_slot(slot)
        if self is InstructionSize.BITS_12:
            return True
        if slot != SLOT_0:
            return False
        if self is InstructionSize.BITS_48:
            return is_aligned(address, FETCH_GROUP_CELLS)
        return True


class PipelineStage(Enum):
    """Named v0.1 pipeline stages from E13-S01."""

    FE0 = "FE0"
    FE1 = "FE1"
    PD = "PD"
    XLT = "XLT"
    ISS = "ISS"
    EX = "EX"
    MEM = "MEM"
    WB = "WB"
    RT = "RT"


class ExceptionCause(IntEnum):
    """Assigned synchronous exception and debug-halt cause values."""

    NONE = 0x0000
    ILLEGAL_INSTRUCTION = 0x0001
    BREAKPOINT = 0x0002
    PRIVILEGE_FAULT = 0x0003
    DIVIDE_BY_ZERO = 0x0004
    ALIGN_FAULT = 0x0005
    ACCESS_FAULT = 0x0006
    PAGE_FAULT = 0x0007
    SYSCALL_TRAP = 0x0008
    CAPABILITY_TAG_FAULT = 0x0009
    CAPABILITY_BOUNDS_FAULT = 0x000A
    CAPABILITY_PERMISSION_FAULT = 0x000B
    CAPABILITY_SEAL_TYPE_FAULT = 0x000C
    CAPABILITY_LOCAL_STORE_FAULT = 0x000D
    DEBUG_HALT = 0x000E
    RESERVED_CSR_FAULT = 0x0020
    ILLEGAL_CSR_READ = 0x0021
    ILLEGAL_CSR_WRITE = 0x0022
    CSR_PRIVILEGE_FAULT = 0x0023
    RESERVED_CCSR_FAULT = 0x0024
    ILLEGAL_CCSR_ACCESS = 0x0025
    CCSR_PRIVILEGE_FAULT = 0x0026
    RETURN_STACK_UNDERFLOW = 0x0030
    RETURN_STACK_OVERFLOW = 0x0031
    RETURN_STACK_PERMISSION_FAULT = 0x0032


class CapCause(IntEnum):
    """Capability-specific reporting values for CAPCAUSE."""

    NONE = 0x0
    TAG = 0x1
    BOUNDS = 0x2
    PERMISSION = 0x3
    SEAL_TYPE = 0x4
    LOCAL_STORE = 0x5


class FaultCapIndex(IntEnum):
    """Capability operand reporting values for FAULTCAPIDX."""

    NONE = 0x00
    UNKNOWN = 0x01
    C0 = 0x10
    C1 = 0x11
    C2 = 0x12
    C3 = 0x13
    C4 = 0x14
    C5 = 0x15
    C6 = 0x16
    C7 = 0x17
    PCC = 0x20
    DDC = 0x21
    DSC = 0x22
    RSC = 0x23
    KSC = 0x24
    KRC = 0x25
    EPCC = 0x26
    TVC = 0x27


class DebugCause(IntEnum):
    """DCAUSE values assigned by E12-S01."""

    NONE = 0x0
    EXTERNAL_HALT = 0x1
    HALTREQ = 0x2
    BRK = 0x3
    ENTRY_FAILURE = 0x4
    HW_BREAKPOINT = 0x5
    WATCHPOINT = 0x6
    SINGLE_STEP = 0x7


class RedirectKind(Enum):
    """Architectural redirect packet classes."""

    FALL_THROUGH = "FALL_THROUGH"
    BRANCH = "BRANCH"
    CALL = "CALL"
    RETURN = "RETURN"
    IRET = "IRET"
    TRAP = "TRAP"
    INTERRUPT = "INTERRUPT"
    DEBUG_MONITOR = "DEBUG_MONITOR"
    RESET = "RESET"


class ExecutionResultKind(Enum):
    """Mutually exclusive retire/debug result classes."""

    NORMAL_RETIRE = "NORMAL_RETIRE"
    FAULT = "FAULT"
    DEBUG_EVENT = "DEBUG_EVENT"
    REDIRECT = "REDIRECT"


@dataclass(frozen=True)
class InstructionLocation:
    """Faulting or retiring architectural instruction location."""

    pcc: SlottedCapability

    def __post_init__(self) -> None:
        if not isinstance(self.pcc, SlottedCapability):
            raise TypeError("pcc must be a SlottedCapability")

    @property
    def address(self) -> int:
        return self.pcc.payload.cursor

    @property
    def slot(self) -> int:
        return self.pcc.slot


@dataclass(frozen=True)
class ArchitecturalEffects:
    """Normal effects prepared for an atomic retire commit."""

    integer_writes: tuple[tuple[int, int], ...] = ()
    capability_writes: tuple[tuple[int, object], ...] = ()
    csr_writes: tuple[tuple[int, int], ...] = ()
    ccsr_writes: tuple[tuple[int, object], ...] = ()
    memory_effects: tuple[object, ...] = ()
    tlb_effects: tuple[object, ...] = ()
    reservation_effects: tuple[object, ...] = ()
    pcc_update: SlottedCapability | None = None
    epcc_update: SlottedCapability | None = None

    @property
    def is_empty(self) -> bool:
        return (
            not self.integer_writes
            and not self.capability_writes
            and not self.csr_writes
            and not self.ccsr_writes
            and not self.memory_effects
            and not self.tlb_effects
            and not self.reservation_effects
            and self.pcc_update is None
            and self.epcc_update is None
        )


@dataclass(frozen=True)
class NormalRetirePacket:
    """A normal-retire packet containing all atomic architectural effects."""

    effects: ArchitecturalEffects = field(default_factory=ArchitecturalEffects)

    def __post_init__(self) -> None:
        if not isinstance(self.effects, ArchitecturalEffects):
            raise TypeError("effects must be ArchitecturalEffects")


@dataclass(frozen=True)
class FaultPacket:
    """A precise exception packet carried with an instruction until RT."""

    cause: ExceptionCause
    faulting_location: InstructionLocation
    tval: int = 0
    capcause: CapCause = CapCause.NONE
    fault_cap_idx: FaultCapIndex = FaultCapIndex.NONE

    def __post_init__(self) -> None:
        object.__setattr__(self, "cause", ExceptionCause(self.cause))
        if not isinstance(self.faulting_location, InstructionLocation):
            raise TypeError("faulting_location must be InstructionLocation")
        object.__setattr__(self, "tval", require_uint(self.tval, CELL_BITS * 2, "tval"))
        object.__setattr__(self, "capcause", CapCause(self.capcause))
        object.__setattr__(self, "fault_cap_idx", FaultCapIndex(self.fault_cap_idx))


@dataclass(frozen=True)
class DebugEventPacket:
    """A precise debug-event packet."""

    dcause: DebugCause
    location: InstructionLocation
    tval: int = 0
    monitor_requested: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "dcause", DebugCause(self.dcause))
        if not isinstance(self.location, InstructionLocation):
            raise TypeError("location must be InstructionLocation")
        object.__setattr__(self, "tval", require_uint(self.tval, CELL_BITS * 2, "tval"))
        if type(self.monitor_requested) is not bool:
            raise TypeError("monitor_requested must be a bool")

    @property
    def cause(self) -> ExceptionCause:
        return ExceptionCause.DEBUG_HALT

    @property
    def capcause(self) -> CapCause:
        return CapCause.NONE

    @property
    def fault_cap_idx(self) -> FaultCapIndex:
        return FaultCapIndex.NONE


@dataclass(frozen=True)
class RedirectPacket:
    """A control-flow redirect selected at precise retire."""

    kind: RedirectKind
    target: SlottedCapability
    flush_younger: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", RedirectKind(self.kind))
        if not isinstance(self.target, SlottedCapability):
            raise TypeError("target must be a SlottedCapability")
        if type(self.flush_younger) is not bool:
            raise TypeError("flush_younger must be a bool")


@dataclass(frozen=True)
class DecodedInstruction:
    """Internal decoded-instruction representation."""

    mnemonic: str
    size: InstructionSize
    operands: tuple[Any, ...] = ()
    location: InstructionLocation | None = None
    attributes: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.mnemonic, str):
            raise TypeError("mnemonic must be a str")
        normalized = self.mnemonic.upper()
        if not normalized:
            raise ValueError("mnemonic must not be empty")
        object.__setattr__(self, "mnemonic", normalized)
        object.__setattr__(self, "size", InstructionSize(self.size))
        object.__setattr__(self, "operands", tuple(self.operands))
        if self.location is not None and not isinstance(self.location, InstructionLocation):
            raise TypeError("location must be InstructionLocation or None")
        object.__setattr__(self, "attributes", MappingProxyType(dict(self.attributes)))

    @property
    def length_cells(self) -> int:
        return self.size.cells

    def placement_is_legal(self) -> bool:
        if self.location is None:
            raise ValueError("instruction has no location")
        return self.size.is_legal_start(self.location.address, self.location.slot)

    def placement_fault(self) -> FaultPacket | None:
        if self.placement_is_legal():
            return None
        assert self.location is not None
        return FaultPacket(
            cause=ExceptionCause.ALIGN_FAULT,
            faulting_location=self.location,
            tval=self.location.address,
        )

    def normal_retire(
        self,
        effects: ArchitecturalEffects | None = None,
    ) -> "ExecutionResult":
        return ExecutionResult.normal_retire(self, effects)

    def fault(self, packet: FaultPacket) -> "ExecutionResult":
        return ExecutionResult.fault(self, packet)

    def debug_event(self, packet: DebugEventPacket) -> "ExecutionResult":
        return ExecutionResult.debug_event(self, packet)

    def redirect(self, packet: RedirectPacket) -> "ExecutionResult":
        return ExecutionResult.redirect(self, packet)


@dataclass(frozen=True)
class ExecutionResult:
    """Mutually exclusive instruction outcome packet."""

    instruction: DecodedInstruction
    kind: ExecutionResultKind
    normal: NormalRetirePacket | None = None
    fault_packet: FaultPacket | None = None
    debug_packet: DebugEventPacket | None = None
    redirect_packet: RedirectPacket | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.instruction, DecodedInstruction):
            raise TypeError("instruction must be a DecodedInstruction")
        object.__setattr__(self, "kind", ExecutionResultKind(self.kind))
        packets = (
            self.normal,
            self.fault_packet,
            self.debug_packet,
            self.redirect_packet,
        )
        if sum(packet is not None for packet in packets) != 1:
            raise ValueError("exactly one result packet must be present")
        expected_type = {
            ExecutionResultKind.NORMAL_RETIRE: NormalRetirePacket,
            ExecutionResultKind.FAULT: FaultPacket,
            ExecutionResultKind.DEBUG_EVENT: DebugEventPacket,
            ExecutionResultKind.REDIRECT: RedirectPacket,
        }[self.kind]
        selected_packet = {
            ExecutionResultKind.NORMAL_RETIRE: self.normal,
            ExecutionResultKind.FAULT: self.fault_packet,
            ExecutionResultKind.DEBUG_EVENT: self.debug_packet,
            ExecutionResultKind.REDIRECT: self.redirect_packet,
        }[self.kind]
        if not isinstance(selected_packet, expected_type):
            raise TypeError(f"{self.kind.value} requires {expected_type.__name__}")

    @classmethod
    def normal_retire(
        cls,
        instruction: DecodedInstruction,
        effects: ArchitecturalEffects | None = None,
    ) -> "ExecutionResult":
        if effects is None:
            effects = ArchitecturalEffects()
        return cls(
            instruction=instruction,
            kind=ExecutionResultKind.NORMAL_RETIRE,
            normal=NormalRetirePacket(effects),
        )

    @classmethod
    def fault(
        cls,
        instruction: DecodedInstruction,
        packet: FaultPacket,
    ) -> "ExecutionResult":
        return cls(
            instruction=instruction,
            kind=ExecutionResultKind.FAULT,
            fault_packet=packet,
        )

    @classmethod
    def debug_event(
        cls,
        instruction: DecodedInstruction,
        packet: DebugEventPacket,
    ) -> "ExecutionResult":
        return cls(
            instruction=instruction,
            kind=ExecutionResultKind.DEBUG_EVENT,
            debug_packet=packet,
        )

    @classmethod
    def redirect(
        cls,
        instruction: DecodedInstruction,
        packet: RedirectPacket,
    ) -> "ExecutionResult":
        return cls(
            instruction=instruction,
            kind=ExecutionResultKind.REDIRECT,
            redirect_packet=packet,
        )

    @property
    def is_normal_retire(self) -> bool:
        return self.kind is ExecutionResultKind.NORMAL_RETIRE

    @property
    def is_fault(self) -> bool:
        return self.kind is ExecutionResultKind.FAULT

    @property
    def is_debug_event(self) -> bool:
        return self.kind is ExecutionResultKind.DEBUG_EVENT

    @property
    def is_redirect(self) -> bool:
        return self.kind is ExecutionResultKind.REDIRECT


@dataclass(frozen=True)
class InFlightInstruction:
    """Traceable in-order instruction state for later pipeline tests."""

    sequence: int
    instruction: DecodedInstruction
    stage: PipelineStage = PipelineStage.XLT
    pending_result: ExecutionResult | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "sequence", require_uint(self.sequence, 64, "sequence"))
        if not isinstance(self.instruction, DecodedInstruction):
            raise TypeError("instruction must be a DecodedInstruction")
        object.__setattr__(self, "stage", PipelineStage(self.stage))
        if self.pending_result is not None and not isinstance(
            self.pending_result,
            ExecutionResult,
        ):
            raise TypeError("pending_result must be ExecutionResult or None")

    def advance_to(self, stage: PipelineStage) -> "InFlightInstruction":
        return InFlightInstruction(
            sequence=self.sequence,
            instruction=self.instruction,
            stage=stage,
            pending_result=self.pending_result,
        )

    def with_result(self, result: ExecutionResult) -> "InFlightInstruction":
        if not isinstance(result, ExecutionResult):
            raise TypeError("result must be an ExecutionResult")
        if result.instruction != self.instruction:
            raise ValueError("pending result must belong to this instruction")
        return InFlightInstruction(
            sequence=self.sequence,
            instruction=self.instruction,
            stage=self.stage,
            pending_result=result,
        )
