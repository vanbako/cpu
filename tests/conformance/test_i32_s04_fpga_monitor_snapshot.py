"""I32-S04 conformance tests for FPGA monitor debug snapshots."""

from __future__ import annotations

import contextlib
import importlib.util
from io import StringIO
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
TOOL = ROOT / "tools" / "fpga_monitor_snapshot.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_debug_status, fpga_monitor_snapshot, state


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_monitor_snapshot_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaMonitorSnapshotTests(unittest.TestCase):
    def test_monitor_snapshot_self_validation_passes(self) -> None:
        self.assertEqual(fpga_monitor_snapshot.validate_fpga_monitor_snapshot(ROOT), ())

    def test_profile_names_dependencies_and_capture_scope(self) -> None:
        profile = fpga_monitor_snapshot.fpga_monitor_snapshot_profile()

        self.assertEqual(profile.story, "I32-S04")
        self.assertEqual(profile.status, "debug_snapshot_replay_handoff")
        self.assertEqual(profile.monitor_firmware_gate, "python tools\\fpga_monitor_firmware.py --check")
        self.assertEqual(
            profile.debug_abi_gate,
            "python -m unittest tests.conformance.test_i09_s04_debug_abi",
        )
        self.assertEqual(profile.replay_mapper_gate, "python tools\\fpga_replay_mapper.py --check")
        for name in ("D0", "C0", "PCC", "EPCC", "SR", "DEBUGCTL"):
            self.assertIn(name, profile.captured_registers)
        self.assertEqual(profile.memory_window_cells, 4)

    def test_snapshot_captures_registers_ccsr_slots_memory_and_packet(self) -> None:
        snapshot = fpga_monitor_snapshot.capture_monitor_debug_snapshot()

        self.assertEqual(snapshot.story, "I32-S04")
        self.assertEqual(snapshot.lifecycle, state.CoreLifecycle.DEBUG_HALTED.value)
        self.assertEqual(snapshot.pc_slot, 0)
        self.assertTrue(snapshot.integer_registers)
        self.assertTrue(snapshot.capability_registers)
        self.assertTrue(snapshot.ccsr_registers)
        self.assertTrue(snapshot.csr_registers)

        integers = {sample.name: sample for sample in snapshot.integer_registers}
        self.assertIn("D0", integers)
        self.assertGreater(integers["D0"].value, 0)

        capabilities = {sample.name: sample for sample in snapshot.capability_registers}
        self.assertTrue(capabilities["C0"].tag_visible)
        self.assertTrue(capabilities["C0"].tag)
        self.assertTrue(capabilities["C1"].tag_visible)
        self.assertFalse(capabilities["C1"].tag)

        ccsr = {sample.name: sample for sample in snapshot.ccsr_registers}
        self.assertTrue(ccsr["PCC"].slot_visible)
        self.assertEqual(ccsr["PCC"].slot, 0)
        self.assertTrue(ccsr["EPCC"].slot_visible)
        self.assertIn(ccsr["EPCC"].slot, (0, 1))
        self.assertFalse(ccsr["TVC"].slot_visible)
        self.assertIsNone(ccsr["TVC"].slot)

        csr = {sample.name: sample for sample in snapshot.csr_registers}
        self.assertIn("SR", csr)
        self.assertIn("CAUSE", csr)
        self.assertIn("TVAL", csr)
        self.assertIn("DEBUGCTL", csr)

        self.assertEqual(snapshot.memory_window.target_memory, "data_ram")
        self.assertEqual(snapshot.memory_window.cell_count, 4)
        self.assertEqual(len(snapshot.memory_window.cells), 4)
        self.assertFalse(snapshot.memory_window.writable_by_snapshot)
        self.assertFalse(snapshot.memory_window.tag_bits_exposed_to_host)

        self.assertEqual(
            fpga_debug_status.validate_debug_status_packet(snapshot.status_packet),
            (),
        )

    def test_replay_handoff_and_tag_policy_are_preserved(self) -> None:
        snapshot = fpga_monitor_snapshot.capture_monitor_debug_snapshot()

        self.assertEqual(
            len(snapshot.replay_handoff.status_packet_hex),
            fpga_debug_status.STATUS_PACKET_SIZE_BYTES * 2,
        )
        self.assertEqual(
            snapshot.replay_handoff.replay_case_id,
            "core.shell.reset_idle",
        )
        self.assertIn("--case-id core.shell.reset_idle", snapshot.replay_handoff.replay_command)
        self.assertIn("--observed-trace", snapshot.replay_handoff.compare_command)
        self.assertTrue(any("start replay" in line for line in snapshot.replay_handoff.diagnostics))

        self.assertTrue(snapshot.tag_policy.passed)
        self.assertTrue(snapshot.tag_policy.register_tags_reported)
        self.assertTrue(snapshot.tag_policy.ccsr_tags_reported)
        self.assertFalse(snapshot.tag_policy.host_tag_write_enabled)
        self.assertTrue(snapshot.tag_policy.memory_tags_unchanged)
        self.assertEqual(snapshot.tag_policy.write_memory_commands_issued, 0)

    def test_cli_validates_profile_and_snapshot_json(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA monitor snapshot issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I32-S04")
        self.assertIn("captured_registers", parsed)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--snapshot"])

        self.assertEqual(result, 0)
        snapshot = json.loads(stream.getvalue())
        self.assertEqual(snapshot["story"], "I32-S04")
        self.assertEqual(snapshot["lifecycle"], "DEBUG_HALTED")
        self.assertTrue(snapshot["tag_policy"]["passed"])

    def test_documentation_names_snapshot_replay_and_tag_policy(self) -> None:
        text = (
            ROOT / "docs" / "implementation" / "fpga-monitor-debug-snapshot.md"
        ).read_text(encoding="utf-8")

        for token in (
            "Story: I32-S04",
            "python tools\\fpga_monitor_snapshot.py --check",
            "python tools\\fpga_monitor_firmware.py --check",
            "python -m unittest tests.conformance.test_i09_s04_debug_abi",
            "python tools\\fpga_replay_mapper.py --check",
            "DEBUG_HALTED",
            "PCC",
            "EPCC",
            "CCSR",
            "memory window",
            "status packet",
            "replay_command",
            "signature",
            "tag forgery",
            "tag_bits_exposed_to_host",
            "I32-S05",
            "I32-S06",
            "Acceptance Review",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
