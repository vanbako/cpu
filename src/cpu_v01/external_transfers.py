"""Noncoherent external-agent transfer fixtures for CPU v0.1.

Owner stories:
- E10-S03: coherent payload/tag visibility at CPU coherence points.
- E10-S04: tag-unaware noncoherent external-agent memory effects.
- E10-S05: cache maintenance for external-agent ownership handoff.
- I06-S04: cache and external-agent litmus support.
- I15-S02: capability tag non-forgery and tag clearing.
- I18-S02: VM memory-type fixture.
- I19-S01: CPU external endpoint and fabric attachment boundary.
- I19-S03: noncoherent external-agent transfer fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from . import capabilities as caps, fence_ops, litmus, mmu, platform, reset, vm
from .cells import (
    CACHE_LINE_CELLS,
    CAPABILITY_OBJECT_CELLS,
    cache_line_base,
    require_cell_address,
    require_positive_cell_count,
)
from .instructions import ExecutionResult
from .memory import TaggedMemory


COHERENT_BUFFER_ADDRESS = 0x0019_0300
UNCACHEABLE_BUFFER_ADDRESS = 0x0019_0400
SOURCE_CAP_CURSOR = 0x0019_3000
REPLACEMENT_CAP_CURSOR = 0x0019_4000


class BufferOwner(Enum):
    CPU = "CPU"
    EXTERNAL_AGENT = "EXTERNAL_AGENT"


@dataclass(frozen=True)
class ExternalBufferDescriptor:
    name: str
    address: int
    length_cells: int = CACHE_LINE_CELLS
    memory_type: int = mmu.MEMORY_TYPE_NORMAL_COHERENT

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name must not be empty")
        object.__setattr__(self, "address", require_cell_address(self.address))
        object.__setattr__(
            self,
            "length_cells",
            require_positive_cell_count(self.length_cells, "length_cells"),
        )
        if cache_line_base(self.address) != self.address:
            raise ValueError("external buffers must start on a cache-line boundary")
        if self.length_cells % CACHE_LINE_CELLS:
            raise ValueError("external buffer length must be whole cache lines")
        if self.memory_type not in _SUPPORTED_MEMORY_TYPES:
            raise ValueError("external buffer memory_type is not supported")

    @property
    def requires_cache_maintenance(self) -> bool:
        return self.memory_type == mmu.MEMORY_TYPE_NORMAL_COHERENT

    @property
    def allows_payload_transfer(self) -> bool:
        return self.memory_type in (
            mmu.MEMORY_TYPE_NORMAL_COHERENT,
            mmu.MEMORY_TYPE_NORMAL_UNCACHEABLE,
        )

    @property
    def ownership_granularity_cells(self) -> int:
        return CACHE_LINE_CELLS


@dataclass(frozen=True)
class ExternalAgentTransferReport:
    coherent_buffer: ExternalBufferDescriptor
    uncacheable_buffer: ExternalBufferDescriptor
    device_buffer: ExternalBufferDescriptor
    source_capability: caps.Capability
    replacement_capability: caps.Capability
    cpu_to_agent_steps: tuple[str, ...]
    agent_to_cpu_steps: tuple[str, ...]
    uncacheable_steps: tuple[str, ...]
    fence_results: tuple[ExecutionResult, ...]
    external_read_before_clean: tuple[int, ...]
    external_read_after_clean: tuple[int, ...]
    memory_tag_after_clean: bool
    stale_cpu_capability_before_inval: caps.Capability
    memory_tag_after_external_write: bool
    cpu_capability_after_inval: caps.Capability
    uncacheable_capability_after_external_write: caps.Capability
    final_coherent_owner: BufferOwner
    final_uncacheable_owner: BufferOwner
    device_payload_transfer_allowed: bool
    device_cache_result: ExecutionResult
    device_cache_fault_tval: int


_SUPPORTED_MEMORY_TYPES = frozenset(
    {
        mmu.MEMORY_TYPE_NORMAL_COHERENT,
        mmu.MEMORY_TYPE_NORMAL_UNCACHEABLE,
        mmu.MEMORY_TYPE_DEVICE_ORDERED,
    }
)


def run_external_agent_transfer_fixture() -> ExternalAgentTransferReport:
    """Run CPU-to-agent and agent-to-CPU ownership handoff fixtures."""
    coherent = ExternalBufferDescriptor(
        "coherent_payload_buffer",
        COHERENT_BUFFER_ADDRESS,
        memory_type=mmu.MEMORY_TYPE_NORMAL_COHERENT,
    )
    uncacheable = ExternalBufferDescriptor(
        "uncacheable_payload_buffer",
        UNCACHEABLE_BUFFER_ADDRESS,
        memory_type=mmu.MEMORY_TYPE_NORMAL_UNCACHEABLE,
    )
    device = ExternalBufferDescriptor(
        "device_ordered_endpoint_window",
        platform.DEVICE_BASE,
        memory_type=mmu.MEMORY_TYPE_DEVICE_ORDERED,
    )
    source = _data_capability(SOURCE_CAP_CURSOR)
    replacement = _data_capability(REPLACEMENT_CAP_CURSOR)

    model = litmus.CacheDmaModel(core_count=2)
    model.csc(0, coherent.address, source)
    external_read_before_clean = model.dma_read_cells(
        coherent.address,
        CAPABILITY_OBJECT_CELLS,
    )

    cpu_to_agent_fence_before = _execute_fence()
    model.cache_clean(coherent.address)
    cpu_to_agent_fence_after = _execute_fence()
    external_read_after_clean = model.dma_read_cells(
        coherent.address,
        CAPABILITY_OBJECT_CELLS,
    )
    memory_tag_after_clean = model.memory_capability_tag(coherent.address)

    model.clc(1, coherent.address)
    model.dma_write_cells(
        coherent.address,
        caps.payload_to_cells(replacement.payload),
    )
    memory_tag_after_external_write = model.memory_capability_tag(coherent.address)
    stale_cpu_capability_before_inval = model.clc(1, coherent.address)

    agent_to_cpu_fence_before = _execute_fence()
    model.cache_inval(coherent.address)
    agent_to_cpu_fence_after = _execute_fence()
    cpu_capability_after_inval = model.clc(1, coherent.address)

    uncacheable_fence = _execute_fence()
    uncacheable_capability_after_external_write = _run_uncacheable_external_write(
        uncacheable,
        replacement,
    )
    device_policy = vm.run_memory_type_fixture()

    return ExternalAgentTransferReport(
        coherent_buffer=coherent,
        uncacheable_buffer=uncacheable,
        device_buffer=device,
        source_capability=source,
        replacement_capability=replacement,
        cpu_to_agent_steps=(
            "CPU_CSC",
            "FENCE",
            "CACHE.CLEAN",
            "FENCE",
            "OWNER_EXTERNAL_AGENT",
        ),
        agent_to_cpu_steps=(
            "EXTERNAL_WRITE",
            "FENCE",
            "CACHE.INVAL",
            "FENCE",
            "OWNER_CPU",
        ),
        uncacheable_steps=(
            "EXTERNAL_WRITE",
            "FENCE",
            "CPU_DIRECT_READ",
            "OWNER_CPU",
        ),
        fence_results=(
            cpu_to_agent_fence_before,
            cpu_to_agent_fence_after,
            agent_to_cpu_fence_before,
            agent_to_cpu_fence_after,
            uncacheable_fence,
        ),
        external_read_before_clean=external_read_before_clean,
        external_read_after_clean=external_read_after_clean,
        memory_tag_after_clean=memory_tag_after_clean,
        stale_cpu_capability_before_inval=stale_cpu_capability_before_inval,
        memory_tag_after_external_write=memory_tag_after_external_write,
        cpu_capability_after_inval=cpu_capability_after_inval,
        uncacheable_capability_after_external_write=(
            uncacheable_capability_after_external_write
        ),
        final_coherent_owner=BufferOwner.CPU,
        final_uncacheable_owner=BufferOwner.CPU,
        device_payload_transfer_allowed=device.allows_payload_transfer,
        device_cache_result=device_policy.cache_result,
        device_cache_fault_tval=device_policy.fault_tval,
    )


def _run_uncacheable_external_write(
    descriptor: ExternalBufferDescriptor,
    replacement: caps.Capability,
) -> caps.Capability:
    memory = TaggedMemory()
    memory.write_cells(
        descriptor.address,
        caps.payload_to_cells(replacement.payload),
    )
    return memory.clc(descriptor.address)


def _execute_fence() -> ExecutionResult:
    core = reset.cold_reset_core(0, 0x1000)
    return fence_ops.execute_fence(core, fence_ops.fence_instruction("FENCE"))


def _data_capability(cursor: int) -> caps.Capability:
    payload = caps.CapabilityPayload(
        cursor=cursor,
        permissions=int(caps.CapabilityPermission.LD | caps.CapabilityPermission.ST),
        flags=int(caps.CapabilityFlag.G),
    ).with_bounds(0, 1 << 48)
    return caps.Capability.valid(payload)
