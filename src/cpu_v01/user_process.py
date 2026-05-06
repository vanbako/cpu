"""User process image and entry-context fixtures for CPU v0.1.

Owner stories:
- E05-S01/E05-S02: public ABI argument register windows.
- E07-S01: user/kernel privilege state.
- E09-S02: SATP and ASID context fields.
- I18-S01: user process image and entry-context fixture.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from . import (
    abi,
    assembly,
    capabilities as caps,
    csrs,
    platform,
    program_image,
    serialization,
    state,
)
from .cells import CAPABILITY_OBJECT_CELLS
from .memory import TaggedMemory


USER_ENTRY_CELL = platform.RESET_VECTOR + 0x400
USER_TEXT_CELLS = 0x20
USER_DATA_BASE = platform.RAM_BASE + 0x0800
USER_DATA_CELLS = 0x20
USER_STACK_BASE = platform.RAM_BASE + 0x8000
USER_STACK_CELLS = 0x0800
USER_RETURN_STACK_BASE = platform.RAM_BASE + 0x9000
USER_RETURN_STACK_CELLS = 0x0800
USER_ASID = 0x12
USER_ARG0 = 0xC0_18
USER_ARG1 = 0x01

USER_TEXT_SOURCE = (
    "SYS",
    "PAUSE",
)


class UserProcessError(ValueError):
    """Raised when a user process image or entry context is rejected."""


@dataclass(frozen=True)
class UserEntryContext:
    manifest: program_image.ProgramImageManifest
    pcc: state.SlottedCapability
    dsc: caps.Capability
    rsc: caps.Capability
    satp: int
    integer_arguments: tuple[int, ...] = ()
    capability_arguments: tuple[caps.Capability, ...] = ()
    user_interrupt_enable: bool = True
    protect_return_stack: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.manifest, program_image.ProgramImageManifest):
            raise TypeError("manifest must be a ProgramImageManifest")
        if not isinstance(self.pcc, state.SlottedCapability):
            raise TypeError("pcc must be a SlottedCapability")
        if not isinstance(self.dsc, caps.Capability):
            raise TypeError("dsc must be a Capability")
        if not isinstance(self.rsc, caps.Capability):
            raise TypeError("rsc must be a Capability")
        object.__setattr__(self, "satp", csrs.validate_satp_value(self.satp))
        object.__setattr__(
            self,
            "integer_arguments",
            tuple(
                csrs.require_uint(value, csrs.CSR_BITS, "integer argument")
                for value in self.integer_arguments
            ),
        )
        object.__setattr__(self, "capability_arguments", tuple(self.capability_arguments))
        for capability in self.capability_arguments:
            if not isinstance(capability, caps.Capability):
                raise TypeError("capability_arguments must contain Capability values")
        if type(self.user_interrupt_enable) is not bool:
            raise TypeError("user_interrupt_enable must be a bool")
        if type(self.protect_return_stack) is not bool:
            raise TypeError("protect_return_stack must be a bool")


@dataclass(frozen=True)
class UserEntryReport:
    manifest_name: str
    entry_cell: int
    entry_slot: int
    satp: int
    asid: int
    integer_argument_registers: tuple[int, ...]
    capability_argument_registers: tuple[int, ...]
    user_mode: bool
    interrupt_enable: bool
    return_stack_protected: bool


def user_process_manifest() -> program_image.ProgramImageManifest:
    """Return the small MANIFEST_ENTRY user image used by I18-S01 fixtures."""
    text_payload = _padded_cells(assembly.assemble_program(USER_TEXT_SOURCE), USER_TEXT_CELLS)
    data_payload = _padded_cells((0xC0_18, 0x00), USER_DATA_CELLS)
    return program_image.ProgramImageManifest(
        name="user_process_demo",
        entry_cell=USER_ENTRY_CELL,
        entry_source=program_image.EntryCapabilitySource.MANIFEST_ENTRY,
        sections=(
            program_image.ProgramImageSection.from_serialized_cells(
                name="user_text",
                region_name="boot_rom",
                base_cell=USER_ENTRY_CELL,
                alignment_cells=2,
                payload_octets=serialization.serialize_cells(text_payload),
                kind=program_image.ProgramImageSectionKind.TEXT,
            ),
            program_image.ProgramImageSection.from_serialized_cells(
                name="user_data",
                region_name="main_ram",
                base_cell=USER_DATA_BASE,
                alignment_cells=2,
                payload_octets=serialization.serialize_cells(data_payload),
                kind=program_image.ProgramImageSectionKind.DATA,
            ),
        ),
    )


def default_user_entry_context() -> UserEntryContext:
    """Build a valid user entry context for the default user process image."""
    manifest = user_process_manifest()
    data_cap = _global_capability(
        cursor=USER_DATA_BASE,
        base=USER_DATA_BASE,
        top=USER_DATA_BASE + USER_DATA_CELLS,
        permissions=(
            caps.CapabilityPermission.LD
            | caps.CapabilityPermission.ST
            | caps.CapabilityPermission.LC
        ),
    )
    return UserEntryContext(
        manifest=manifest,
        pcc=entry_pcc_for_manifest(manifest),
        dsc=_stack_capability(USER_STACK_BASE, USER_STACK_CELLS),
        rsc=_stack_capability(USER_RETURN_STACK_BASE, USER_RETURN_STACK_CELLS),
        satp=csrs.pack_satp(csrs.SATP_MODE_BARE, USER_ASID, 0),
        integer_arguments=(USER_ARG0, USER_ARG1),
        capability_arguments=(data_cap,),
    )


def entry_pcc_for_manifest(
    manifest: program_image.ProgramImageManifest,
    profile: platform.TestPlatformProfile = platform.TEST_PLATFORM_PROFILE,
) -> state.SlottedCapability:
    """Construct the user entry PCC from a validated MANIFEST_ENTRY image."""
    issues = validate_user_process_image(manifest, profile)
    if issues:
        raise UserProcessError("; ".join(issues))
    section = _entry_text_section(manifest)
    assert section is not None
    return state.SlottedCapability.from_capability(
        _global_capability(
            cursor=manifest.entry_cell,
            base=section.base_cell,
            top=section.end_cell,
            permissions=caps.CapabilityPermission.EX,
        ),
        state.SLOT_0,
    )


def validate_user_process_image(
    manifest: program_image.ProgramImageManifest,
    profile: platform.TestPlatformProfile = platform.TEST_PLATFORM_PROFILE,
) -> tuple[str, ...]:
    """Return deterministic user-image issues without loading memory."""
    issues = list(program_image.validate_program_image_manifest(manifest, profile))
    if manifest.entry_source is not program_image.EntryCapabilitySource.MANIFEST_ENTRY:
        issues.append("user process image must use MANIFEST_ENTRY")
    if manifest.entry_slot != state.SLOT_0:
        issues.append("user process image must enter slot 0")
    return tuple(issues)


def load_user_process_image(
    context: UserEntryContext,
    memory: TaggedMemory,
    profile: platform.TestPlatformProfile = platform.TEST_PLATFORM_PROFILE,
) -> program_image.ProgramImageLoadReport:
    """Load a validated user process image into simulator memory."""
    if not isinstance(memory, TaggedMemory):
        raise TypeError("memory must be a TaggedMemory")
    issues = validate_user_entry_context(context, profile)
    if issues:
        raise UserProcessError("; ".join(issues))
    return program_image.load_program_image(context.manifest, memory, profile)


def validate_user_entry_context(
    context: UserEntryContext,
    profile: platform.TestPlatformProfile = platform.TEST_PLATFORM_PROFILE,
) -> tuple[str, ...]:
    """Return deterministic user entry-context issues without mutating a core."""
    if not isinstance(context, UserEntryContext):
        raise TypeError("context must be a UserEntryContext")
    issues = list(validate_user_process_image(context.manifest, profile))
    issues.extend(_validate_entry_pcc(context, profile))
    issues.extend(_validate_stack_capability(context.dsc, "DSC", profile))
    issues.extend(_validate_stack_capability(context.rsc, "RSC", profile))
    issues.extend(_validate_satp(context))
    issues.extend(_validate_abi_arguments(context))
    return tuple(issues)


def enter_user_process_context(
    core: state.CoreState,
    context: UserEntryContext,
    memory: TaggedMemory | None = None,
    profile: platform.TestPlatformProfile = platform.TEST_PLATFORM_PROFILE,
) -> UserEntryReport:
    """Install a validated user context atomically from the kernel fixture."""
    if not isinstance(core, state.CoreState):
        raise TypeError("core must be a CoreState")
    if memory is not None and not isinstance(memory, TaggedMemory):
        raise TypeError("memory must be a TaggedMemory")
    issues = validate_user_entry_context(context, profile)
    if issues:
        raise UserProcessError("; ".join(issues))

    for index in range(state.INTEGER_REGISTER_COUNT):
        core.write_d(index, 0)
    for index, value in enumerate(context.integer_arguments):
        core.write_d(abi.INTEGER_ARGUMENT_REGS[index], value)

    for index in range(state.GENERAL_CAPABILITY_REGISTER_COUNT):
        core.write_c(index, caps.Capability.invalid())
    for index, capability in enumerate(context.capability_arguments):
        core.write_c(abi.CAPABILITY_ARGUMENT_REGS[index], capability)

    core.install_pcc(context.pcc)
    _write_special(core, "DSC", context.dsc)
    _write_special(core, "RSC", context.rsc)
    core.write_csr_raw(csrs.CSR_SATP, context.satp)
    core.write_csr_raw(csrs.CSR_ASID, csrs.satp_asid(context.satp))
    core.tlbs.invalidate_all()
    core.reservation.clear()
    core.write_csr_raw(csrs.CSR_SR, _user_entry_sr(core.read_csr(csrs.CSR_SR), context))

    return_stack_protected = False
    if memory is not None and context.protect_return_stack:
        memory.protect_range(context.rsc.payload.bounds.base, _bounds_size(context.rsc))
        return_stack_protected = True

    return UserEntryReport(
        manifest_name=context.manifest.name,
        entry_cell=core.pcc.payload.cursor,
        entry_slot=core.pcc.slot,
        satp=core.read_csr(csrs.CSR_SATP),
        asid=core.read_csr(csrs.CSR_ASID),
        integer_argument_registers=abi.INTEGER_ARGUMENT_REGS[: len(context.integer_arguments)],
        capability_argument_registers=abi.CAPABILITY_ARGUMENT_REGS[
            : len(context.capability_arguments)
        ],
        user_mode=not _sr_bit(core.read_csr(csrs.CSR_SR), csrs.SR_PRIV_BIT),
        interrupt_enable=_sr_bit(core.read_csr(csrs.CSR_SR), csrs.SR_IE_BIT),
        return_stack_protected=return_stack_protected,
    )


def _validate_entry_pcc(
    context: UserEntryContext,
    profile: platform.TestPlatformProfile,
) -> tuple[str, ...]:
    issues: list[str] = []
    expected = None
    try:
        expected = entry_pcc_for_manifest(context.manifest, profile)
    except UserProcessError as exc:
        issues.append(str(exc))
    if context.pcc.slot != state.SLOT_0:
        issues.append("user entry PCC must enter slot 0")
    if context.pcc.is_invalid:
        issues.append("user entry PCC must carry a valid tag")
    elif not context.pcc.payload.has_permissions(caps.CapabilityPermission.EX):
        issues.append("user entry PCC must grant execute permission")
    elif context.pcc.payload.cursor != context.manifest.entry_cell:
        issues.append("user entry PCC cursor must equal manifest entry_cell")
    if expected is not None and context.pcc != expected:
        issues.append("user entry PCC must match the manifest text bounds")
    return tuple(dict.fromkeys(issues))


def _validate_stack_capability(
    capability: caps.Capability,
    name: str,
    profile: platform.TestPlatformProfile,
) -> tuple[str, ...]:
    issues: list[str] = []
    if capability.is_invalid:
        return (f"user {name} must carry a valid tag",)
    if capability.is_sealed:
        issues.append(f"user {name} must be unsealed")
    if not capability.is_local:
        issues.append(f"user {name} must be local")
    required = (
        caps.CapabilityPermission.LD
        | caps.CapabilityPermission.ST
        | caps.CapabilityPermission.LC
        | caps.CapabilityPermission.SC
        | caps.CapabilityPermission.SL
    )
    if not capability.payload.has_permissions(required):
        issues.append(f"user {name} must grant stack load/store capability permissions")
    if capability.payload.has_permissions(caps.CapabilityPermission.EX):
        issues.append(f"user {name} must not grant execute permission")
    if not capability.payload.bounds.contains_cursor(capability.payload.cursor):
        issues.append(f"user {name} cursor must be inside bounds")
    if capability.payload.cursor % CAPABILITY_OBJECT_CELLS:
        issues.append(f"user {name} cursor must be capability-slot aligned")
    try:
        ram = profile.region_by_name("main_ram")
    except KeyError as exc:
        issues.append(str(exc))
    else:
        bounds = capability.payload.bounds
        if not ram.range.contains_range(bounds.range):
            issues.append(f"user {name} bounds must be inside main RAM")
    return tuple(issues)


def _validate_satp(context: UserEntryContext) -> tuple[str, ...]:
    issues: list[str] = []
    try:
        csrs.validate_satp_value(context.satp)
    except ValueError as exc:
        issues.append(str(exc))
    if csrs.satp_asid(context.satp) == 0:
        issues.append("user SATP must carry a nonzero ASID")
    return tuple(issues)


def _validate_abi_arguments(context: UserEntryContext) -> tuple[str, ...]:
    issues: list[str] = []
    if len(context.integer_arguments) > len(abi.INTEGER_ARGUMENT_REGS):
        issues.append("user integer ABI arguments exceed D0-D5")
    if len(context.capability_arguments) > len(abi.CAPABILITY_ARGUMENT_REGS):
        issues.append("user capability ABI arguments exceed C0-C3")
    for index, capability in enumerate(context.capability_arguments):
        if capability.is_invalid:
            issues.append(f"user capability argument C{index} must carry a valid tag")
    return tuple(issues)


def _entry_text_section(
    manifest: program_image.ProgramImageManifest,
) -> program_image.ProgramImageSection | None:
    for section in manifest.sections:
        if section.kind is not program_image.ProgramImageSectionKind.TEXT:
            continue
        if section.contains_cell(manifest.entry_cell):
            return section
    return None


def _padded_cells(cells: Iterable[int], size_cells: int) -> tuple[int, ...]:
    cell_tuple = tuple(cells)
    if len(cell_tuple) > size_cells:
        raise ValueError("payload exceeds requested padded size")
    return (*cell_tuple, *((0,) * (size_cells - len(cell_tuple))))


def _global_capability(
    *,
    cursor: int,
    base: int,
    top: int,
    permissions: caps.CapabilityPermission,
) -> caps.Capability:
    return _capability(
        cursor=cursor,
        base=base,
        top=top,
        permissions=permissions,
        flags=caps.CapabilityFlag.G,
    )


def _stack_capability(base: int, size_cells: int) -> caps.Capability:
    return _capability(
        cursor=base + size_cells - CAPABILITY_OBJECT_CELLS,
        base=base,
        top=base + size_cells,
        permissions=(
            caps.CapabilityPermission.LD
            | caps.CapabilityPermission.ST
            | caps.CapabilityPermission.LC
            | caps.CapabilityPermission.SC
            | caps.CapabilityPermission.SL
        ),
        flags=caps.CapabilityFlag.NONE,
    )


def _capability(
    *,
    cursor: int,
    base: int,
    top: int,
    permissions: caps.CapabilityPermission,
    flags: caps.CapabilityFlag,
) -> caps.Capability:
    payload = caps.CapabilityPayload(
        cursor=cursor,
        permissions=int(permissions),
        flags=int(flags),
    ).with_bounds(base, top)
    return caps.Capability.valid(payload)


def _write_special(core: state.CoreState, name: str, capability: caps.Capability) -> None:
    core.write_ccsr(state.SPECIAL_NAME_TO_CCSR_INDEX[name], capability.copy())


def _bounds_size(capability: caps.Capability) -> int:
    bounds = capability.payload.bounds
    return bounds.top - bounds.base


def _user_entry_sr(old_sr: int, context: UserEntryContext) -> int:
    value = old_sr
    value = _set_sr_bit(value, csrs.SR_IE_BIT, context.user_interrupt_enable)
    value = _set_sr_bit(value, csrs.SR_PIE_BIT, context.user_interrupt_enable)
    value = _set_sr_bit(value, csrs.SR_PRIV_BIT, False)
    value = _set_sr_bit(value, csrs.SR_PPRIV_BIT, False)
    value = _set_sr_bit(value, csrs.SR_EXL_BIT, False)
    return value


def _set_sr_bit(value: int, bit: int, enabled: bool) -> int:
    mask = 1 << bit
    if enabled:
        return value | mask
    return value & ~mask


def _sr_bit(value: int, bit: int) -> bool:
    return bool(value & (1 << bit))
