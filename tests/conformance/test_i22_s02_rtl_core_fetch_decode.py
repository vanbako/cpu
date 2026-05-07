"""I22-S02 conformance tests for integrated core fetch/decode."""

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
TOOL = ROOT / "tools" / "rtl_core_fetch_decode.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import opcodes, rtl_core_fetch


def load_tool_module():
    spec = importlib.util.spec_from_file_location("rtl_core_fetch_decode_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RtlCoreFetchDecodeTests(unittest.TestCase):
    def test_rtl_core_fetch_decode_sources_exist_and_self_validate(self) -> None:
        self.assertEqual(rtl_core_fetch.validate_rtl_core_fetch_decode(ROOT), ())
        for path in rtl_core_fetch.RTL_CORE_FETCH_SOURCE_FILES:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).exists())

    def test_projection_covers_every_mandatory_opcode_by_size(self) -> None:
        rows = {row.size_bits: row for row in rtl_core_fetch.fetch_decode_coverage_rows()}

        self.assertEqual(set(rows), {12, 24, 48})
        self.assertIn("RET", rows[12].mnemonics)
        self.assertIn("WFI", rows[12].mnemonics)
        self.assertIn("ADD", rows[24].mnemonics)
        self.assertIn("SFENCE.VM.VA_ASID", rows[24].mnemonics)
        self.assertIn("CGETADDR", rows[48].mnemonics)
        self.assertIn("CCSRWR", rows[48].mnemonics)

        accounted = {
            mnemonic
            for row in rows.values()
            for mnemonic in row.mnemonics
        }
        self.assertEqual(accounted, set(opcodes.mandatory_mnemonics()))

    def test_package_and_core_name_fetch_decode_tables_and_fault_paths(self) -> None:
        package = (ROOT / "rtl" / "cpu_v01_pkg.sv").read_text(encoding="utf-8")
        core = (ROOT / "rtl" / "cpu_v01_core.sv").read_text(encoding="utf-8")

        self.assertIn("OPC_WFI_12", package)
        for token in (
            "ENABLE_FETCH",
            "ST_FETCH_REQ",
            "ST_FETCH_WAIT",
            "ST_DECODE",
            "fetch_group_base",
            "is_12_opcode",
            "is_24_major",
            "is_48_major",
            "opcode_id_for_12",
            "start_decoded_packet",
            "start_fault_packet",
            "advance_pc",
            "EXC_ALIGN_FAULT",
            "EXC_ILLEGAL_INSTRUCTION",
            "pcc_slot_q <= SLOT_1",
            "pcc_q.payload.cursor <= fetch_pc_q + 48'd2",
        ):
            with self.subTest(token=token):
                self.assertIn(token, core)

        for form in opcodes.all_opcode_forms():
            token = (
                f"12'h{form.opcode_id:03X}"
                if form.size.bits == 12
                else f"8'h{form.opcode_id:02X}"
            )
            with self.subTest(mnemonic=form.mnemonic, token=token):
                self.assertIn(token, core)

    def test_fetch_decode_testbench_checks_legal_and_fault_cases(self) -> None:
        tb = (ROOT / "rtl" / "cpu_v01_core_fetch_decode_tb.sv").read_text(
            encoding="utf-8"
        )

        self.assertIn("integrated core fetch/decode legal sequence mismatch", tb)
        self.assertIn("did not fault 48-bit instruction at second fetch-group cell", tb)
        self.assertIn("did not fault 24-bit instruction at slot 1", tb)
        self.assertIn("did not fault illegal opcode contents", tb)
        self.assertIn("OPC_ADD_24", tb)
        self.assertIn("OPC_PAUSE_12", tb)
        self.assertIn("OPC_BRK_12", tb)
        self.assertIn("OPC_CGETADDR_48", tb)

    def test_cli_validates_and_renders_fetch_decode_projection_json(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("RTL integrated core fetch/decode issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        sizes = {row["size_bits"] for row in parsed}
        self.assertEqual(sizes, {12, 24, 48})
        by_size = {row["size_bits"]: row for row in parsed}
        self.assertIn("PAUSE", by_size[12]["mnemonics"])
        self.assertIn("ADD", by_size[24]["mnemonics"])
        self.assertIn("CGETADDR", by_size[48]["mnemonics"])

    def test_documentation_artifact_names_sources_commands_and_deferrals(self) -> None:
        text = (ROOT / "docs" / "implementation" / "rtl-integrated-core-fetch-decode.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I22-S02", text)
        self.assertIn("rtl/cpu_v01_core.sv", text)
        self.assertIn("rtl/cpu_v01_core_fetch_decode_tb.sv", text)
        self.assertIn("python tools\\rtl_core_fetch_decode.py --check", text)
        self.assertIn("cpu_v01_core_fetch_decode_tb", text)
        self.assertIn("12/24/48", text)
        self.assertIn("placement", text)
        self.assertIn("illegal-instruction", text)
        self.assertIn("I22-S03", text)


if __name__ == "__main__":
    unittest.main()
