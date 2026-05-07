"""I22-S03 conformance tests for integrated core scalar/control execution."""

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
TOOL = ROOT / "tools" / "rtl_core_scalar_control.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import rtl_core_scalar, rtl_scalar_control


def load_tool_module():
    spec = importlib.util.spec_from_file_location("rtl_core_scalar_control_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RtlCoreScalarControlTests(unittest.TestCase):
    def test_rtl_core_scalar_control_sources_exist_and_self_validate(self) -> None:
        self.assertEqual(rtl_core_scalar.validate_rtl_core_scalar_control(ROOT), ())
        for path in rtl_core_scalar.RTL_CORE_SCALAR_SOURCE_FILES:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).exists())

    def test_projection_covers_i21_scalar_control_mnemonics(self) -> None:
        rows = {row.mnemonic: row for row in rtl_core_scalar.integrated_scalar_control_coverage_rows()}

        self.assertEqual(set(rows), set(rtl_scalar_control.scalar_control_mnemonics()))
        self.assertEqual(rows["ADD"].retire_effects, ("integer_write",))
        self.assertEqual(rows["CMP"].retire_effects, ("csr_write:SR",))
        self.assertEqual(rows["BRA"].retire_effects, ("pcc_update",))
        self.assertEqual(rows["BRK"].retire_effects, ("fault:BREAKPOINT",))
        self.assertEqual(rows["PAUSE"].retire_effects, ("normal_retire:no_write",))
        self.assertEqual(set(rows["CSRRD"].size_bits), {24, 48})
        self.assertEqual(rows["CCSRWR"].retire_effects, ("ccsr_write",))

    def test_core_names_architectural_state_execution_and_effect_paths(self) -> None:
        core = (ROOT / "rtl" / "cpu_v01_core.sv").read_text(encoding="utf-8")

        for token in (
            "d_regs [INT_REG_COUNT]",
            "c_regs [CAP_REG_COUNT]",
            "csr_regs [CSR_COUNT]",
            "epcc_q",
            "dsc_q",
            "execute_decoded_packet",
            "commit_integer_write",
            "commit_capability_write",
            "commit_csr_write",
            "commit_ccsr_write",
            "commit_pcc_update",
            "commit_epcc_update",
            "retire_packet_q.redirect_valid <= 1'b1",
            "mark_decoded_fault(EXC_BREAKPOINT, fetch_pc_q)",
            "mark_decoded_fault(EXC_DIVIDE_BY_ZERO, fetch_pc_q)",
            "OPC_CSRRD_48",
            "OPC_CSRWR_48",
            "OPC_CCSRRD_48",
            "OPC_CCSRWR_48",
        ):
            with self.subTest(token=token):
                self.assertIn(token, core)

    def test_scalar_control_testbench_checks_effects_and_first_mismatch_paths(self) -> None:
        tb = (ROOT / "rtl" / "cpu_v01_core_scalar_control_tb.sv").read_text(
            encoding="utf-8"
        )

        for token in (
            "module cpu_v01_core_scalar_control_tb",
            "cpu_v01_core_scalar_control_fixture",
            "CSRRD D1, SR",
            "ADD D2, D1, D1",
            "BEQ 0x008, not taken",
            "CSRWR.L DEBUGCTL, D3",
            "CSRRD.L D4, DEBUGCTL",
            "EPCCRD C2, D2",
            "EPCCWR C2, D2",
            "CCSRWR DSC, C2",
            "CCSRRD C3, DSC",
            "BRK",
            "integrated scalar/control ADD mismatch",
            "integrated scalar/control BRA redirect mismatch",
            "integrated scalar/control CCSRWR mismatch",
            "integrated scalar/control BRK fault mismatch",
        ):
            with self.subTest(token=token):
                self.assertIn(token, tb)

    def test_cli_validates_and_renders_integrated_scalar_control_json(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("RTL integrated core scalar/control issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        by_mnemonic = {row["mnemonic"]: row for row in parsed}
        self.assertIn("ADD", by_mnemonic)
        self.assertIn("BRK", by_mnemonic)
        self.assertEqual(by_mnemonic["BRK"]["retire_effects"], ["fault:BREAKPOINT"])
        self.assertEqual(set(by_mnemonic["CSRRD"]["size_bits"]), {24, 48})

    def test_documentation_artifact_names_sources_commands_and_deferrals(self) -> None:
        text = (
            ROOT
            / "docs"
            / "implementation"
            / "rtl-integrated-core-scalar-control.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Story: I22-S03", text)
        self.assertIn("rtl/cpu_v01_core.sv", text)
        self.assertIn("rtl/cpu_v01_core_scalar_control_tb.sv", text)
        self.assertIn("python tools\\rtl_core_scalar_control.py --check", text)
        self.assertIn("cpu_v01_core_scalar_control_tb", text)
        self.assertIn("execute_decoded_packet", text)
        self.assertIn("EPCCRD", text)
        self.assertIn("EPCCWR", text)
        self.assertIn("BRK", text)
        self.assertIn("I22-S04", text)

    def test_verilator_command_names_integrated_scalar_control_top(self) -> None:
        command = rtl_core_scalar.core_scalar_control_verilator_command()

        self.assertIn("--top-module cpu_v01_core_scalar_control_tb", command)
        self.assertIn("rtl/cpu_v01_core.sv", command)
        self.assertIn("rtl/cpu_v01_core_scalar_control_tb.sv", command)


if __name__ == "__main__":
    unittest.main()
