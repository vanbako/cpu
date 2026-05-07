"""I22-S04 conformance tests for integrated core capability/memory execution."""

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
TOOL = ROOT / "tools" / "rtl_core_cap_mem.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import rtl_cap_mem, rtl_core_cap_mem


def load_tool_module():
    spec = importlib.util.spec_from_file_location("rtl_core_cap_mem_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RtlCoreCapMemTests(unittest.TestCase):
    def test_rtl_core_cap_mem_sources_exist_and_self_validate(self) -> None:
        self.assertEqual(rtl_core_cap_mem.validate_rtl_core_cap_mem(ROOT), ())
        for path in rtl_core_cap_mem.RTL_CORE_CAP_MEM_SOURCE_FILES:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).exists())

    def test_projection_covers_i20_cap_mem_mnemonics(self) -> None:
        rows = rtl_core_cap_mem.integrated_cap_mem_coverage_rows()
        by_mnemonic = {row.mnemonic: row for row in rows}
        source_mnemonics = {projection.mnemonic for projection in rtl_cap_mem.cap_mem_packet_projections()}

        self.assertEqual(set(by_mnemonic), source_mnemonics)
        self.assertEqual(by_mnemonic["CMOVE"].retire_effects, ("capability_write",))
        self.assertEqual(by_mnemonic["CGETADDR"].retire_effects, ("integer_write",))
        self.assertEqual(by_mnemonic["CANDPERM"].retire_effects, ("capability_write",))
        self.assertEqual(by_mnemonic["CSC"].retire_effects, ("memory_effect:CSC", "tag_write:preserve"))
        self.assertEqual(by_mnemonic["ST48"].retire_effects, ("memory_effect:ST48", "tag_write:clear"))
        self.assertEqual(by_mnemonic["LD48"].retire_effects, ("integer_write",))
        invalid = next(row for row in rows if row.case_id == "fault_cases.invalid_tag_csetaddr")
        self.assertEqual(invalid.retire_effects, ("fault:CAPABILITY_TAG_FAULT",))

    def test_core_names_memory_states_ports_and_effect_paths(self) -> None:
        core = (ROOT / "rtl" / "cpu_v01_core.sv").read_text(encoding="utf-8")

        for token in (
            "ST_MEM_DREQ",
            "ST_MEM_DWAIT",
            "ST_MEM_TAG_REQ",
            "ST_MEM_TAG_WAIT",
            "dmem_req_valid = state_q == ST_MEM_DREQ",
            "tagmem_req_valid = state_q == ST_MEM_TAG_REQ",
            "cap_payload_cell",
            "cap_from_cells",
            "cap_contains_range",
            "memory_access_check",
            "prepare_memory_op",
            "start_pending_packet",
            "OPC_LD48_24",
            "OPC_ST48_24",
            "OPC_CLC_24",
            "OPC_CSC_24",
            "OPC_CMOVE_48",
            "OPC_CGETADDR_48",
            "OPC_CSETADDR_48",
            "OPC_CANDPERM_48",
            "MEM_EFFECT_ST48",
            "MEM_EFFECT_CSC",
            "EXC_CAPABILITY_TAG_FAULT",
            "CAPCAUSE_TAG",
        ):
            with self.subTest(token=token):
                self.assertIn(token, core)

    def test_cap_mem_testbench_checks_register_memory_tag_and_fault_paths(self) -> None:
        tb = (ROOT / "rtl" / "cpu_v01_core_cap_mem_tb.sv").read_text(encoding="utf-8")

        for token in (
            "module cpu_v01_core_cap_mem_tb",
            "cpu_v01_core_cap_mem_fixture",
            "CCSRRD C1, PCC",
            "CMOVE C2, C1",
            "CGETADDR D3, C2",
            "CSETADDR C4, C1, D3",
            "CANDPERM C5, C4, D1",
            "CSC C1, D0, C2",
            "CLC C6, C1, D0",
            "ST48 C1, D0, D7",
            "LD48 D8, C1, D0",
            "integrated cap/mem CLC mismatch",
            "integrated cap/mem ST48 mismatch",
            "integrated cap/mem invalid-tag fault mismatch",
        ):
            with self.subTest(token=token):
                self.assertIn(token, tb)

    def test_cli_validates_and_renders_integrated_cap_mem_json(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("RTL integrated core cap/mem issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        by_mnemonic = {row["mnemonic"]: row for row in parsed}
        self.assertIn("CMOVE", by_mnemonic)
        self.assertIn("LD48", by_mnemonic)
        self.assertEqual(by_mnemonic["ST48"]["retire_effects"], ["memory_effect:ST48", "tag_write:clear"])

    def test_documentation_artifact_names_sources_commands_and_deferrals(self) -> None:
        text = (
            ROOT
            / "docs"
            / "implementation"
            / "rtl-integrated-core-cap-mem.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Story: I22-S04", text)
        self.assertIn("rtl/cpu_v01_core.sv", text)
        self.assertIn("rtl/cpu_v01_core_cap_mem_tb.sv", text)
        self.assertIn("python tools\\rtl_core_cap_mem.py --check", text)
        self.assertIn("cpu_v01_core_cap_mem_tb", text)
        self.assertIn("CMOVE", text)
        self.assertIn("LD48", text)
        self.assertIn("ST48", text)
        self.assertIn("CLC", text)
        self.assertIn("CSC", text)
        self.assertIn("invalid-tag", text)
        self.assertIn("I22-S05", text)

    def test_verilator_command_names_integrated_cap_mem_top(self) -> None:
        command = rtl_core_cap_mem.core_cap_mem_verilator_command()

        self.assertIn("--top-module cpu_v01_core_cap_mem_tb", command)
        self.assertIn("rtl/cpu_v01_core.sv", command)
        self.assertIn("rtl/cpu_v01_core_cap_mem_tb.sv", command)


if __name__ == "__main__":
    unittest.main()
