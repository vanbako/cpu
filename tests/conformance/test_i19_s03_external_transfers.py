"""I19-S03 conformance tests for noncoherent external-agent transfers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import capabilities as caps
from cpu_v01 import external_transfers, instructions, mmu, platform, vm


class ExternalAgentTransferFixtureTests(unittest.TestCase):
    def test_coherent_cpu_to_agent_handoff_requires_fence_clean_fence(self) -> None:
        report = external_transfers.run_external_agent_transfer_fixture()

        self.assertTrue(report.coherent_buffer.allows_payload_transfer)
        self.assertTrue(report.coherent_buffer.requires_cache_maintenance)
        self.assertEqual(
            report.coherent_buffer.ownership_granularity_cells,
            external_transfers.CACHE_LINE_CELLS,
        )
        self.assertEqual(report.cpu_to_agent_steps[0], "CPU_CSC")
        self.assertEqual(report.cpu_to_agent_steps[-1], "OWNER_EXTERNAL_AGENT")
        self.assertEqual(report.external_read_before_clean, (0, 0, 0, 0))
        self.assertEqual(
            report.external_read_after_clean,
            caps.payload_to_cells(report.source_capability.payload),
        )
        self.assertTrue(report.memory_tag_after_clean)

    def test_agent_to_cpu_handoff_invalidates_stale_line_and_clears_tags(self) -> None:
        report = external_transfers.run_external_agent_transfer_fixture()

        self.assertEqual(report.agent_to_cpu_steps[0], "EXTERNAL_WRITE")
        self.assertEqual(report.agent_to_cpu_steps[-1], "OWNER_CPU")
        self.assertEqual(
            report.stale_cpu_capability_before_inval,
            report.source_capability,
        )
        self.assertFalse(report.memory_tag_after_external_write)
        self.assertEqual(
            report.cpu_capability_after_inval.payload,
            report.replacement_capability.payload,
        )
        self.assertFalse(report.cpu_capability_after_inval.tag)
        self.assertEqual(report.final_coherent_owner, external_transfers.BufferOwner.CPU)

    def test_uncacheable_buffer_uses_direct_memory_without_cache_maintenance(self) -> None:
        report = external_transfers.run_external_agent_transfer_fixture()

        self.assertEqual(
            report.uncacheable_buffer.memory_type,
            mmu.MEMORY_TYPE_NORMAL_UNCACHEABLE,
        )
        self.assertTrue(report.uncacheable_buffer.allows_payload_transfer)
        self.assertFalse(report.uncacheable_buffer.requires_cache_maintenance)
        self.assertNotIn("CACHE.CLEAN", report.uncacheable_steps)
        self.assertNotIn("CACHE.INVAL", report.uncacheable_steps)
        self.assertEqual(
            report.uncacheable_capability_after_external_write.payload,
            report.replacement_capability.payload,
        )
        self.assertFalse(report.uncacheable_capability_after_external_write.tag)
        self.assertEqual(
            report.final_uncacheable_owner,
            external_transfers.BufferOwner.CPU,
        )

    def test_device_ordered_policy_rejects_payload_buffer_and_cache_maintenance(self) -> None:
        report = external_transfers.run_external_agent_transfer_fixture()

        self.assertEqual(report.device_buffer.memory_type, mmu.MEMORY_TYPE_DEVICE_ORDERED)
        self.assertFalse(report.device_payload_transfer_allowed)
        self.assertFalse(report.device_buffer.requires_cache_maintenance)
        self.assertTrue(report.device_cache_result.is_fault)
        self.assertEqual(
            report.device_cache_result.fault_packet.cause,
            instructions.ExceptionCause.ACCESS_FAULT,
        )
        device_mapping = vm.VmMapping(physical_page=platform.DEVICE_BASE)
        self.assertEqual(
            report.device_cache_fault_tval,
            device_mapping.physical_address(),
        )

    def test_fences_retire_and_documentation_names_handoff_scope(self) -> None:
        report = external_transfers.run_external_agent_transfer_fixture()

        self.assertTrue(all(result.is_normal_retire for result in report.fence_results))

        text = (
            ROOT / "docs" / "implementation" / "external-agent-transfers.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Story: I19-S03", text)
        self.assertIn("ownership handoff", text)
        self.assertIn("CACHE.CLEAN", text)
        self.assertIn("CACHE.INVAL", text)
        self.assertIn("tag-aware", text)


if __name__ == "__main__":
    unittest.main()
