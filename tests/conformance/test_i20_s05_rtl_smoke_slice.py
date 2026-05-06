"""I20-S05 conformance tests for the first SystemVerilog smoke slice."""

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
TOOL = ROOT / "tools" / "rtl_smoke_slice.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import opcodes, rtl_smoke, sv_contract


def load_tool_module():
    spec = importlib.util.spec_from_file_location("rtl_smoke_slice_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RtlSmokeSliceTests(unittest.TestCase):
    def test_rtl_smoke_sources_exist_and_self_validate(self) -> None:
        self.assertEqual(rtl_smoke.validate_rtl_smoke_slice(ROOT), ())
        for path in rtl_smoke.RTL_SMOKE_SOURCE_FILES:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).exists())

    def test_package_retire_packet_matches_first_slice_contract_fields(self) -> None:
        package = (ROOT / "rtl" / "cpu_v01_pkg.sv").read_text(encoding="utf-8")

        for token in (
            "package cpu_v01_pkg",
            "localparam int CELL_BITS = 24",
            "localparam logic [OPCODE_ID_BITS-1:0] OPC_ADD_24 = 8'h12",
            "typedef struct packed",
            "fault_packet_t",
            "retire_packet_t",
            "integer_write_valid",
            "integer_write_index",
            "integer_write_value",
        ):
            with self.subTest(token=token):
                self.assertIn(token, package)

        retire_fields = {
            field.name
            for struct in sv_contract.systemverilog_contract().structs
            if struct.name == "retire_packet_t"
            for field in struct.fields
        }
        self.assertGreaterEqual(
            retire_fields,
            {"integer_write_valid", "integer_write_index", "integer_write_value"},
        )

    def test_smoke_core_names_reset_add_slot_and_placement_fault_logic(self) -> None:
        core = (ROOT / "rtl" / "cpu_v01_smoke_core.sv").read_text(encoding="utf-8")

        for token in (
            "module cpu_v01_smoke_core",
            "RESET_VECTOR",
            "FORCE_ILLEGAL_SLOT1",
            "slot_q != SLOT_0",
            "d_regs[0] <= 48'h0000_0000_0010",
            "d_regs[1] <= 48'h0000_0000_0020",
            "wire int_reg_t add_result = d_regs[ra] + d_regs[rb]",
            "d_regs[rd] <= add_result",
            "retire_packet_q.integer_write_value <= add_result",
            "retire_packet_q.fault.cause <= EXC_ALIGN_FAULT",
            "pc_q <= pc_q + 48'd1",
        ):
            with self.subTest(token=token):
                self.assertIn(token, core)

    def test_smoke_testbench_checks_normal_and_fault_paths(self) -> None:
        tb = (ROOT / "rtl" / "cpu_v01_smoke_tb.sv").read_text(encoding="utf-8")

        self.assertIn("normal_core", tb)
        self.assertIn("placement_core", tb)
        self.assertIn("normal_packet.integer_write_value != 48'h0000_0000_0030", tb)
        self.assertIn("placement_packet.fault.cause != EXC_ALIGN_FAULT", tb)
        self.assertIn("$fatal", tb)

    def test_smoke_slice_projection_matches_golden_reset_and_placement_cases(self) -> None:
        projections = rtl_smoke.smoke_slice_packet_projections()

        self.assertEqual(
            tuple(projection.case_id for projection in projections),
            ("reset_smoke.add_slot0", "fault_cases.slot1_48bit_placement"),
        )
        reset, placement = projections
        self.assertEqual(reset.pc_cell, 0x1000)
        self.assertEqual(reset.slot, 0)
        self.assertEqual(reset.opcode_id, opcodes.opcode_form_for("ADD").opcode_id)
        self.assertTrue(reset.normal_valid)
        self.assertEqual(reset.integer_write_register, "D2")
        self.assertEqual(reset.integer_write_value, 0x30)
        self.assertEqual(placement.pc_cell, 0x1700)
        self.assertEqual(placement.slot, 1)
        self.assertFalse(placement.normal_valid)
        self.assertEqual(placement.fault_cause, "ALIGN_FAULT")
        self.assertEqual(placement.result_stage, "PD")

    def test_cli_validates_and_renders_smoke_projection_json(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("RTL smoke slice issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed[0]["case_id"], "reset_smoke.add_slot0")
        self.assertEqual(parsed[0]["integer_write_value"], 0x30)

    def test_documentation_artifact_names_sources_and_commands(self) -> None:
        text = (ROOT / "docs" / "implementation" / "rtl-smoke-slice.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I20-S05", text)
        self.assertIn("rtl/cpu_v01_smoke_core.sv", text)
        self.assertIn("python tools\\rtl_smoke_slice.py --check", text)
        self.assertIn("reset_smoke.add_slot0", text)
        self.assertIn("fault_cases.slot1_48bit_placement", text)


if __name__ == "__main__":
    unittest.main()
