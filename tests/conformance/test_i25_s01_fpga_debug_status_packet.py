"""I25-S01 conformance tests for the FPGA debug/status packet."""

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
TOOL = ROOT / "tools" / "fpga_debug_status_packet.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_debug_status


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_debug_status_packet_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaDebugStatusPacketTests(unittest.TestCase):
    def test_debug_status_profile_self_validation_passes(self) -> None:
        self.assertEqual(fpga_debug_status.validate_fpga_debug_status(ROOT), ())

    def test_profile_names_layout_flags_and_states(self) -> None:
        profile = fpga_debug_status.fpga_debug_status_profile()

        self.assertEqual(profile.story, "I25-S01")
        self.assertEqual(profile.board, "Sipeed Tang Mega 138K Dock")
        self.assertEqual(profile.packet_size_bytes, 32)
        self.assertEqual(profile.magic, 0xC501)
        self.assertEqual(profile.version, 1)
        self.assertEqual(profile.byte_order, "little_endian")

        fields = {field.name: field for field in profile.fields}
        self.assertEqual(fields["magic"].offset, 0)
        self.assertEqual(fields["flags"].offset, 4)
        self.assertEqual(fields["slot"].offset, 6)
        self.assertEqual(fields["pc_cell"].offset, 8)
        self.assertEqual(fields["retire_count"].offset, 16)
        self.assertEqual(fields["fault_code"].offset, 20)
        self.assertEqual(fields["trap_cause"].offset, 22)
        self.assertEqual(fields["build_id"].offset, 24)
        self.assertEqual(fields["sequence"].offset, 28)

        flags = {flag.name: flag for flag in profile.flags}
        for name in (
            "reset_asserted",
            "reset_observed",
            "core_idle",
            "retire_valid",
            "fault_valid",
            "pass_led",
            "fail_led",
            "heartbeat",
        ):
            self.assertIn(name, flags)
        self.assertEqual(profile.pass_fail_states[2], "first_pass")
        self.assertEqual(profile.pass_fail_states[3], "failed")
        self.assertTrue(any("retire behavior" in rule for rule in profile.non_interference_rules))

    def test_flag_mask_and_packet_round_trip(self) -> None:
        flags = fpga_debug_status.debug_status_flag_mask(
            "reset_observed",
            "retire_valid",
            "pass_led",
            "heartbeat",
        )
        self.assertEqual(flags, (1 << 1) | (1 << 3) | (1 << 5) | (1 << 7))

        packet = fpga_debug_status.example_debug_status_packet()
        encoded = fpga_debug_status.encode_debug_status_packet(packet)
        decoded = fpga_debug_status.decode_debug_status_packet(encoded)

        self.assertEqual(len(encoded), 32)
        self.assertEqual(decoded, packet)
        self.assertEqual(decoded.pass_fail_state, 2)
        self.assertEqual(decoded.retire_count, 8)
        self.assertEqual(decoded.fault_code, 0)

    def test_packet_validation_rejects_reserved_bits_and_bad_header(self) -> None:
        packet = fpga_debug_status.DebugStatusPacket(
            flags=1 << 12,
            slot=0,
            pass_fail_state=2,
            pc_cell=0x1008,
            retire_count=8,
            fault_code=0,
            trap_cause=0,
            build_id=1,
            sequence=1,
        )

        self.assertIn("flags contain reserved bits", fpga_debug_status.validate_debug_status_packet(packet))

        with self.assertRaises(ValueError):
            fpga_debug_status.encode_debug_status_packet(packet)

        encoded = bytearray(fpga_debug_status.encode_debug_status_packet(fpga_debug_status.example_debug_status_packet()))
        encoded[0] = 0
        with self.assertRaises(ValueError):
            fpga_debug_status.decode_debug_status_packet(bytes(encoded))

        with self.assertRaises(ValueError):
            fpga_debug_status.decode_debug_status_packet(b"\x00")

    def test_cli_validates_json_example_and_decode(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA debug/status packet issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I25-S01")
        self.assertEqual(parsed["packet_size_bytes"], 32)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--example"])

        self.assertEqual(result, 0)
        packet_hex = stream.getvalue().strip()
        self.assertEqual(len(bytes.fromhex(packet_hex)), 32)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--decode-hex", packet_hex])

        self.assertEqual(result, 0)
        decoded = json.loads(stream.getvalue())
        self.assertEqual(decoded["pass_fail_state"], 2)
        self.assertEqual(decoded["retire_count"], 8)

    def test_documentation_names_packet_fields_and_followup_stories(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-debug-status-packet.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I25-S01", text)
        self.assertIn("python tools\\fpga_debug_status_packet.py --check", text)
        self.assertIn("32 bytes", text)
        self.assertIn("0xC501", text)
        self.assertIn("little-endian", text)
        self.assertIn("reset_asserted", text)
        self.assertIn("reset_observed", text)
        self.assertIn("pc_cell", text)
        self.assertIn("slot", text)
        self.assertIn("retire_count", text)
        self.assertIn("fault_code", text)
        self.assertIn("trap_cause", text)
        self.assertIn("pass_fail_state", text)
        self.assertIn("build_id", text)
        self.assertIn("sequence", text)
        self.assertIn("first_pass", text)
        self.assertIn("retire behavior", text)
        self.assertIn("I25-S02", text)
        self.assertIn("I25-S03", text)


if __name__ == "__main__":
    unittest.main()
