"""I22-S05 conformance tests for integrated core control/trap execution."""

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
TOOL = ROOT / "tools" / "rtl_core_control_trap.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import rtl_control_trap, rtl_core_control_trap


def load_tool_module():
    spec = importlib.util.spec_from_file_location("rtl_core_control_trap_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RtlCoreControlTrapTests(unittest.TestCase):
    def test_rtl_core_control_trap_sources_exist_and_self_validate(self) -> None:
        self.assertEqual(rtl_core_control_trap.validate_rtl_core_control_trap(ROOT), ())
        for path in rtl_core_control_trap.RTL_CORE_CONTROL_TRAP_SOURCE_FILES:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).exists())

    def test_projection_covers_i21_control_trap_mnemonics(self) -> None:
        rows = rtl_core_control_trap.integrated_control_trap_coverage_rows()
        by_case = {row.case_id: row for row in rows}
        covered = {row.mnemonic for row in rows}

        self.assertGreaterEqual(covered, set(rtl_control_trap.CONTROL_TRAP_MNEMONICS))
        self.assertIn("return_stack_push", by_case["callc.entry_success"].retire_effects)
        self.assertIn("pcc_update", by_case["callc.entry_success"].retire_effects)
        self.assertEqual(
            by_case["callc.entry_tag_fault"].retire_effects,
            ("fault:CAPABILITY_TAG_FAULT",),
        )
        self.assertIn("return_stack_pop", by_case["ret.pop_success"].retire_effects)
        self.assertEqual(
            by_case["ret.pop_underflow_tag"].retire_effects,
            ("fault:RETURN_STACK_UNDERFLOW",),
        )
        self.assertIn("trap_entry", by_case["sys.sys_trap_frame_save"].retire_effects)
        self.assertIn("trap_frame_save", by_case["sys.sys_trap_frame_save"].retire_effects)
        self.assertIn(
            "trap_frame_save",
            by_case["sys.scall_alias_trap_frame_save"].retire_effects,
        )
        self.assertIn(
            "trap_frame_restore",
            by_case["syscall.ok_frame_restore_iret"].retire_effects,
        )

    def test_core_names_return_stack_trap_and_syscall_paths(self) -> None:
        core = (ROOT / "rtl" / "cpu_v01_core.sv").read_text(encoding="utf-8")

        for token in (
            "return_stack_slot_q",
            "return_stack_cap",
            "return_capability",
            "unsealed_capability",
            "next_pcc",
            "next_slot",
            "OPC_CALL_24",
            "OPC_CALLC_24",
            "OPC_RET_12",
            "OPC_SYS_12",
            "OPC_IRET_24",
            "MEM_EFFECT_RETURN_STACK_PUSH",
            "EXC_RETURN_STACK_UNDERFLOW",
            "EXC_SYSCALL_TRAP",
            "trap_entry_valid",
            "trap_frame_save_valid",
            "trap_frame_restore_valid",
            "commit_epcc_update",
            "commit_pcc_update(tvc_q, SLOT_0)",
        ):
            with self.subTest(token=token):
                self.assertIn(token, core)

    def test_control_trap_testbench_checks_success_and_fault_paths(self) -> None:
        tb = (ROOT / "rtl" / "cpu_v01_core_control_trap_tb.sv").read_text(
            encoding="utf-8"
        )

        for token in (
            "module cpu_v01_core_control_trap_tb",
            "cpu_v01_core_control_trap_fixture",
            "CALL 0x5002",
            "CALLC C1",
            "SYS; PAUSE",
            "IRET",
            "CALLC C0 invalid tag",
            "RET with empty protected return stack",
            "integrated control/trap CALL mismatch",
            "integrated control/trap SYS mismatch",
            "integrated control/trap RET underflow mismatch",
        ):
            with self.subTest(token=token):
                self.assertIn(token, tb)

    def test_cli_validates_and_renders_integrated_control_trap_json(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("RTL integrated core control/trap issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        by_case = {row["case_id"]: row for row in parsed}
        self.assertIn("callc.entry_success", by_case)
        self.assertIn("ret.pop_underflow_tag", by_case)
        self.assertIn("syscall.ok_frame_restore_iret", by_case)
        self.assertIn(
            "trap_frame_save",
            by_case["sys.sys_trap_frame_save"]["retire_effects"],
        )

    def test_documentation_artifact_names_sources_commands_and_deferrals(self) -> None:
        text = (
            ROOT
            / "docs"
            / "implementation"
            / "rtl-integrated-core-control-trap.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Story: I22-S05", text)
        self.assertIn("rtl/cpu_v01_core.sv", text)
        self.assertIn("rtl/cpu_v01_core_control_trap_tb.sv", text)
        self.assertIn("python tools\\rtl_core_control_trap.py --check", text)
        self.assertIn("cpu_v01_core_control_trap_tb", text)
        self.assertIn("CALL", text)
        self.assertIn("CALLC", text)
        self.assertIn("RET", text)
        self.assertIn("SYS", text)
        self.assertIn("SCALL", text)
        self.assertIn("IRET", text)
        self.assertIn("RETURN_STACK_UNDERFLOW", text)
        self.assertIn("trap-frame", text)
        self.assertIn("I22-S06", text)

    def test_verilator_command_names_integrated_control_trap_top(self) -> None:
        command = rtl_core_control_trap.core_control_trap_verilator_command()

        self.assertIn("--top-module cpu_v01_core_control_trap_tb", command)
        self.assertIn("rtl/cpu_v01_core.sv", command)
        self.assertIn("rtl/cpu_v01_core_control_trap_tb.sv", command)


if __name__ == "__main__":
    unittest.main()
