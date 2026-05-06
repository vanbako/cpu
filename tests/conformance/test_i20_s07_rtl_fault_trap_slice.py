"""I20-S07 conformance tests for fault, trap, and protected-stack RTL behavior."""

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
TOOL = ROOT / "tools" / "rtl_fault_trap_slice.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import opcodes, rtl_fault_trap, sv_contract


def load_tool_module():
    spec = importlib.util.spec_from_file_location("rtl_fault_trap_slice_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RtlFaultTrapSliceTests(unittest.TestCase):
    def test_rtl_fault_trap_sources_exist_and_self_validate(self) -> None:
        self.assertEqual(rtl_fault_trap.validate_rtl_fault_trap_slice(ROOT), ())
        for path in rtl_fault_trap.RTL_FAULT_TRAP_SOURCE_FILES:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).exists())

    def test_package_exposes_fault_trap_and_control_retire_fields(self) -> None:
        package = (ROOT / "rtl" / "cpu_v01_pkg.sv").read_text(encoding="utf-8")

        for token in (
            "OPC_DIV_24",
            "OPC_SYS_12",
            "OPC_IRET_24",
            "OPC_CALL_24",
            "OPC_RET_12",
            "EXC_DIVIDE_BY_ZERO",
            "EXC_SYSCALL_TRAP",
            "MEM_EFFECT_RETURN_STACK_PUSH",
            "CSR_CAUSE",
            "CCSR_RSC",
            "trap_entry_valid",
            "pcc_update_valid",
            "epcc_update_valid",
            "csr_write_valid",
            "ccsr_write_valid",
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
                "csr_write_valid",
                "csr_write_index",
                "csr_write_value",
                "ccsr_write_valid",
                "ccsr_write_index",
                "ccsr_write_value",
                "pcc_update_valid",
                "pcc_update_value",
                "pcc_update_slot",
                "epcc_update_valid",
                "epcc_update_value",
                "epcc_update_slot",
                "trap_entry_valid",
                "trap_target",
                "trap_target_slot",
            },
        )

    def test_fault_trap_core_names_required_states_and_effect_paths(self) -> None:
        core = (ROOT / "rtl" / "cpu_v01_fault_trap_core.sv").read_text(encoding="utf-8")

        for token in (
            "ST_DIV_ZERO_FAULT",
            "ST_SYS_TRAP",
            "ST_IRET",
            "ST_CALL",
            "ST_RET",
            "start_fault_packet(OPC_DIV_24, 8'd24, EXC_DIVIDE_BY_ZERO)",
            "start_fault_packet(OPC_SYS_12, 8'd12, EXC_SYSCALL_TRAP)",
            "retire_packet_q.trap_entry_valid <= 1'b1",
            "retire_packet_q.epcc_update_value <= executable_cap(48'h0000_0000_1750)",
            "retire_packet_q.pcc_update_value <= executable_cap(48'h0000_0000_1750)",
            "retire_packet_q.memory_effect_kind <= MEM_EFFECT_RETURN_STACK_PUSH",
            "retire_packet_q.ccsr_write_index <= CCSR_RSC",
            "return_stack_slot_q <= sealed_return_cap(48'h0000_0000_1501)",
        ):
            with self.subTest(token=token):
                self.assertIn(token, core)

    def test_fault_trap_testbench_checks_fault_trap_iret_call_and_ret(self) -> None:
        tb = (ROOT / "rtl" / "cpu_v01_fault_trap_tb.sv").read_text(encoding="utf-8")

        self.assertIn("divide fault smoke result mismatch", tb)
        self.assertIn("SYS trap entry smoke result mismatch", tb)
        self.assertIn("IRET PCC restore smoke result mismatch", tb)
        self.assertIn("CALL protected return-stack push smoke result mismatch", tb)
        self.assertIn("RET protected return-stack restore smoke result mismatch", tb)
        self.assertIn("packet.pcc_update_value.payload.cursor != 48'h0000_0000_1501", tb)

    def test_projection_matches_golden_fault_trap_call_and_ret_cases(self) -> None:
        projections = rtl_fault_trap.fault_trap_packet_projections()
        by_case_mnemonic = {
            (projection.case_id, projection.mnemonic): projection
            for projection in projections
        }

        divide = by_case_mnemonic[("fault_cases.divide_by_zero", "DIV")]
        self.assertEqual(divide.opcode_id, opcodes.opcode_form_for("DIV").opcode_id)
        self.assertFalse(divide.normal_valid)
        self.assertEqual(divide.fault_cause, "DIVIDE_BY_ZERO")

        sys_trap = by_case_mnemonic[("traps.sys_to_tvc", "SYS")]
        self.assertEqual(sys_trap.opcode_id, opcodes.opcode_form_for("SYS").opcode_id)
        self.assertFalse(sys_trap.normal_valid)
        self.assertEqual(sys_trap.fault_cause, "SYSCALL_TRAP")
        self.assertTrue(sys_trap.trap_entered)
        self.assertEqual(sys_trap.trap_target_cursor, 0x9000)

        iret = by_case_mnemonic[("traps.sys_iret_return", "IRET")]
        self.assertEqual(iret.opcode_id, opcodes.opcode_form_for("IRET").opcode_id)
        self.assertTrue(iret.normal_valid)
        self.assertEqual(iret.pcc_update_cursor, 0x1750)
        self.assertEqual(iret.csr_write_register, "SR")
        self.assertEqual(iret.csr_write_value, 0xC0)

        call = by_case_mnemonic[("calls_returns.direct_call_ret", "CALL")]
        self.assertEqual(call.opcode_id, opcodes.opcode_form_for("CALL").opcode_id)
        self.assertEqual(call.memory_effect_kind, "RETURN_STACK_PUSH")
        self.assertEqual(call.memory_effect_address, 0x3000)
        self.assertEqual(call.memory_capability_cursor, 0x1501)
        self.assertEqual(call.memory_capability_otype, 0xFF)
        self.assertTrue(call.memory_tag_write)
        self.assertEqual(call.ccsr_write_register, "RSC")
        self.assertEqual(call.ccsr_write_cursor, 0x3000)
        self.assertEqual(call.pcc_update_cursor, 0x1510)

        ret = by_case_mnemonic[("calls_returns.direct_call_ret", "RET")]
        self.assertEqual(ret.opcode_id, opcodes.opcode_form_for("RET").opcode_id)
        self.assertEqual(ret.pcc_update_cursor, 0x1501)
        self.assertEqual(ret.ccsr_write_cursor, 0x3004)

    def test_cli_validates_and_renders_fault_trap_projection_json(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("RTL fault/trap slice issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertIn("DIV", {packet["mnemonic"] for packet in parsed})
        self.assertIn("IRET", {packet["mnemonic"] for packet in parsed})
        self.assertIn("CALL", {packet["mnemonic"] for packet in parsed})

    def test_documentation_artifact_names_sources_and_commands(self) -> None:
        text = (ROOT / "docs" / "implementation" / "rtl-fault-trap-slice.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I20-S07", text)
        self.assertIn("rtl/cpu_v01_fault_trap_core.sv", text)
        self.assertIn("python tools\\rtl_fault_trap_slice.py --check", text)
        self.assertIn("DIVIDE_BY_ZERO", text)
        self.assertIn("protected return-stack push", text)


if __name__ == "__main__":
    unittest.main()
