"""I17-S04 conformance tests for the toolchain regression corpus."""

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
TOOL = ROOT / "tools" / "toolchain_corpus.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import assembly, linker, toolchain_corpus


def load_tool_module():
    spec = importlib.util.spec_from_file_location("toolchain_corpus_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ToolchainRegressionCorpusTests(unittest.TestCase):
    def test_corpus_self_validation_passes_and_categories_are_complete(self) -> None:
        cases = toolchain_corpus.toolchain_corpus()

        self.assertEqual(toolchain_corpus.validate_toolchain_corpus(cases), ())
        self.assertEqual(
            {case.category.value for case in cases},
            toolchain_corpus.REQUIRED_TOOLCHAIN_CORPUS_CATEGORIES,
        )
        self.assertEqual(len({case.case_id for case in cases}), len(cases))

    def test_binary_fixtures_roundtrip_through_cells_octets_and_disassembly(self) -> None:
        for case in toolchain_corpus.toolchain_corpus():
            for section in case.binary_sections:
                with self.subTest(case_id=case.case_id, section=section.name):
                    self.assertEqual(section.disassembled_lines, section.source_lines)
                    self.assertEqual(
                        assembly.disassemble_program(section.payload_cells),
                        section.source_lines,
                    )
                    self.assertEqual(len(section.payload_octets), len(section.payload_cells) * 3)

        reset = toolchain_corpus.toolchain_case_by_id("reset_smoke.reset_to_trap_image")
        self.assertEqual(
            tuple(section.name for section in reset.binary_sections),
            ("main", "trap_handler"),
        )
        call = toolchain_corpus.toolchain_case_by_id("call_return.direct_call_ret_binary")
        self.assertEqual(call.binary_sections[0].disassembled_lines, ("CALL 0x104", "RET"))
        syscall = toolchain_corpus.toolchain_case_by_id("syscall_trap.sys_pause_iret_binary")
        self.assertEqual(syscall.binary_sections[0].disassembled_lines, ("SYS", "PAUSE", "IRET"))

    def test_relocation_debug_metadata_and_bad_object_cases_are_executable(self) -> None:
        relocation = toolchain_corpus.toolchain_case_by_id("relocation.branch_call_data_object")
        image = linker.link_objects(relocation.linker_objects, base_cell=relocation.base_cell)
        text = image.section_by_name("reloc", "text")
        data = image.section_by_name("reloc", "data")

        self.assertEqual(text.payload_cells[0], assembly.assemble_line("BRA 0x203").cells[0])
        self.assertEqual(text.payload_cells[1], assembly.assemble_line("Bcc EQ, 0x203").cells[0])
        self.assertEqual(text.payload_cells[2], assembly.assemble_line("CALL 0x203").cells[0])
        self.assertEqual(data.payload_cells, (0x0203, 0))

        debug = toolchain_corpus.toolchain_case_by_id("debug_metadata.lines_symbols_registers")
        debug_dict = debug.as_dict()["debug_metadata"]
        locations = {line["location"]: line["source"] for line in debug_dict["lines"]}
        registers = {register["name"]: register for register in debug_dict["registers"]}
        self.assertEqual(locations["0x0301:slot1"], "corpus/debug.cv01:3:1")
        self.assertTrue(registers["PCC"]["slot_visible"])
        self.assertIn("CONTEXT_SWITCH", registers["PCC"]["abi_roles"])
        self.assertTrue(debug_dict["unwind_hints"])

        bad = toolchain_corpus.toolchain_case_by_id("bad_object.missing_payload_and_abi")
        issues = "; ".join(linker.validate_linker_inputs(bad.linker_objects))
        self.assertIn("object ABI attributes must include PURE_CAPABILITY", issues)
        self.assertIn("missing payload for section bad:data", issues)
        with self.assertRaises(linker.LinkerError):
            linker.link_objects(bad.linker_objects)

    def test_cli_validates_lists_and_prints_machine_readable_json(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("Toolchain corpus issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--list"])

        self.assertEqual(result, 0)
        self.assertIn("relocation.branch_call_data_object\trelocation", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--case", "debug_metadata.lines_symbols_registers"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed[0]["case_id"], "debug_metadata.lines_symbols_registers")
        self.assertIn("debug_metadata", parsed[0])

    def test_local_checks_plan_runs_toolchain_corpus_gate(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "local_checks_tool",
            ROOT / "tools" / "local_checks.py",
        )
        assert spec is not None
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)

        commands = tuple(check.command for check in module.local_checks(python="python"))

        self.assertIn(("python", "tools/toolchain_corpus.py", "--check"), commands)

    def test_documentation_artifact_names_toolchain_corpus_command_and_scope(self) -> None:
        text = (ROOT / "docs" / "implementation" / "toolchain-regression-corpus.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I17-S04", text)
        self.assertIn("python tools\\toolchain_corpus.py --check", text)
        self.assertIn("bad-object", text)
        self.assertIn("python tools\\local_checks.py", text)


if __name__ == "__main__":
    unittest.main()
