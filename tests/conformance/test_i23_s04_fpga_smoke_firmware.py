"""I23-S04 conformance tests for the FPGA smoke firmware path."""

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
TOOL = ROOT / "tools" / "fpga_smoke_firmware.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_smoke


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_smoke_firmware_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaSmokeFirmwareTests(unittest.TestCase):
    def test_fpga_smoke_sources_exist_and_self_validate(self) -> None:
        self.assertEqual(fpga_smoke.validate_fpga_smoke_firmware(ROOT), ())
        for path in fpga_smoke.FPGA_SMOKE_SOURCE_FILES:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).exists())

    def test_smoke_observation_inventory_covers_pass_fail_heartbeat_and_faults(self) -> None:
        observations = {row.name: row for row in fpga_smoke.fpga_smoke_observations()}

        self.assertEqual(fpga_smoke.FPGA_SMOKE_PASS_RETIRE_COUNT, 8)
        self.assertEqual(fpga_smoke.FPGA_SMOKE_CELL, "24'h05B05B")
        self.assertIn("pass_sticky_q", observations["pass_led_o"].source)
        self.assertIn("fault_sticky_q", observations["fail_led_o"].source)
        self.assertEqual(observations["heartbeat_led_o"].source, "debug_retire_sequence[0]")
        self.assertEqual(observations["status_retire_count_o"].source, "debug_retire_sequence[31:0]")
        self.assertEqual(observations["status_fault_code_o"].source, "fault_code_q")

    def test_top_source_defines_fetch_enabled_pass_fail_and_progress_status(self) -> None:
        top = (ROOT / "rtl" / "cpu_v01_fpga_top.sv").read_text(encoding="utf-8")

        for token in (
            "parameter bit ENABLE_FETCH = 1'b1",
            "parameter int FIRST_TEST_PASS_RETIRE_COUNT = 8",
            "FIRST_TEST_PASS_THRESHOLD",
            "pass_sticky_q",
            "assign pass_led_o = pass_sticky_q && !fault_sticky_q",
            "assign fail_led_o = fault_sticky_q",
            "assign heartbeat_led_o = debug_retire_sequence[0]",
            "assign status_retire_count_o = debug_retire_sequence[31:0]",
            "retire_valid && debug_retire_sequence >= FIRST_TEST_PASS_THRESHOLD",
            "fault_code_q <= retire_packet.fault.cause",
        ):
            with self.subTest(token=token):
                self.assertIn(token, top)

    def test_rom_default_image_is_pause_stream_with_init_override(self) -> None:
        memories = (ROOT / "rtl" / "cpu_v01_fpga_memories.sv").read_text(encoding="utf-8")

        self.assertIn("rom_q[i] = 24'h05B05B", memories)
        self.assertIn("$readmemh(INIT_FILE, rom_q)", memories)

    def test_first_testbench_checks_pass_fail_retire_and_heartbeat(self) -> None:
        tb = (ROOT / "rtl" / "cpu_v01_fpga_first_test_tb.sv").read_text(
            encoding="utf-8"
        )

        self.assertIn("module cpu_v01_fpga_first_test_tb", tb)
        self.assertIn("FPGA first-test smoke firmware did not reach pass status", tb)
        self.assertIn("FPGA first-test smoke firmware reported a fault", tb)
        self.assertIn("FPGA first-test smoke firmware did not retire enough PAUSE instructions", tb)
        self.assertIn("FPGA first-test smoke did not expose activity and heartbeat", tb)
        self.assertIn("status_retire_count_o < 32'd8", tb)

    def test_cli_validates_and_renders_smoke_observation_json(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA smoke firmware issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        names = {row["name"] for row in parsed}
        self.assertIn("pass_led_o", names)
        self.assertIn("fail_led_o", names)
        self.assertIn("heartbeat_led_o", names)
        self.assertIn("status_retire_count_o", names)
        self.assertIn("status_fault_code_o", names)

    def test_documentation_artifact_names_sources_commands_and_deferrals(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-smoke-firmware.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I23-S04", text)
        self.assertIn("rtl/cpu_v01_fpga_first_test_tb.sv", text)
        self.assertIn("python tools\\fpga_smoke_firmware.py --check", text)
        self.assertIn("cpu_v01_fpga_first_test_tb", text)
        self.assertIn("PAUSE", text)
        self.assertIn("pass_led_o", text)
        self.assertIn("fail_led_o", text)
        self.assertIn("heartbeat_led_o", text)
        self.assertIn("status_retire_count_o", text)
        self.assertIn("status_fault_code_o", text)
        self.assertIn("I23-S05", text)

    def test_verilator_command_names_smoke_sources(self) -> None:
        command = fpga_smoke.fpga_smoke_verilator_command()

        self.assertIn("--top-module cpu_v01_fpga_first_test_tb", command)
        self.assertIn("rtl/cpu_v01_pkg.sv", command)
        self.assertIn("rtl/cpu_v01_core.sv", command)
        self.assertIn("rtl/cpu_v01_fpga_memories.sv", command)
        self.assertIn("rtl/cpu_v01_fpga_top.sv", command)
        self.assertIn("rtl/cpu_v01_fpga_first_test_tb.sv", command)


if __name__ == "__main__":
    unittest.main()
