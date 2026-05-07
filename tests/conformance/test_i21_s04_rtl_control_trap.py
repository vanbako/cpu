"""I21-S04 conformance tests for control/trap RTL coverage."""

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
TOOL = ROOT / "tools" / "rtl_control_trap_slice.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import opcodes, rtl_control_trap, sv_contract, syscall_demo


def load_tool_module():
    spec = importlib.util.spec_from_file_location("rtl_control_trap_slice_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RtlControlTrapSliceTests(unittest.TestCase):
    def test_rtl_control_trap_sources_exist_and_self_validate(self) -> None:
        self.assertEqual(rtl_control_trap.validate_rtl_control_trap_slice(ROOT), ())
        for path in rtl_control_trap.RTL_CONTROL_TRAP_SOURCE_FILES:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).exists())

    def test_projection_covers_callc_ret_syscall_and_iret_cases(self) -> None:
        rows = rtl_control_trap.control_trap_coverage_rows()
        by_case = {row.case_id: row for row in rows}

        self.assertEqual(by_case["callc.entry_success"].pcc_update_cursor, 0x1800)
        self.assertEqual(by_case["callc.entry_success"].rsc_cursor_after, 0x303C)
        self.assertEqual(by_case["callc.entry_success"].return_stack_effect, "push")
        self.assertEqual(
            by_case["callc.entry_tag_fault"].fault_cause,
            "CAPABILITY_TAG_FAULT",
        )
        self.assertEqual(by_case["callc.entry_tag_fault"].fault_cap_idx, "C2")
        self.assertEqual(by_case["ret.pop_success"].pcc_update_cursor, 0x1800)
        self.assertEqual(by_case["ret.pop_success"].rsc_cursor_after, 0x3040)
        self.assertEqual(
            by_case["ret.pop_underflow_tag"].fault_cause,
            "RETURN_STACK_UNDERFLOW",
        )
        self.assertEqual(
            by_case["ret.unprotected_permission_fault"].fault_cause,
            "RETURN_STACK_PERMISSION_FAULT",
        )
        self.assertTrue(by_case["sys.sys_trap_frame_save"].trap_entered)
        self.assertTrue(by_case["sys.sys_trap_frame_save"].trap_frame_saved)
        self.assertEqual(
            by_case["sys.scall_alias_trap_frame_save"].opcode_id,
            by_case["sys.sys_trap_frame_save"].opcode_id,
        )

        syscall = by_case["syscall.ok_frame_restore_iret"]
        self.assertTrue(syscall.trap_frame_restored)
        self.assertEqual(syscall.syscall_status, syscall_demo.SyscallDemoStatus.OK.name)
        self.assertEqual(syscall.return_d0, int(syscall_demo.SyscallDemoStatus.OK))
        self.assertEqual(syscall.return_epcc_slot, 1)
        self.assertTrue(syscall.final_user_mode)

    def test_projection_covers_required_mnemonics_and_aliases(self) -> None:
        covered = {row.mnemonic for row in rtl_control_trap.control_trap_coverage_rows()}

        for mnemonic in rtl_control_trap.CONTROL_TRAP_MNEMONICS:
            with self.subTest(mnemonic=mnemonic):
                self.assertIn(mnemonic, covered)

        self.assertEqual(opcodes.canonical_mnemonic("SCALL"), "SYS")
        self.assertEqual(opcodes.opcode_form_for("SCALL"), opcodes.opcode_form_for("SYS"))
        for mnemonic in rtl_control_trap.DEFERRED_MNEMONICS:
            with self.subTest(deferred=mnemonic):
                self.assertNotIn(mnemonic, covered)

    def test_package_and_sv_contract_expose_control_trap_fields(self) -> None:
        package = (ROOT / "rtl" / "cpu_v01_pkg.sv").read_text(encoding="utf-8")

        for token in (
            "OPC_CALLC_24",
            "OPC_SCALL_12",
            "EXC_RETURN_STACK_UNDERFLOW",
            "EXC_RETURN_STACK_PERMISSION_FAULT",
            "CAPCAUSE_PERMISSION",
            "FAULT_CAP_IDX_C2",
            "FAULT_CAP_IDX_RSC",
            "trap_frame_save_valid",
            "trap_frame_restore_valid",
            "trap_frame_epcc_value",
            "trap_frame_sr_value",
            "syscall_service_valid",
            "syscall_service_number",
            "syscall_status",
            "syscall_return_valid",
            "syscall_return_d0",
            "syscall_return_d1",
            "syscall_return_c0",
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
                "trap_frame_save_valid",
                "trap_frame_restore_valid",
                "trap_frame_epcc_value",
                "trap_frame_epcc_slot",
                "trap_frame_sr_value",
                "syscall_service_valid",
                "syscall_service_number",
                "syscall_status",
                "syscall_return_valid",
                "syscall_return_d0",
                "syscall_return_d1",
                "syscall_return_c0",
            },
        )

    def test_control_trap_core_names_states_and_effect_paths(self) -> None:
        core = (ROOT / "rtl" / "cpu_v01_control_trap_core.sv").read_text(
            encoding="utf-8"
        )

        for token in (
            "ST_CALLC_ENTRY",
            "ST_CALLC_TAG_FAULT",
            "ST_RET_POP",
            "ST_RET_UNDERFLOW",
            "ST_RET_PERMISSION_FAULT",
            "ST_SYS_TRAP",
            "ST_SCALL_TRAP_ALIAS",
            "ST_SYSCALL_FRAME_SAVE",
            "ST_SYSCALL_FRAME_RESTORE",
            "ST_IRET_USER_RETURN",
            "retire_packet_q.memory_effect_kind <= MEM_EFFECT_RETURN_STACK_PUSH",
            "retire_packet_q.trap_frame_save_valid <= 1'b1",
            "retire_packet_q.trap_frame_restore_valid <= 1'b1",
            "retire_packet_q.syscall_service_valid <= 1'b1",
            "retire_packet_q.syscall_return_valid <= 1'b1",
            "start_fault_packet(OPC_SCALL_12, 8'd12, EXC_SYSCALL_TRAP)",
            "start_fault_packet(OPC_RET_12, 8'd12, EXC_RETURN_STACK_UNDERFLOW)",
        ):
            with self.subTest(token=token):
                self.assertIn(token, core)

    def test_testbench_checks_i21_s04_coverage_groups(self) -> None:
        tb = (ROOT / "rtl" / "cpu_v01_control_trap_tb.sv").read_text(
            encoding="utf-8"
        )

        self.assertIn("CALLC entry protected-stack result mismatch", tb)
        self.assertIn("CALLC entry fault result mismatch", tb)
        self.assertIn("RET pop result mismatch", tb)
        self.assertIn("RET protected pop fault result mismatch", tb)
        self.assertIn("SYS/SCALL trap-frame save result mismatch", tb)
        self.assertIn("syscall frame restore result mismatch", tb)
        self.assertIn("IRET user return result mismatch", tb)

    def test_cli_validates_and_renders_control_trap_projection_json(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("RTL control/trap slice issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        case_ids = {row["case_id"] for row in parsed}
        self.assertIn("callc.entry_success", case_ids)
        self.assertIn("ret.pop_underflow_tag", case_ids)
        self.assertIn("syscall.ok_frame_restore_iret", case_ids)

    def test_documentation_artifact_names_sources_commands_and_deferrals(self) -> None:
        text = (
            ROOT / "docs" / "implementation" / "rtl-control-trap-slice.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Story: I21-S04", text)
        self.assertIn("rtl/cpu_v01_control_trap_core.sv", text)
        self.assertIn("python tools\\rtl_control_trap_slice.py --check", text)
        self.assertIn("CALLC", text)
        self.assertIn("SCALL", text)
        self.assertIn("RETURN_STACK_UNDERFLOW", text)
        self.assertIn("syscall trap-frame", text)
        self.assertIn("remain for later stories", text)


if __name__ == "__main__":
    unittest.main()
