"""I20-S06 conformance tests for capability and memory/tag RTL behavior."""

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
TOOL = ROOT / "tools" / "rtl_cap_mem_slice.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import opcodes, rtl_cap_mem, sv_contract


def load_tool_module():
    spec = importlib.util.spec_from_file_location("rtl_cap_mem_slice_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RtlCapMemSliceTests(unittest.TestCase):
    def test_rtl_cap_mem_sources_exist_and_self_validate(self) -> None:
        self.assertEqual(rtl_cap_mem.validate_rtl_cap_mem_slice(ROOT), ())
        for path in rtl_cap_mem.RTL_CAP_MEM_SOURCE_FILES:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).exists())

    def test_package_exposes_capability_memory_and_tag_retire_fields(self) -> None:
        package = (ROOT / "rtl" / "cpu_v01_pkg.sv").read_text(encoding="utf-8")

        for token in (
            "OPC_CMOVE_48",
            "OPC_CGETADDR_48",
            "OPC_CSETADDR_48",
            "OPC_CANDPERM_48",
            "OPC_LD48_24",
            "OPC_ST48_24",
            "OPC_CLC_24",
            "OPC_CSC_24",
            "EXC_CAPABILITY_TAG_FAULT",
            "CAPCAUSE_TAG",
            "FAULT_CAP_IDX_C1",
            "capability_write_valid",
            "memory_effect_kind",
            "memory_capability_value",
            "tag_write_valid",
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
            {
                "capability_write_valid",
                "capability_write_index",
                "capability_write_value",
                "memory_effect_kind",
                "memory_effect_address",
                "memory_integer_value",
                "memory_capability_value",
                "tag_write_valid",
                "tag_write_value",
            },
        )

    def test_cap_mem_core_names_all_required_operations_and_effect_paths(self) -> None:
        core = (ROOT / "rtl" / "cpu_v01_cap_mem_core.sv").read_text(encoding="utf-8")

        for token in (
            "ST_CMOVE",
            "ST_CGETADDR",
            "ST_CSETADDR",
            "ST_CANDPERM",
            "ST_CSC",
            "ST_CLC",
            "ST_ST48",
            "ST_LD48",
            "ST_INVALID_TAG_FAULT",
            "cap_with_cursor",
            "cap_with_permissions",
            "memory_cap_slot_q <= c_regs[2]",
            "memory_tag_q <= c_regs[2].tag",
            "memory_tag_q <= 1'b0",
            "retire_packet_q.capability_write_value",
            "retire_packet_q.memory_effect_kind <= MEM_EFFECT_CSC",
            "retire_packet_q.memory_effect_kind <= MEM_EFFECT_ST48",
            "retire_packet_q.fault.cause <= EXC_CAPABILITY_TAG_FAULT",
        ):
            with self.subTest(token=token):
                self.assertIn(token, core)

    def test_cap_mem_testbench_checks_register_memory_tag_and_fault_results(self) -> None:
        tb = (ROOT / "rtl" / "cpu_v01_cap_mem_tb.sv").read_text(encoding="utf-8")

        self.assertIn("CMOVE/CGETADDR smoke result mismatch", tb)
        self.assertIn("CSETADDR/CANDPERM smoke result mismatch", tb)
        self.assertIn("ST48/LD48 tag-clear smoke result mismatch", tb)
        self.assertIn("invalid-tag fault smoke result mismatch", tb)
        self.assertIn("packet.fault.cause != EXC_CAPABILITY_TAG_FAULT", tb)

    def test_projection_matches_golden_capability_memory_and_fault_cases(self) -> None:
        projections = rtl_cap_mem.cap_mem_packet_projections()
        by_mnemonic = {projection.mnemonic: projection for projection in projections}

        self.assertEqual(by_mnemonic["CMOVE"].opcode_id, opcodes.opcode_form_for("CMOVE").opcode_id)
        self.assertEqual(by_mnemonic["CMOVE"].capability_write_register, "C2")
        self.assertTrue(by_mnemonic["CMOVE"].capability_write_tag)
        self.assertEqual(by_mnemonic["CGETADDR"].integer_write_register, "D3")
        self.assertEqual(by_mnemonic["CGETADDR"].integer_write_value, 0x2200)
        normal_csetaddr = next(
            projection
            for projection in projections
            if projection.mnemonic == "CSETADDR" and projection.normal_valid
        )
        self.assertEqual(normal_csetaddr.capability_write_cursor, 0x2080)
        self.assertEqual(by_mnemonic["CANDPERM"].capability_write_permissions, 1)
        self.assertEqual(by_mnemonic["CSC"].memory_effect_kind, "CSC")
        self.assertTrue(by_mnemonic["CSC"].memory_tag_write)
        self.assertEqual(by_mnemonic["ST48"].memory_effect_kind, "ST48")
        self.assertFalse(by_mnemonic["ST48"].memory_tag_write)
        self.assertEqual(by_mnemonic["LD48"].integer_write_value, 0x123456789ABC)

        invalid = next(
            projection
            for projection in projections
            if projection.case_id == "fault_cases.invalid_tag_csetaddr"
        )
        self.assertFalse(invalid.normal_valid)
        self.assertEqual(invalid.fault_cause, "CAPABILITY_TAG_FAULT")
        self.assertEqual(invalid.capcause, "TAG")
        self.assertEqual(invalid.fault_cap_idx, "C1")

    def test_cli_validates_and_renders_cap_mem_projection_json(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("RTL cap/mem slice issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertIn("CMOVE", {packet["mnemonic"] for packet in parsed})
        self.assertIn("LD48", {packet["mnemonic"] for packet in parsed})

    def test_documentation_artifact_names_sources_and_commands(self) -> None:
        text = (ROOT / "docs" / "implementation" / "rtl-capability-memory-slice.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I20-S06", text)
        self.assertIn("rtl/cpu_v01_cap_mem_core.sv", text)
        self.assertIn("python tools\\rtl_cap_mem_slice.py --check", text)
        self.assertIn("CMOVE", text)
        self.assertIn("invalid-tag faults", text)


if __name__ == "__main__":
    unittest.main()
