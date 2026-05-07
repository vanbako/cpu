"""I22-S01 conformance tests for the integrated RTL core shell."""

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
TOOL = ROOT / "tools" / "rtl_core_shell.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import rtl_core


def load_tool_module():
    spec = importlib.util.spec_from_file_location("rtl_core_shell_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RtlCoreShellTests(unittest.TestCase):
    def test_rtl_core_shell_sources_exist_and_self_validate(self) -> None:
        self.assertEqual(rtl_core.validate_rtl_core_shell(ROOT), ())
        for path in rtl_core.RTL_CORE_SHELL_SOURCE_FILES:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).exists())

    def test_port_projection_covers_top_level_interface_groups(self) -> None:
        ports = rtl_core.core_shell_ports()
        by_name = {port.name: port for port in ports}

        for group in (
            "clock_reset",
            "instruction_memory",
            "data_memory",
            "tag_memory",
            "events",
            "debug",
            "retire",
        ):
            with self.subTest(group=group):
                self.assertIn(group, {port.group for port in ports})

        self.assertEqual(by_name["imem_req_valid"].idle_value, "0")
        self.assertEqual(by_name["dmem_req_valid"].idle_value, "0")
        self.assertEqual(by_name["tagmem_req_valid"].idle_value, "0")
        self.assertEqual(by_name["retire_valid"].idle_value, "0")
        self.assertEqual(by_name["debug_sr"].idle_value, "0xC0")
        self.assertEqual(by_name["debug_pcc"].type_name, "cap_t")
        self.assertEqual(by_name["retire_packet"].type_name, "retire_packet_t")

    def test_core_source_names_final_ports_reset_and_idle_drives(self) -> None:
        core = (ROOT / "rtl" / "cpu_v01_core.sv").read_text(encoding="utf-8")

        for token in (
            "module cpu_v01_core",
            "RESET_VECTOR",
            "imem_req_valid",
            "imem_req_addr",
            "dmem_req_wdata",
            "tagmem_req_slot_addr",
            "external_event_valid",
            "debug_halt_request",
            "retire_packet_t",
            "debug_pcc",
            "debug_retire_sequence",
            "SR_RESET_VALUE = 48'h0000_0000_00C0",
            "assign imem_req_valid = 1'b0",
            "assign imem_rsp_ready = 1'b0",
            "assign dmem_req_valid = 1'b0",
            "assign tagmem_req_valid = 1'b0",
            "assign imem_req_addr = pcc_q.payload.cursor",
            "pcc_q <= reset_pcc(RESET_VECTOR)",
            "retire_packet_q <= '0",
        ):
            with self.subTest(token=token):
                self.assertIn(token, core)

    def test_testbench_checks_no_program_reset_idle_behavior(self) -> None:
        tb = (ROOT / "rtl" / "cpu_v01_core_shell_tb.sv").read_text(
            encoding="utf-8"
        )

        self.assertIn("integrated core shell did not expose idle reset observation", tb)
        self.assertIn("integrated core shell did not keep all request and retire ports idle", tb)
        self.assertIn("integrated core shell reset PCC/SR observation mismatch", tb)
        self.assertIn("imem_req_addr != 48'h0000_0000_1000", tb)
        self.assertIn("debug_pcc.payload.permissions != 8'd4", tb)
        self.assertIn("debug_sr != 48'h0000_0000_00C0", tb)

    def test_cli_validates_and_renders_core_shell_projection_json(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("RTL integrated core shell issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        names = {row["name"] for row in parsed}
        self.assertIn("imem_req_valid", names)
        self.assertIn("dmem_req_valid", names)
        self.assertIn("tagmem_req_valid", names)
        self.assertIn("retire_packet", names)
        self.assertIn("debug_pcc", names)

    def test_documentation_artifact_names_sources_commands_and_deferrals(self) -> None:
        text = (ROOT / "docs" / "implementation" / "rtl-integrated-core-shell.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I22-S01", text)
        self.assertIn("rtl/cpu_v01_core.sv", text)
        self.assertIn("rtl/cpu_v01_core_shell_tb.sv", text)
        self.assertIn("python tools\\rtl_core_shell.py --check", text)
        self.assertIn("cpu_v01_core_shell_tb", text)
        self.assertIn("no-program", text)
        self.assertIn("I22-S02", text)
        self.assertIn("point-to-point fabric", text)


if __name__ == "__main__":
    unittest.main()
