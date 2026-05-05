"""I15-S02 property-style tests for capability tag integrity."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import capabilities as caps
from cpu_v01 import debug_abi, execution, instructions, litmus, memory_ops
from cpu_v01 import reset, serialization, state
from cpu_v01.cells import CACHE_LINE_CELLS, CAPABILITY_OBJECT_CELLS, CELL_BITS
from cpu_v01.memory import TaggedMemory


DATA_ADDRESS = 0x1000


def capability(
    cursor: int = DATA_ADDRESS,
    *,
    base: int = 0,
    top: int = 1 << 48,
    permissions: int = int(caps.ALL_PERMISSIONS),
    tag: bool = True,
    flags: int = int(caps.CapabilityFlag.G),
    otype: int = caps.OTYPE_UNSEALED,
) -> caps.Capability:
    payload = caps.CapabilityPayload(
        cursor=cursor,
        permissions=permissions,
        otype=otype,
        flags=flags,
    ).with_bounds(base, top)
    return caps.Capability(payload=payload, tag=tag)


def low_integer(payload_cells: tuple[int, ...]) -> int:
    return payload_cells[0] | (payload_cells[1] << CELL_BITS)


def high_integer(payload_cells: tuple[int, ...]) -> int:
    return payload_cells[2] | (payload_cells[3] << CELL_BITS)


def execute_and_commit_memory(core, memory, decoded):
    result = memory_ops.execute_memory(core, memory, decoded)
    if result.is_normal_retire:
        execution.commit_normal_result(core, result, memory)
    return result


class TagIntegrityPropertyTests(unittest.TestCase):
    def test_integer_storage_never_creates_capability_tags_from_payload_bits(self) -> None:
        source = capability(cursor=0x1234, tag=True)
        payload_cells = caps.payload_to_cells(source.payload)

        for slot_base in (DATA_ADDRESS, DATA_ADDRESS + CAPABILITY_OBJECT_CELLS):
            with self.subTest(slot_base=slot_base):
                memory = TaggedMemory()
                memory.st48(slot_base, low_integer(payload_cells))
                memory.st48(slot_base + 2, high_integer(payload_cells))

                loaded = memory.clc(slot_base)
                self.assertEqual(loaded.payload, source.payload)
                self.assertFalse(loaded.tag)
                self.assertFalse(memory.capability_tag(slot_base))

        memory = TaggedMemory()
        memory.csc(DATA_ADDRESS, capability(cursor=0x2222, tag=True))
        memory.write_cell(DATA_ADDRESS + 1, payload_cells[1])
        self.assertFalse(memory.capability_tag(DATA_ADDRESS))

    def test_st48_instruction_clears_but_never_sets_overlapped_tags(self) -> None:
        source = capability(cursor=0x3456, tag=True)
        payload_cells = caps.payload_to_cells(source.payload)
        writes = (
            (0, low_integer(payload_cells)),
            (2, high_integer(payload_cells)),
        )

        for initial_tag in (False, True):
            for offset, value in writes:
                with self.subTest(initial_tag=initial_tag, offset=offset):
                    core = reset.cold_reset_core(0, 0x1000)
                    memory = TaggedMemory()
                    memory.csc(DATA_ADDRESS, capability(cursor=0x2000, tag=initial_tag))
                    core.write_c(
                        1,
                        capability(
                            permissions=int(caps.CapabilityPermission.ST),
                            tag=True,
                        ),
                    )
                    core.write_d(2, offset)
                    core.write_d(3, value)

                    result = memory_ops.execute_memory(
                        core,
                        memory,
                        memory_ops.memory_instruction("ST48", (1, 2, 3)),
                    )

                    self.assertTrue(result.is_normal_retire)
                    self.assertEqual(memory.capability_tag(DATA_ADDRESS), initial_tag)
                    execution.commit_normal_result(core, result, memory)
                    self.assertFalse(memory.capability_tag(DATA_ADDRESS))

    def test_clc_and_csc_copy_existing_tags_exactly(self) -> None:
        for tag in (False, True):
            with self.subTest(tag=tag):
                stored = capability(cursor=0x4567, tag=tag)
                core = reset.cold_reset_core(0, 0x1000)
                memory = TaggedMemory()
                core.write_c(
                    1,
                    capability(
                        permissions=int(
                            caps.CapabilityPermission.LD
                            | caps.CapabilityPermission.LC
                            | caps.CapabilityPermission.ST
                            | caps.CapabilityPermission.SC
                            | caps.CapabilityPermission.SL
                        ),
                    ),
                )
                core.write_c(2, stored)
                core.write_d(3, 0)

                store = execute_and_commit_memory(
                    core,
                    memory,
                    memory_ops.memory_instruction("CSC", (1, 3, 2)),
                )
                self.assertTrue(store.is_normal_retire)
                self.assertEqual(memory.capability_tag(DATA_ADDRESS), tag)

                load = execute_and_commit_memory(
                    core,
                    memory,
                    memory_ops.memory_instruction("CLC", (0, 1, 3)),
                )
                self.assertTrue(load.is_normal_retire)
                self.assertEqual(core.read_c(0), stored)
                self.assertEqual(core.read_c(0).tag, tag)

    def test_serialized_cell_payloads_remain_untagged_without_sidecar(self) -> None:
        source = capability(cursor=0x5678, tag=True)
        payload_cells = caps.payload_to_cells(source.payload)
        payload_octets = serialization.serialize_cells(payload_cells)

        memory = TaggedMemory()
        memory.csc(DATA_ADDRESS, capability(cursor=0x2222, tag=True))
        memory.write_cells(DATA_ADDRESS, serialization.deserialize_cells(payload_octets))

        loaded = memory.clc(DATA_ADDRESS)
        self.assertEqual(loaded.payload, source.payload)
        self.assertFalse(loaded.tag)

        line_cells = [0] * CACHE_LINE_CELLS
        line_cells[4:8] = payload_cells
        line_octets = serialization.serialize_cache_line(tuple(line_cells))
        memory = TaggedMemory()
        memory.write_cells(DATA_ADDRESS, serialization.deserialize_cache_line(line_octets))

        for slot_offset in range(0, CACHE_LINE_CELLS, CAPABILITY_OBJECT_CELLS):
            self.assertFalse(memory.capability_tag(DATA_ADDRESS + slot_offset))
        self.assertEqual(memory.clc(DATA_ADDRESS + 4).payload, source.payload)
        self.assertFalse(memory.clc(DATA_ADDRESS + 4).tag)

    def test_dma_writes_clear_memory_tags_and_invalidation_does_not_forge_tags(self) -> None:
        original = capability(cursor=0x6000, tag=True)
        replacement = capability(cursor=0x7000, tag=True)
        model = litmus.CacheDmaModel(core_count=2)

        model.csc(0, DATA_ADDRESS, original)
        model.cache_clean(DATA_ADDRESS)
        self.assertTrue(model.memory_capability_tag(DATA_ADDRESS))
        self.assertEqual(model.clc(1, DATA_ADDRESS), original)

        model.dma_write_cells(DATA_ADDRESS, caps.payload_to_cells(replacement.payload))
        self.assertFalse(model.memory_capability_tag(DATA_ADDRESS))

        model.cache_inval(DATA_ADDRESS)
        observed = model.clc(1, DATA_ADDRESS)
        self.assertEqual(observed.payload, replacement.payload)
        self.assertFalse(observed.tag)

    def test_cache_integer_writes_and_maintenance_do_not_restore_cleared_tags(self) -> None:
        source = capability(cursor=0x8000, tag=True)
        payload_cells = caps.payload_to_cells(capability(cursor=0x9000).payload)
        writes = (
            (DATA_ADDRESS, low_integer(payload_cells)),
            (DATA_ADDRESS + 2, high_integer(payload_cells)),
        )

        for address, value in writes:
            with self.subTest(address=address):
                model = litmus.CacheDmaModel(core_count=2)
                model.csc(0, DATA_ADDRESS, source)
                model.st48(0, address, value)

                self.assertFalse(model.clc(0, DATA_ADDRESS).tag)
                model.cache_clean(DATA_ADDRESS)
                self.assertFalse(model.memory_capability_tag(DATA_ADDRESS))

                model.cache_cleaninval(DATA_ADDRESS)
                self.assertFalse(model.clc(1, DATA_ADDRESS).tag)

    def test_ccsr_commit_copies_preserve_tags_without_promoting_invalid_caps(self) -> None:
        valid = capability(cursor=0xA000, tag=True)
        invalid = capability(cursor=0xB000, tag=False)

        for name, index in state.SPECIAL_NAME_TO_CCSR_INDEX.items():
            for source in (valid, invalid):
                with self.subTest(name=name, tag=source.tag):
                    core = reset.cold_reset_core(0, 0x1000)
                    result = instructions.DecodedInstruction(
                        "CCSRWR",
                        instructions.InstructionSize.BITS_48,
                    ).normal_retire(
                        instructions.ArchitecturalEffects(
                            ccsr_writes=((index, source),)
                        )
                    )

                    execution.commit_normal_result(core, result)

                    observed = core.read_ccsr(index)
                    self.assertEqual(observed, source)
                    self.assertEqual(observed.tag, source.tag)
                    if source.is_invalid:
                        self.assertFalse(observed.with_tag(True) == core.read_ccsr(index))
                    else:
                        self.assertFalse(observed.with_tag(False) == core.read_ccsr(index))
                    self.assertEqual(core.read_ccsr(index).tag, source.tag)

    def test_debug_observation_exposes_tags_but_cannot_create_them(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        core.lifecycle = state.CoreLifecycle.DEBUG_HALTED
        invalid = capability(cursor=0xC000, tag=False)

        self.assertTrue(debug_abi.direct_register_access_allowed(core.lifecycle))
        for index in range(state.GENERAL_CAPABILITY_REGISTER_COUNT):
            core.write_c(index, invalid)
            view = debug_abi.debug_register_view(f"C{index}")
            observed = core.read_c(view.index)
            self.assertTrue(view.tag_visible)
            self.assertFalse(observed.tag)
            self.assertEqual(core.read_c(index).tag, invalid.tag)

        for name, ccsr_index in state.SPECIAL_NAME_TO_CCSR_INDEX.items():
            core.write_ccsr(ccsr_index, invalid)
            view = debug_abi.debug_register_view(name)
            observed = core.read_ccsr(view.index)
            self.assertTrue(view.tag_visible)
            self.assertFalse(observed.tag)
            self.assertEqual(core.read_ccsr(ccsr_index).tag, invalid.tag)

        for name in ("D0", "SR", "DEBUGCTL"):
            view = debug_abi.debug_register_view(name)
            self.assertFalse(view.tag_visible)
            self.assertFalse(view.slot_visible)


if __name__ == "__main__":
    unittest.main()
