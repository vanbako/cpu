"""I19-S04 point-to-point fabric integration litmus tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import endpoint_events, external_transfers, fabric_litmus, firmware
from cpu_v01 import kernel, state


class PointToPointFabricIntegrationLitmusTests(unittest.TestCase):
    def test_four_core_startup_and_logical_link_event_delivery(self) -> None:
        report = fabric_litmus.run_point_to_point_fabric_litmus_suite()

        self.assertEqual(report.started_coreids, (1, 2, 3))
        self.assertTrue(all(result.accepted for result in report.startup_results))
        self.assertEqual(report.cores[0].lifecycle, state.CoreLifecycle.RUNNING)
        for core_id in report.started_coreids:
            self.assertEqual(report.cores[core_id].lifecycle, state.CoreLifecycle.STARTED)

        self.assertEqual(
            tuple(link.ingress for link in report.links),
            (
                endpoint_events.EndpointIngress.FABRIC0,
                endpoint_events.EndpointIngress.LEFT_PEER,
                endpoint_events.EndpointIngress.RIGHT_PEER,
                endpoint_events.EndpointIngress.FABRIC1,
            ),
        )
        self.assertTrue(report.all_interrupts_returned)
        self.assertEqual(len(report.event_observations), fabric_litmus.FABRIC_CORE_COUNT)
        for observation in report.event_observations:
            self.assertEqual(
                observation.selected_source,
                kernel.InterruptSource.EXTERNAL,
            )
            self.assertEqual(
                observation.vector_cursor,
                firmware.ROM_TRAP_VECTOR_CELL + 12,
            )
            self.assertEqual(
                observation.saved_cause,
                kernel.InterruptSource.EXTERNAL.cause_value,
            )
            self.assertFalse(observation.external_pending_after_ack)

    def test_shared_memory_fences_make_all_core_writes_visible(self) -> None:
        report = fabric_litmus.run_point_to_point_fabric_litmus_suite()
        expected = tuple(
            0x1904_0000 + core_id
            for core_id in range(fabric_litmus.FABRIC_CORE_COUNT)
        )

        self.assertEqual(report.shared_memory.visible_before_fences, (0, 0, 0, 0))
        self.assertEqual(report.shared_memory.final_values, expected)
        self.assertEqual(
            report.shared_memory.post_fence_reads,
            tuple(expected for _ in range(fabric_litmus.FABRIC_CORE_COUNT)),
        )

    def test_llsc_contention_has_one_winner_and_three_failed_stores(self) -> None:
        report = fabric_litmus.run_point_to_point_fabric_litmus_suite()
        llsc = report.llsc_contention

        self.assertEqual(llsc.loaded_values, (0, 0, 0, 0))
        self.assertEqual(llsc.reservation_valid_after_ll, (True, True, True, True))
        self.assertEqual(llsc.sc_results, (0, 1, 1, 1))
        self.assertEqual(llsc.final_lock_value, 1)
        self.assertEqual(llsc.reservation_valid_after_sc, (False, False, False, False))

    def test_coherent_tag_visibility_and_external_agent_ordering_compose(self) -> None:
        report = fabric_litmus.run_point_to_point_fabric_litmus_suite()

        self.assertTrue(report.tag_visibility.capability_visible_to_peer)
        self.assertFalse(report.tag_visibility.tag_after_integer_store)
        self.assertEqual(report.tag_visibility.first_word_after_integer_store, 0x55AA)

        transfer = report.external_transfer
        self.assertEqual(
            transfer.final_coherent_owner,
            external_transfers.BufferOwner.CPU,
        )
        self.assertEqual(
            transfer.final_uncacheable_owner,
            external_transfers.BufferOwner.CPU,
        )
        self.assertFalse(transfer.cpu_capability_after_inval.tag)
        self.assertTrue(all(result.is_normal_retire for result in transfer.fence_results))

    def test_documentation_artifact_names_fabric_litmus_scope(self) -> None:
        text = (
            ROOT / "docs" / "implementation" / "point-to-point-fabric-litmus.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Story: I19-S04", text)
        self.assertIn("four-core startup", text)
        self.assertIn("LL/SC contention", text)
        self.assertIn("coherence/tag visibility", text)
        self.assertIn("external-agent ordering", text)


if __name__ == "__main__":
    unittest.main()
