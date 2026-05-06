"""I21-S01 conformance tests for scalar/control RTL coverage."""

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
TOOL = ROOT / "tools" / "rtl_scalar_control_slice.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import integer, opcodes, rtl_scalar_control


def load_tool_module():
    spec = importlib.util.spec_from_file_location("rtl_scalar_control_slice_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RtlScalarControlSliceTests(unittest.TestCase):
    def test_rtl_scalar_control_sources_exist_and_self_validate(self) -> None:
        self.assertEqual(rtl_scalar_control.validate_rtl_scalar_control_slice(ROOT), ())
        for path in rtl_scalar_control.RTL_SCALAR_CONTROL_SOURCE_FILES:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).exists())

    def test_projection_covers_expected_non_mmu_non_atomic_mnemonics(self) -> None:
        rows = rtl_scalar_control.scalar_control_coverage_rows()
        by_mnemonic = {row.mnemonic: row for row in rows}

        for mnemonic in integer.MANDATORY_INTEGER_MNEMONICS:
            with self.subTest(mnemonic=mnemonic):
                self.assertIn(mnemonic, by_mnemonic)
                self.assertEqual(by_mnemonic[mnemonic].family, "integer")

        for mnemonic in (
            "BRA",
            "BCC",
            "JMP",
            "BRK",
            "EPCCRD",
            "EPCCWR",
            "PAUSE",
            "CSRRD",
            "CSRWR",
            "CSRSET",
            "CSRCLR",
            "CCSRRD",
            "CCSRWR",
        ):
            with self.subTest(mnemonic=mnemonic):
                self.assertIn(mnemonic, by_mnemonic)

        covered = set(by_mnemonic)
        for mnemonic in rtl_scalar_control.DEFERRED_MNEMONICS:
            with self.subTest(deferred=mnemonic):
                self.assertNotIn(mnemonic, covered)

    def test_projection_tracks_opcode_table_forms_and_effect_families(self) -> None:
        by_mnemonic = {
            row.mnemonic: row for row in rtl_scalar_control.scalar_control_coverage_rows()
        }

        for mnemonic, row in by_mnemonic.items():
            forms = opcodes.opcode_forms_for(mnemonic)
            with self.subTest(mnemonic=mnemonic):
                self.assertEqual(row.opcode_ids, tuple(form.opcode_id for form in forms))
                self.assertEqual(row.size_bits, tuple(form.size.bits for form in forms))
                self.assertGreater(len(row.rtl_states), 0)
                self.assertGreater(len(row.retire_effects), 0)

        self.assertEqual(by_mnemonic["BRK"].retire_effects, ("fault:BREAKPOINT",))
        self.assertEqual(by_mnemonic["EPCCWR"].retire_effects, ("epcc_update",))
        self.assertEqual(by_mnemonic["CCSRWR"].retire_effects, ("ccsr_write",))
        self.assertEqual(set(by_mnemonic["CSRRD"].size_bits), {24, 48})
        self.assertEqual(set(by_mnemonic["CSRCLR"].size_bits), {24, 48})

    def test_package_exposes_scalar_control_csr_and_ccsr_constants(self) -> None:
        package = (ROOT / "rtl" / "cpu_v01_pkg.sv").read_text(encoding="utf-8")

        for token in (
            "OPC_CPY_24",
            "OPC_BCLR_24",
            "OPC_BRA_24",
            "OPC_BCC_24",
            "OPC_JMP_24",
            "OPC_BRK_12",
            "OPC_EPCCRD_24",
            "OPC_EPCCWR_24",
            "OPC_PAUSE_12",
            "OPC_CSRRD_24",
            "OPC_CSRRD_48",
            "OPC_CSRCLR_24",
            "OPC_CSRCLR_48",
            "OPC_CCSRRD_48",
            "OPC_CCSRWR_48",
            "EXC_BREAKPOINT",
            "CSR_SCRATCH",
            "CSR_DEBUGCTL",
            "CCSR_PCC",
            "CCSR_DSC",
            "CCSR_EPCC",
        ):
            with self.subTest(token=token):
                self.assertIn(token, package)

    def test_scalar_control_core_names_states_and_retire_effect_paths(self) -> None:
        core = (ROOT / "rtl" / "cpu_v01_scalar_control_core.sv").read_text(
            encoding="utf-8"
        )

        for token in (
            "ST_CPY",
            "ST_MUL",
            "ST_DIV",
            "ST_BCLR",
            "ST_BRA",
            "ST_BCC_TAKEN",
            "ST_BCC_NOT_TAKEN",
            "ST_JMP",
            "ST_EPCCRD",
            "ST_EPCCWR",
            "ST_PAUSE",
            "ST_BRK",
            "ST_CSRRD",
            "ST_CSRRD48",
            "ST_CCSRWR",
            "retire_packet_q.integer_write_valid <= 1'b1",
            "retire_packet_q.csr_write_valid <= 1'b1",
            "retire_packet_q.ccsr_write_valid <= 1'b1",
            "retire_packet_q.pcc_update_valid <= 1'b1",
            "retire_packet_q.epcc_update_valid <= 1'b1",
            "start_fault_packet(OPC_BRK_12, 8'd12, EXC_BREAKPOINT)",
        ):
            with self.subTest(token=token):
                self.assertIn(token, core)

    def test_testbench_checks_all_i21_s01_coverage_groups(self) -> None:
        tb = (ROOT / "rtl" / "cpu_v01_scalar_control_tb.sv").read_text(
            encoding="utf-8"
        )

        self.assertIn("scalar integer coverage result mismatch", tb)
        self.assertIn("branch/control coverage result mismatch", tb)
        self.assertIn("CSR coverage result mismatch", tb)
        self.assertIn("CCSR coverage result mismatch", tb)
        self.assertIn("BRK breakpoint coverage result mismatch", tb)
        self.assertIn("PAUSE retire coverage result mismatch", tb)

    def test_cli_validates_and_renders_scalar_control_projection_json(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("RTL scalar/control slice issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        mnemonics = {row["mnemonic"] for row in parsed}
        self.assertIn("CPY", mnemonics)
        self.assertIn("BCLR", mnemonics)
        self.assertIn("CSRRD", mnemonics)
        self.assertIn("CCSRWR", mnemonics)
        self.assertNotIn("SFENCE.VM", mnemonics)

    def test_documentation_artifact_names_sources_commands_and_deferrals(self) -> None:
        text = (ROOT / "docs" / "implementation" / "rtl-scalar-control-slice.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I21-S01", text)
        self.assertIn("rtl/cpu_v01_scalar_control_core.sv", text)
        self.assertIn("python tools\\rtl_scalar_control_slice.py --check", text)
        self.assertIn("CSRRD", text)
        self.assertIn("CCSRWR", text)
        self.assertIn("BRK", text)
        self.assertIn("WFI", text)
        self.assertIn("remain for later I21 stories", text)


if __name__ == "__main__":
    unittest.main()
