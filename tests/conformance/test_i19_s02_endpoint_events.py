"""I19-S02 conformance tests for endpoint event and interrupt routing."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import csrs, endpoint_events, firmware, kernel, startup


class EndpointEventRoutingFixtureTests(unittest.TestCase):
    def test_fixture_starts_secondary_and_routes_three_sources_to_each_core(self) -> None:
        report = endpoint_events.run_endpoint_interrupt_routing_fixture()

        self.assertTrue(report.start_result.accepted)
        self.assertEqual(report.start_result.failure_code, startup.StartupFailureCode.NONE)
        self.assertEqual(report.started_coreid, 1)

        expected_order = (
            kernel.InterruptSource.EXTERNAL,
            kernel.InterruptSource.SOFTWARE_IPI,
            kernel.InterruptSource.TIMER,
        )
        self.assertEqual(dict(report.priority_orders), {0: expected_order, 1: expected_order})
        self.assertEqual(dict(report.final_selected_sources), {0: None, 1: None})
        self.assertEqual(len(report.observations_for_core(0)), 3)
        self.assertEqual(len(report.observations_for_core(report.started_coreid)), 3)

    def test_external_event_uses_fabric_ingress_and_external_vector(self) -> None:
        controller = endpoint_events.EndpointEventController()
        boot_event = controller.route_external_event(
            0,
            ingress=endpoint_events.EndpointIngress.FABRIC0,
        )
        secondary_event = controller.route_external_event(
            1,
            ingress=endpoint_events.EndpointIngress.FABRIC1,
        )

        self.assertEqual(boot_event.ingress, endpoint_events.EndpointIngress.FABRIC0)
        self.assertEqual(secondary_event.ingress, endpoint_events.EndpointIngress.FABRIC1)
        self.assertTrue(controller.external_pending(0))
        self.assertTrue(controller.external_pending(1))

        report = endpoint_events.run_endpoint_interrupt_routing_fixture()
        external_observations = [
            observation
            for observation in report.observations
            if observation.source is kernel.InterruptSource.EXTERNAL
        ]

        self.assertEqual(len(external_observations), 2)
        for observation in external_observations:
            self.assertEqual(
                observation.vector_cursor,
                firmware.ROM_TRAP_VECTOR_CELL + 12,
            )
            self.assertEqual(
                observation.saved_frame.cause,
                kernel.InterruptSource.EXTERNAL.cause_value,
            )
            self.assertFalse(observation.external_pending_after_ack)

    def test_ipi_and_timer_acknowledgement_clear_only_their_pending_sources(self) -> None:
        report = endpoint_events.run_endpoint_interrupt_routing_fixture()

        for core_id in (0, report.started_coreid):
            observations = report.observations_for_core(core_id)
            external, ipi, timer = observations

            self.assertTrue(
                external.pending_before_delivery
                & (1 << kernel.InterruptSource.EXTERNAL.bit)
            )
            self.assertFalse(
                external.pending_after_ack
                & (1 << kernel.InterruptSource.EXTERNAL.bit)
            )
            self.assertTrue(
                ipi.pending_before_delivery
                & (1 << kernel.InterruptSource.SOFTWARE_IPI.bit)
            )
            self.assertFalse(
                ipi.pending_after_ack
                & (1 << kernel.InterruptSource.SOFTWARE_IPI.bit)
            )
            self.assertTrue(
                timer.pending_before_delivery
                & (1 << kernel.InterruptSource.TIMER.bit)
            )
            self.assertFalse(timer.pending_after_ack & (1 << kernel.InterruptSource.TIMER.bit))

    def test_delivery_saves_frame_and_returns_with_iret_to_each_core_context(self) -> None:
        report = endpoint_events.run_endpoint_interrupt_routing_fixture()

        for observation in report.observations:
            self.assertTrue(observation.entry.entered)
            self.assertTrue(observation.iret_result.is_normal_retire)
            self.assertEqual(observation.entry.source, observation.source)
            self.assertEqual(observation.saved_frame.cause, observation.source.cause_value)
            self.assertEqual(observation.saved_frame.tval, 0)

        for core_id in (0, report.started_coreid):
            core = report.cores[core_id]
            self.assertTrue(core.read_csr(csrs.CSR_SR) & (1 << csrs.SR_IE_BIT))
            self.assertFalse(core.read_csr(csrs.CSR_SR) & (1 << csrs.SR_EXL_BIT))
            self.assertEqual(core.read_csr(csrs.CSR_IPENDING), 0)

    def test_documentation_artifact_names_topology_neutral_routing_scope(self) -> None:
        text = (
            ROOT / "docs" / "implementation" / "endpoint-event-routing.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Story: I19-S02", text)
        self.assertIn("point-to-point", text)
        self.assertIn("software IPI", text)
        self.assertIn("acknowledgement", text)
        self.assertNotIn("shared bus", text.lower())


if __name__ == "__main__":
    unittest.main()
