"""I20-S02 conformance tests for the semantic golden retire trace corpus."""

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
TOOL = ROOT / "tools" / "golden_trace_corpus.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import golden_traces


def load_tool_module():
    spec = importlib.util.spec_from_file_location("golden_trace_corpus_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class GoldenTraceCorpusTests(unittest.TestCase):
    def test_corpus_self_validation_passes_and_categories_are_complete(self) -> None:
        cases = golden_traces.golden_trace_corpus()

        self.assertEqual(golden_traces.validate_golden_trace_corpus(cases), ())
        self.assertEqual(
            {case.category for case in cases},
            golden_traces.REQUIRED_GOLDEN_TRACE_CATEGORIES,
        )
        self.assertEqual(len({case.case_id for case in cases}), len(cases))

    def test_packets_are_machine_readable_and_have_required_retire_fields(self) -> None:
        parsed = json.loads(golden_traces.golden_trace_corpus_json())

        self.assertIsInstance(parsed, list)
        for case in parsed:
            with self.subTest(case_id=case["case_id"]):
                self.assertTrue(case["packets"])
                for sequence, packet in enumerate(case["packets"]):
                    self.assertTrue(packet["valid"])
                    self.assertEqual(packet["sequence"], sequence)
                    for field in (
                        "pc_cell",
                        "slot",
                        "instruction_length",
                        "mnemonic",
                        "opcode_id",
                        "result_kind",
                        "result_stage",
                    ):
                        self.assertIn(field, packet)
                    selected = sum(
                        packet[name] is not None
                        for name in ("normal_effects", "fault_packet", "redirect_packet")
                    )
                    self.assertEqual(selected, 1)

    def test_memory_tag_case_covers_capability_transfer_and_tag_clear(self) -> None:
        move = golden_traces.golden_trace_case_by_id("capability_derivation.cmove_cgetaddr")
        self.assertEqual(tuple(packet["mnemonic"] for packet in move.packets), ("CMOVE", "CGETADDR"))
        self.assertTrue(move.final_observations["capability_registers"]["C2"]["tag"])
        self.assertEqual(move.final_observations["integer_registers"]["D3"], 0x2200)

        case = golden_traces.golden_trace_case_by_id("memory_tag_ops.csc_clc_st48_ld48")
        mnemonics = tuple(packet["mnemonic"] for packet in case.packets)

        self.assertEqual(mnemonics, ("CSC", "CLC", "ST48", "LD48"))
        first_effects = case.packets[0]["normal_effects"]["memory_effects"]
        self.assertEqual(first_effects[0]["kind"], "CSC")
        self.assertTrue(first_effects[0]["capability"]["tag"])
        self.assertTrue(case.final_observations["capability_registers"]["C3"]["tag"])
        self.assertFalse(case.final_observations["memory_tags"]["0x2000"])
        self.assertEqual(case.final_observations["integer_registers"]["D5"], 0x123456789ABC)

    def test_trap_call_return_and_fault_cases_have_expected_packets(self) -> None:
        trap = golden_traces.golden_trace_case_by_id("traps.sys_to_tvc")
        self.assertEqual(trap.packets[0]["fault_packet"]["cause"], "SYSCALL_TRAP")
        self.assertTrue(trap.packets[0]["trap_entry"]["entered"])
        self.assertEqual(trap.final_observations["pcc"]["payload"]["cursor"], 0x9000)

        trap_iret = golden_traces.golden_trace_case_by_id("traps.sys_iret_return")
        self.assertEqual(tuple(packet["mnemonic"] for packet in trap_iret.packets), ("SYS", "IRET"))
        self.assertTrue(trap_iret.packets[0]["trap_entry"]["entered"])
        self.assertEqual(
            trap_iret.packets[1]["normal_effects"]["pcc_update"]["payload"]["cursor"],
            0x1750,
        )
        self.assertEqual(trap_iret.final_observations["pcc"]["payload"]["cursor"], 0x1750)

        call_return = golden_traces.golden_trace_case_by_id("calls_returns.direct_call_ret")
        self.assertEqual(tuple(packet["mnemonic"] for packet in call_return.packets), ("CALL", "RET"))
        self.assertEqual(
            call_return.packets[0]["normal_effects"]["memory_effects"][0]["kind"],
            "RETURN_STACK_PUSH",
        )
        self.assertEqual(call_return.final_observations["pcc"]["payload"]["cursor"], 0x1501)
        self.assertTrue(call_return.final_observations["memory_tags"]["0x3000"])

        divide = golden_traces.golden_trace_case_by_id("fault_cases.divide_by_zero")
        invalid_tag = golden_traces.golden_trace_case_by_id("fault_cases.invalid_tag_csetaddr")
        placement = golden_traces.golden_trace_case_by_id("fault_cases.slot1_48bit_placement")
        self.assertEqual(divide.packets[0]["fault_packet"]["cause"], "DIVIDE_BY_ZERO")
        self.assertEqual(invalid_tag.packets[0]["fault_packet"]["cause"], "CAPABILITY_TAG_FAULT")
        self.assertEqual(invalid_tag.packets[0]["fault_packet"]["capcause"], "TAG")
        self.assertEqual(invalid_tag.packets[0]["fault_packet"]["fault_cap_idx"], "C1")
        self.assertEqual(placement.packets[0]["fault_packet"]["cause"], "ALIGN_FAULT")
        self.assertEqual(placement.packets[0]["result_stage"], "PD")

    def test_cli_lists_cases_and_prints_json_for_single_case(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--list"])

        self.assertEqual(result, 0)
        self.assertIn("reset_smoke.add_slot0\treset_smoke", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--case", "traps.sys_to_tvc"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed[0]["case_id"], "traps.sys_to_tvc")
        self.assertEqual(parsed[0]["packets"][0]["fault_packet"]["cause"], "SYSCALL_TRAP")

    def test_documentation_artifact_names_command_and_coverage_scope(self) -> None:
        text = (ROOT / "docs" / "implementation" / "golden-retire-trace-corpus.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I20-S02", text)
        self.assertIn("python tools\\golden_trace_corpus.py", text)
        self.assertIn("memory_tag_ops.csc_clc_st48_ld48", text)
        self.assertIn("Expected retire packets are machine-readable", text)


if __name__ == "__main__":
    unittest.main()
