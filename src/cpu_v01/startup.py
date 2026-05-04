"""Secondary-core startup binding for the CPU v0.1 test platform.

Owner stories:
- E11-S03: secondary-core startup.
- I08-S02: platform mailbox and start-event binding.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import MutableMapping, Sequence

from . import csrs, platform
from .capabilities import Capability, CapabilityPermission
from .cells import CAPABILITY_OBJECT_CELLS, is_aligned
from .state import (
    CoreLifecycle,
    CoreState,
    SLOT_0,
    SlottedCapability,
    SPECIAL_NAME_TO_CCSR_INDEX,
)


class MailboxState(Enum):
    EMPTY = "EMPTY"
    READY = "READY"
    CONSUMED = "CONSUMED"
    FAILED = "FAILED"


class StartupFailureCode(Enum):
    NONE = "NONE"
    NOT_READY = "NOT_READY"
    WRONG_CORE = "WRONG_CORE"
    STALE_GENERATION = "STALE_GENERATION"
    INVALID_PCC = "INVALID_PCC"
    INVALID_STACK = "INVALID_STACK"
    INVALID_CAPABILITY = "INVALID_CAPABILITY"
    INVALID_DESCRIPTOR = "INVALID_DESCRIPTOR"
    INVALID_TARGET = "INVALID_TARGET"
    ALREADY_STARTED = "ALREADY_STARTED"


@dataclass
class StartMailbox:
    target_coreid: int
    generation: int = 0
    state: MailboxState = MailboxState.EMPTY
    entry_pcc: SlottedCapability | None = None
    dsc: Capability | None = None
    rsc: Capability | None = None
    ksc: Capability | None = None
    krc: Capability | None = None
    tvc: Capability | None = None
    ddc: Capability | None = None
    arg0: int = 0
    arg_cap0: Capability | None = None
    failure_code: StartupFailureCode = StartupFailureCode.NONE

    def __post_init__(self) -> None:
        if type(self.target_coreid) is not int:
            raise TypeError("target_coreid must be an int")
        if type(self.generation) is not int:
            raise TypeError("generation must be an int")
        if self.generation < 0:
            raise ValueError("generation must be nonnegative")
        self.state = MailboxState(self.state)
        self.arg0 = csrs.require_uint(self.arg0, csrs.CSR_BITS, "arg0")
        self.failure_code = StartupFailureCode(self.failure_code)


@dataclass(frozen=True)
class StartupResult:
    target_coreid: int
    accepted: bool
    failure_code: StartupFailureCode
    mailbox_state: MailboxState
    lifecycle: CoreLifecycle


@dataclass
class SecondaryStartupController:
    profile: platform.TestPlatformProfile = platform.TEST_PLATFORM_PROFILE
    mailboxes: MutableMapping[int, StartMailbox] = field(default_factory=dict)
    consumed_generations: MutableMapping[int, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.profile, platform.TestPlatformProfile):
            raise TypeError("profile must be a TestPlatformProfile")
        if not self.mailboxes:
            self.mailboxes.update(
                {
                    core_id: StartMailbox(core_id)
                    for core_id in range(1, self.profile.core_count)
                }
            )
        if not self.consumed_generations:
            self.consumed_generations.update(
                {core_id: 0 for core_id in range(1, self.profile.core_count)}
            )

    def mailbox(self, core_id: int) -> StartMailbox:
        self._require_secondary_coreid(core_id)
        return self.mailboxes[core_id]

    def publish_start(
        self,
        target_coreid: int,
        generation: int,
        *,
        entry_pcc: SlottedCapability,
        dsc: Capability,
        rsc: Capability,
        ksc: Capability | None = None,
        krc: Capability | None = None,
        tvc: Capability | None = None,
        ddc: Capability | None = None,
        arg0: int = 0,
        arg_cap0: Capability | None = None,
    ) -> StartMailbox:
        mailbox = StartMailbox(
            target_coreid=target_coreid,
            generation=generation,
            state=MailboxState.READY,
            entry_pcc=entry_pcc,
            dsc=dsc,
            rsc=rsc,
            ksc=ksc,
            krc=krc,
            tvc=tvc,
            ddc=ddc,
            arg0=arg0,
            arg_cap0=arg_cap0,
        )
        self.publish_mailbox(target_coreid, mailbox)
        return mailbox

    def publish_mailbox(self, slot_coreid: int, mailbox: StartMailbox) -> None:
        self._require_secondary_coreid(slot_coreid)
        if not isinstance(mailbox, StartMailbox):
            raise TypeError("mailbox must be a StartMailbox")
        current = self.mailboxes[slot_coreid]
        if current.state is MailboxState.READY:
            raise ValueError("cannot update a READY start mailbox in place")
        mailbox.state = MailboxState.READY
        mailbox.failure_code = StartupFailureCode.NONE
        self.mailboxes[slot_coreid] = mailbox

    def send_start_signal(
        self,
        cores: Sequence[CoreState],
        target_coreid: int,
    ) -> StartupResult:
        if target_coreid <= 0 or target_coreid >= self.profile.core_count:
            return StartupResult(
                target_coreid,
                False,
                StartupFailureCode.INVALID_TARGET,
                MailboxState.FAILED,
                CoreLifecycle.STOPPED,
            )
        if len(cores) <= target_coreid:
            raise ValueError("cores does not contain the target core")
        target = cores[target_coreid]
        if not isinstance(target, CoreState):
            raise TypeError("cores must contain CoreState instances")
        if target.core_id != target_coreid:
            raise ValueError("target core index does not match COREID")

        mailbox = self.mailboxes[target_coreid]
        if target.lifecycle is CoreLifecycle.STARTED:
            return self._fail(target, mailbox, StartupFailureCode.ALREADY_STARTED, replace_state=False)
        if target.lifecycle not in (
            CoreLifecycle.STOPPED,
            CoreLifecycle.WFI_PARKED,
            CoreLifecycle.START_FAILED,
        ):
            return self._fail(target, mailbox, StartupFailureCode.INVALID_TARGET)

        target.lifecycle = CoreLifecycle.START_PENDING
        failure = self._validate_mailbox(target, mailbox)
        if failure is not StartupFailureCode.NONE:
            return self._fail(target, mailbox, failure)

        self._install_startup_state(target, mailbox)
        mailbox.state = MailboxState.CONSUMED
        mailbox.failure_code = StartupFailureCode.NONE
        self.consumed_generations[target_coreid] = mailbox.generation
        return StartupResult(
            target_coreid,
            True,
            StartupFailureCode.NONE,
            mailbox.state,
            target.lifecycle,
        )

    def _validate_mailbox(
        self,
        target: CoreState,
        mailbox: StartMailbox,
    ) -> StartupFailureCode:
        if mailbox.state is not MailboxState.READY:
            return StartupFailureCode.NOT_READY
        if mailbox.target_coreid != target.core_id:
            return StartupFailureCode.WRONG_CORE
        if mailbox.generation <= self.consumed_generations[target.core_id]:
            return StartupFailureCode.STALE_GENERATION
        if not _valid_entry_pcc(mailbox.entry_pcc):
            return StartupFailureCode.INVALID_PCC
        if not _valid_stack_capability(mailbox.dsc):
            return StartupFailureCode.INVALID_STACK
        if not _valid_stack_capability(mailbox.rsc):
            return StartupFailureCode.INVALID_STACK
        if mailbox.ksc is not None and not _valid_stack_capability(mailbox.ksc):
            return StartupFailureCode.INVALID_CAPABILITY
        if mailbox.krc is not None and not _valid_plain_capability(mailbox.krc):
            return StartupFailureCode.INVALID_CAPABILITY
        if mailbox.tvc is not None and not _valid_executable_capability(mailbox.tvc):
            return StartupFailureCode.INVALID_CAPABILITY
        if mailbox.ddc is not None and not _valid_plain_capability(mailbox.ddc):
            return StartupFailureCode.INVALID_CAPABILITY
        if mailbox.arg_cap0 is not None and not _valid_plain_capability(mailbox.arg_cap0):
            return StartupFailureCode.INVALID_CAPABILITY
        return StartupFailureCode.NONE

    def _install_startup_state(self, target: CoreState, mailbox: StartMailbox) -> None:
        assert mailbox.entry_pcc is not None
        assert mailbox.dsc is not None
        assert mailbox.rsc is not None

        target.scalar_csrs = csrs.ScalarCsrFile.reset(target.core_id)
        for index in range(16):
            target.write_d(index, 0)
        target.write_d(0, mailbox.arg0)
        for index in range(8):
            target.write_c(index, Capability.invalid())
        if mailbox.arg_cap0 is not None:
            target.write_c(0, mailbox.arg_cap0)

        target.install_pcc(mailbox.entry_pcc)
        _write_special(target, "DSC", mailbox.dsc)
        _write_special(target, "RSC", mailbox.rsc)
        _write_special(target, "KSC", mailbox.ksc or Capability.invalid())
        _write_special(target, "KRC", mailbox.krc or Capability.invalid())
        _write_special(target, "TVC", mailbox.tvc or Capability.invalid())
        _write_special(target, "DDC", mailbox.ddc or Capability.invalid())
        target.write_csr_raw(csrs.CSR_IENABLE, 0)
        target.write_csr_raw(csrs.CSR_IPENDING, 0)
        target.write_csr_raw(csrs.CSR_SATP, 0)
        target.write_csr_raw(csrs.CSR_ASID, 0)
        target.reservation.clear()
        target.lifecycle = CoreLifecycle.STARTED

    def _fail(
        self,
        target: CoreState,
        mailbox: StartMailbox,
        code: StartupFailureCode,
        *,
        replace_state: bool = True,
    ) -> StartupResult:
        if replace_state:
            target.lifecycle = CoreLifecycle.START_FAILED
            mailbox.state = MailboxState.FAILED
        mailbox.failure_code = code
        return StartupResult(
            target.core_id,
            False,
            code,
            mailbox.state,
            target.lifecycle,
        )

    def _require_secondary_coreid(self, core_id: int) -> int:
        if type(core_id) is not int:
            raise TypeError("core_id must be an int")
        if not 1 <= core_id < self.profile.core_count:
            raise ValueError("core_id must name a secondary core")
        return core_id


def _valid_entry_pcc(value: SlottedCapability | None) -> bool:
    if not isinstance(value, SlottedCapability):
        return False
    if not value.is_valid or value.slot != SLOT_0:
        return False
    return _valid_executable_capability(value.without_slot())


def _valid_executable_capability(value: Capability | None) -> bool:
    if not _valid_plain_capability(value):
        return False
    assert value is not None
    return (
        value.payload.has_permissions(CapabilityPermission.EX)
        and value.payload.bounds.contains_cursor(value.payload.cursor)
    )


def _valid_stack_capability(value: Capability | None) -> bool:
    if not _valid_plain_capability(value):
        return False
    assert value is not None
    required = (
        CapabilityPermission.LD
        | CapabilityPermission.ST
        | CapabilityPermission.LC
        | CapabilityPermission.SC
        | CapabilityPermission.SL
    )
    return (
        value.is_local
        and value.payload.has_permissions(required)
        and not value.payload.has_permissions(CapabilityPermission.EX)
        and value.payload.bounds.contains_cursor(value.payload.cursor)
        and is_aligned(value.payload.cursor, CAPABILITY_OBJECT_CELLS)
    )


def _valid_plain_capability(value: Capability | None) -> bool:
    return (
        isinstance(value, Capability)
        and value.is_valid
        and value.is_unsealed
        and value.payload.bounds.contains_cursor(value.payload.cursor)
    )


def _write_special(core: CoreState, name: str, capability: Capability) -> None:
    core.write_ccsr(SPECIAL_NAME_TO_CCSR_INDEX[name], capability.copy())
