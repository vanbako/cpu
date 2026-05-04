"""Cold-reset construction helpers for CPU v0.1.

Owner stories:
- E11-S01: cold reset lifecycle and scalar reset state.
- E11-S02: reset capability state.
- I02-S05: reset-state construction for the semantic model.
"""

from __future__ import annotations

from .capabilities import (
    Capability,
    CapabilityFlag,
    CapabilityPayload,
    CapabilityPermission,
    OTYPE_UNSEALED,
)
from .cells import require_cell_address
from .csrs import ScalarCsrFile
from .state import (
    CoreLifecycle,
    CoreState,
    SlottedCapability,
    SLOT_0,
)


V01_CORE_COUNT = 4


def require_reset_core_id(core_id: int) -> int:
    if type(core_id) is not int:
        raise TypeError("core_id must be an int")
    if not 0 <= core_id < V01_CORE_COUNT:
        raise ValueError(f"core_id must be in range [0, {V01_CORE_COUNT})")
    return core_id


def reset_pcc_capability(reset_vector: int) -> SlottedCapability:
    reset_vector = require_cell_address(reset_vector, "reset_vector")
    payload = CapabilityPayload(
        cursor=reset_vector,
        permissions=int(CapabilityPermission.EX),
        otype=OTYPE_UNSEALED,
        flags=int(CapabilityFlag.G),
    )
    return SlottedCapability.from_capability(Capability.valid(payload), SLOT_0)


def cold_reset_core(
    core_id: int,
    reset_vector: int,
    secondary_lifecycle: CoreLifecycle = CoreLifecycle.STOPPED,
) -> CoreState:
    core_id = require_reset_core_id(core_id)
    if not isinstance(secondary_lifecycle, CoreLifecycle):
        raise TypeError("secondary_lifecycle must be a CoreLifecycle")
    if secondary_lifecycle not in (CoreLifecycle.STOPPED, CoreLifecycle.WFI_PARKED):
        raise ValueError("secondary_lifecycle must be STOPPED or WFI_PARKED")

    lifecycle = CoreLifecycle.RUNNING if core_id == 0 else secondary_lifecycle
    core = CoreState(
        core_id=core_id,
        lifecycle=lifecycle,
        scalar_csrs=ScalarCsrFile.reset(core_id),
    )
    if core_id == 0:
        core.install_pcc(reset_pcc_capability(reset_vector))
    return core


def cold_reset_cores(
    reset_vector: int,
    secondary_lifecycle: CoreLifecycle = CoreLifecycle.STOPPED,
) -> tuple[CoreState, ...]:
    return tuple(
        cold_reset_core(core_id, reset_vector, secondary_lifecycle)
        for core_id in range(V01_CORE_COUNT)
    )
