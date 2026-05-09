"""I25-S04 conformance tests for FPGA capture replay mapping."""

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
TOOL = ROOT / "tools" / "fpga_replay_mapper.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_debug_status, fpga_replay_mapper, instructions


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_replay_mapper_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def packet_hex(packet: fpga_debug_status.DebugStatusPacket) -> str:
    return fpga_debug_status.encode_debug_status_packet(packet).hex()


class FpgaReplayMapperTests(unittest.TestCase):
    def test_replay_mapper_self_validation_passes(self) -> None:
        self.assertEqual(fpga_replay_mapper.validate_fpga_replay_mapper(ROOT), ())

    def test_profile_names_prerequisites_and_required_commands(self) -> None:
        profile = fpga_replay_mapper.fpga_replay_mapper_profile()

        self.assertEqual(profile.story, "I25-S04")
        self.assertEqual(profile.packet_gate, "python tools\\fpga_debug_status_packet.py --check")
        self.assertEqual(profile.uart_gate, "python tools\\fpga_uart_status_streamer.py --check")
        self.assertIn("verilator_diff_harness.py", profile.regression_gate)
        self.assertIn("python tools\\fpga_bringup_runbook.py --check", profile.bringup_gate)
        self.assertIn("fault_code", profile.required_capture_fields)
        self.assertTrue(any("--observed-trace" in command for command in profile.output_commands))

    def test_first_pass_packet_maps_to_fast_integrated_scalar_replay(self) -> None:
        mapping = fpga_replay_mapper.example_replay_mapping()

        self.assertEqual(mapping.pass_fail_state, "first_pass")
        self.assertEqual(mapping.candidates[0].case_id, "core.scalar.integer_ops_add_mul")
        self.assertIn("pass_led", mapping.flag_names)
        self.assertIn("--case-id core.scalar.integer_ops_add_mul", mapping.candidates[0].replay_command)
        self.assertIn("observed-trace", mapping.candidates[0].compare_command)

    def test_fault_packets_map_to_specific_integrated_or_golden_cases(self) -> None:
        align_packet = fpga_debug_status.DebugStatusPacket(
            flags=fpga_debug_status.debug_status_flag_mask("reset_observed", "fault_valid", "fail_led"),
            slot=1,
            pass_fail_state=3,
            pc_cell=0x1001,
            retire_count=1,
            fault_code=int(instructions.ExceptionCause.ALIGN_FAULT),
            trap_cause=int(instructions.ExceptionCause.ALIGN_FAULT),
            build_id=0x2501C0DE,
            sequence=7,
        )
        align_mapping = fpga_replay_mapper.map_debug_status_packet(align_packet)
        self.assertEqual(align_mapping.candidates[0].case_id, "core.fetch_decode.slot1_48bit_placement")
        self.assertTrue(any(candidate.case_id == "fault_cases.slot1_48bit_placement" for candidate in align_mapping.candidates))

        cap_packet = fpga_debug_status.DebugStatusPacket(
            flags=fpga_debug_status.debug_status_flag_mask("reset_observed", "fault_valid", "fail_led"),
            slot=0,
            pass_fail_state=3,
            pc_cell=0x1010,
            retire_count=4,
            fault_code=int(instructions.ExceptionCause.CAPABILITY_TAG_FAULT),
            trap_cause=int(instructions.ExceptionCause.CAPABILITY_TAG_FAULT),
            build_id=0x2501C0DE,
            sequence=8,
        )
        cap_mapping = fpga_replay_mapper.map_debug_status_packet(cap_packet)
        self.assertEqual(cap_mapping.candidates[0].case_id, "core.cap_mem.memory_tag_ops")
        self.assertTrue(any(candidate.case_id == "fault_cases.invalid_tag_csetaddr" for candidate in cap_mapping.candidates))

        page_packet = fpga_debug_status.DebugStatusPacket(
            flags=fpga_debug_status.debug_status_flag_mask("reset_observed", "fault_valid", "fail_led"),
            slot=0,
            pass_fail_state=3,
            pc_cell=0x1800,
            retire_count=6,
            fault_code=int(instructions.ExceptionCause.PAGE_FAULT),
            trap_cause=int(instructions.ExceptionCause.PAGE_FAULT),
            build_id=0x2501C0DE,
            sequence=9,
        )
        page_mapping = fpga_replay_mapper.map_debug_status_packet(page_packet)
        self.assertEqual(page_mapping.candidates[0].case_id, "core.mmu_tlb.translation_sfence")

    def test_cli_validates_profile_and_maps_packet_hex(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA replay mapper issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I25-S04")
        self.assertIn("heuristics", parsed)

        packet = fpga_debug_status.example_debug_status_packet()
        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--map-hex", packet_hex(packet)])

        self.assertEqual(result, 0)
        mapped = json.loads(stream.getvalue())
        self.assertEqual(mapped["candidates"][0]["case_id"], "core.scalar.integer_ops_add_mul")
        self.assertIn("first-mismatch", " ".join(mapped["diagnostics"]))

    def test_documentation_names_cases_commands_and_diagnostics(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-replay-mapper.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I25-S04", text)
        self.assertIn("python tools\\fpga_replay_mapper.py --check", text)
        self.assertIn("python tools\\fpga_debug_status_packet.py --decode-hex", text)
        self.assertIn("python tools\\fpga_replay_mapper.py --map-hex", text)
        self.assertIn("python tools\\verilator_diff_harness.py --case-id", text)
        self.assertIn("core.fetch_decode.slot1_48bit_placement", text)
        self.assertIn("core.scalar.integer_ops_add_mul", text)
        self.assertIn("core.cap_mem.memory_tag_ops", text)
        self.assertIn("core.control_trap.sys_iret", text)
        self.assertIn("core.mmu_tlb.translation_sfence", text)
        self.assertIn("fault_cases.divide_by_zero", text)
        self.assertIn("first-mismatch", text)
        self.assertIn("observed-trace", text)
        self.assertIn("UART", text)
        self.assertIn("GAO/ILA", text)


if __name__ == "__main__":
    unittest.main()
