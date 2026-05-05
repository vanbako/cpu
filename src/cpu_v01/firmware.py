"""Tiny firmware ROM bring-up helpers for CPU v0.1.

Owner stories:
- E11-S02: ROM/firmware capability initialization.
- I14-S01: tiny ROM initialization sequence and kernel handoff.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import assembly, capabilities as caps, platform, program_image, serialization, state
from .cells import CAPABILITY_OBJECT_CELLS, is_aligned
from .memory import TaggedMemory


KERNEL_HANDOFF_CELL = platform.RESET_VECTOR + 0x80
ROM_TRAP_VECTOR_CELL = platform.RESET_VECTOR + 0xC0
ROM_HANDOFF_MAGIC = 0xC0_01

ROM_INIT_SOURCE = (
    "CPY D0, D0",
    "PAUSE",
)
KERNEL_HANDOFF_SOURCE = (
    "PAUSE",
)

KERNEL_STACK_BASE = platform.RAM_BASE + 0x1000
KERNEL_STACK_CELLS = 0x400
DATA_STACK_BASE = platform.RAM_BASE + 0x2000
DATA_STACK_CELLS = 0x400
RETURN_STACK_BASE = platform.RAM_BASE + 0x3000
RETURN_STACK_CELLS = 0x400


class TinyRomError(RuntimeError):
    """Raised when the tiny ROM bring-up fixture cannot reach handoff."""


@dataclass(frozen=True)
class TinyRomHandoffState:
    pcc: state.SlottedCapability
    krc: caps.Capability
    ksc: caps.Capability
    dsc: caps.Capability
    rsc: caps.Capability
    tvc: caps.Capability
    ddc: caps.Capability
    general_capability_tags: tuple[bool, ...]
    handoff_magic: int
    protected_return_stack_base: int
    protected_return_stack_cells: int


@dataclass(frozen=True)
class TinyRomReport:
    image_load: program_image.ProgramImageLoadReport
    profile_issues: tuple[str, ...]
    steps: int
    handoff: TinyRomHandoffState


def tiny_rom_manifest() -> program_image.ProgramImageManifest:
    """Return the serialized ROM image used by the tiny bring-up fixture."""
    init_cells = assembly.assemble_program(ROM_INIT_SOURCE)
    handoff_cells = assembly.assemble_program(KERNEL_HANDOFF_SOURCE)
    return program_image.ProgramImageManifest(
        name="tiny_rom_init",
        entry_cell=platform.RESET_VECTOR,
        entry_source=program_image.EntryCapabilitySource.RESET_PCC,
        sections=(
            program_image.ProgramImageSection.from_serialized_cells(
                name="rom_init",
                region_name="boot_rom",
                base_cell=platform.RESET_VECTOR,
                alignment_cells=2,
                payload_octets=serialization.serialize_cells(init_cells),
                kind=program_image.ProgramImageSectionKind.TEXT,
            ),
            program_image.ProgramImageSection.from_serialized_cells(
                name="kernel_handoff",
                region_name="boot_rom",
                base_cell=KERNEL_HANDOFF_CELL,
                alignment_cells=2,
                payload_octets=serialization.serialize_cells(handoff_cells),
                kind=program_image.ProgramImageSectionKind.TEXT,
            ),
        ),
    )


def run_tiny_rom_initialization(
    *,
    profile: platform.TestPlatformProfile = platform.TEST_PLATFORM_PROFILE,
    memory: TaggedMemory | None = None,
) -> TinyRomReport:
    """Load the tiny ROM image and run the trusted ROM handoff sequence."""
    if memory is None:
        memory = TaggedMemory()
    if not isinstance(memory, TaggedMemory):
        raise TypeError("memory must be a TaggedMemory")
    issues = validate_tiny_rom_layout(profile)
    if issues:
        raise TinyRomError("; ".join(issues))

    manifest = tiny_rom_manifest()
    load_report = program_image.load_program_image(manifest, memory)
    core = platform.cold_reset_cores(profile)[0]
    handoff = initialize_boot_core_for_kernel_handoff(core, memory, profile=profile)
    return TinyRomReport(
        image_load=load_report,
        profile_issues=issues,
        steps=3,
        handoff=handoff,
    )


def initialize_boot_core_for_kernel_handoff(
    core: state.CoreState,
    memory: TaggedMemory,
    *,
    profile: platform.TestPlatformProfile = platform.TEST_PLATFORM_PROFILE,
) -> TinyRomHandoffState:
    """Install trusted ROM capabilities and branch the boot core to handoff."""
    if not isinstance(core, state.CoreState):
        raise TypeError("core must be a CoreState")
    if not isinstance(memory, TaggedMemory):
        raise TypeError("memory must be a TaggedMemory")
    issues = validate_tiny_rom_layout(profile)
    if issues:
        raise TinyRomError("; ".join(issues))

    rom = profile.reset_rom_region
    ram = profile.region_by_name("main_ram")
    krc = _global_capability(
        cursor=ram.base,
        base=0,
        top=1 << 48,
        permissions=caps.ALL_PERMISSIONS,
    )
    ksc = _stack_capability(KERNEL_STACK_BASE, KERNEL_STACK_CELLS)
    dsc = _stack_capability(DATA_STACK_BASE, DATA_STACK_CELLS)
    rsc = _stack_capability(RETURN_STACK_BASE, RETURN_STACK_CELLS)
    tvc = _global_capability(
        cursor=ROM_TRAP_VECTOR_CELL,
        base=rom.base,
        top=rom.end,
        permissions=caps.CapabilityPermission.EX,
    )
    handoff_pcc = state.SlottedCapability.from_capability(
        _global_capability(
            cursor=KERNEL_HANDOFF_CELL,
            base=rom.base,
            top=rom.end,
            permissions=caps.CapabilityPermission.EX,
        ),
        state.SLOT_0,
    )

    for index in range(8):
        core.write_c(index, caps.Capability.invalid())
    core.write_d(0, ROM_HANDOFF_MAGIC)
    core.install_pcc(handoff_pcc)
    _write_special(core, "KRC", krc)
    _write_special(core, "KSC", ksc)
    _write_special(core, "DSC", dsc)
    _write_special(core, "RSC", rsc)
    _write_special(core, "TVC", tvc)
    _write_special(core, "DDC", caps.Capability.invalid())
    memory.protect_range(RETURN_STACK_BASE, RETURN_STACK_CELLS)

    return TinyRomHandoffState(
        pcc=core.pcc,
        krc=krc,
        ksc=ksc,
        dsc=dsc,
        rsc=rsc,
        tvc=tvc,
        ddc=core.special_capabilities.read("DDC"),
        general_capability_tags=tuple(
            capability.is_valid for capability in core.general_capabilities
        ),
        handoff_magic=core.read_d(0),
        protected_return_stack_base=RETURN_STACK_BASE,
        protected_return_stack_cells=RETURN_STACK_CELLS,
    )


def validate_tiny_rom_layout(
    profile: platform.TestPlatformProfile = platform.TEST_PLATFORM_PROFILE,
) -> tuple[str, ...]:
    """Validate that the platform can host the tiny ROM handoff fixture."""
    if not isinstance(profile, platform.TestPlatformProfile):
        raise TypeError("profile must be a TestPlatformProfile")
    issues = list(platform.validate_profile(profile))
    try:
        rom = profile.reset_rom_region
        ram = profile.region_by_name("main_ram")
    except (KeyError, ValueError) as exc:
        return tuple([*issues, str(exc)])

    for name, cursor in (
        ("kernel handoff", KERNEL_HANDOFF_CELL),
        ("ROM trap vector", ROM_TRAP_VECTOR_CELL),
    ):
        if not rom.contains(cursor):
            issues.append(f"{name} cell must be inside boot ROM")

    for name, base, size_cells in (
        ("kernel stack", KERNEL_STACK_BASE, KERNEL_STACK_CELLS),
        ("data stack", DATA_STACK_BASE, DATA_STACK_CELLS),
        ("return stack", RETURN_STACK_BASE, RETURN_STACK_CELLS),
    ):
        cursor = _stack_cursor(base, size_cells)
        if not (ram.base <= base and base + size_cells <= ram.end):
            issues.append(f"{name} must be inside main RAM")
        if not is_aligned(cursor, CAPABILITY_OBJECT_CELLS):
            issues.append(f"{name} cursor must be capability-slot aligned")

    return tuple(issues)


def _stack_capability(base: int, size_cells: int) -> caps.Capability:
    return _local_capability(
        cursor=_stack_cursor(base, size_cells),
        base=base,
        top=base + size_cells,
        permissions=(
            caps.CapabilityPermission.LD
            | caps.CapabilityPermission.ST
            | caps.CapabilityPermission.LC
            | caps.CapabilityPermission.SC
            | caps.CapabilityPermission.SL
        ),
    )


def _stack_cursor(base: int, size_cells: int) -> int:
    return base + size_cells - CAPABILITY_OBJECT_CELLS


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


def _local_capability(
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
