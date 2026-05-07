"""I20-S08 conformance tests for the RTL readiness gap report."""

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
TOOL = ROOT / "tools" / "rtl_readiness_gap.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import golden_traces, opcodes, rtl_readiness


def load_tool_module():
    spec = importlib.util.spec_from_file_location("rtl_readiness_gap_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RtlReadinessGapTests(unittest.TestCase):
    def test_readiness_report_self_validates_and_names_gate_command(self) -> None:
        self.assertEqual(rtl_readiness.validate_rtl_readiness_report(ROOT), ())
        report = rtl_readiness.rtl_readiness_report()

        self.assertEqual(report.gate_command, "python tools\\local_checks.py")
        self.assertIn(
            "python tools\\rtl_fault_trap_slice.py --check",
            report.slice_check_commands,
        )
        self.assertIn(
            "python tools\\rtl_scalar_control_slice.py --check",
            report.slice_check_commands,
        )
        self.assertIn(
            "python tools\\rtl_mmu_tlb_slice.py --check",
            report.slice_check_commands,
        )
        self.assertIn(
            "python tools\\rtl_atomic_cache_slice.py --check",
            report.slice_check_commands,
        )
        self.assertIn(
            "python tools\\rtl_control_trap_slice.py --check",
            report.slice_check_commands,
        )
        self.assertIn(
            "python tools\\verilator_diff_harness.py --suite fast",
            report.slice_check_commands,
        )

    def test_implemented_surface_lists_rtl_slices_and_artifacts(self) -> None:
        report = rtl_readiness.rtl_readiness_report()
        by_story = {surface.story: surface for surface in report.implemented_surfaces}

        self.assertIn("rtl/cpu_v01_smoke_core.sv", by_story["I20-S05"].artifacts)
        self.assertIn("rtl/cpu_v01_cap_mem_core.sv", by_story["I20-S06"].artifacts)
        self.assertIn("rtl/cpu_v01_fault_trap_core.sv", by_story["I20-S07"].artifacts)
        self.assertIn("rtl/cpu_v01_scalar_control_core.sv", by_story["I21-S01"].artifacts)
        self.assertIn("rtl/cpu_v01_mmu_tlb_core.sv", by_story["I21-S02"].artifacts)
        self.assertIn("rtl/cpu_v01_atomic_cache_core.sv", by_story["I21-S03"].artifacts)
        self.assertIn("rtl/cpu_v01_control_trap_core.sv", by_story["I21-S04"].artifacts)
        self.assertIn("tools/verilator_diff_harness.py", by_story["I21-S05"].artifacts)
        self.assertIn("ADD", by_story["I20-S05"].mnemonics)
        self.assertIn("CSETADDR", by_story["I20-S06"].mnemonics)
        self.assertIn("IRET", by_story["I20-S07"].mnemonics)
        self.assertIn("CPY", by_story["I21-S01"].mnemonics)
        self.assertIn("CCSRWR", by_story["I21-S01"].mnemonics)
        self.assertIn("SFENCE.VM", by_story["I21-S02"].mnemonics)
        self.assertIn("SFENCE.VM.VA_ASID", by_story["I21-S02"].mnemonics)
        self.assertIn("LL48", by_story["I21-S03"].mnemonics)
        self.assertIn("CACHE.CLEANINVAL", by_story["I21-S03"].mnemonics)
        self.assertIn("CALLC", by_story["I21-S04"].mnemonics)
        self.assertIn("SCALL", by_story["I21-S04"].mnemonics)
        self.assertIn("calls_returns.direct_call_ret", by_story["I20-S07"].golden_cases)

    def test_verilator_fixture_commands_name_all_slice_testbenches(self) -> None:
        report = rtl_readiness.rtl_readiness_report()
        by_top = {
            fixture.top_module: fixture
            for fixture in report.verilator_fixture_commands
        }

        self.assertEqual(
            set(by_top),
            {
                "cpu_v01_smoke_tb",
                "cpu_v01_cap_mem_tb",
                "cpu_v01_fault_trap_tb",
                "cpu_v01_scalar_control_tb",
                "cpu_v01_mmu_tlb_tb",
                "cpu_v01_atomic_cache_tb",
                "cpu_v01_control_trap_tb",
            },
        )
        cap_mem = by_top["cpu_v01_cap_mem_tb"]
        self.assertIn("rtl/cpu_v01_pkg.sv", cap_mem.source_files)
        self.assertIn("rtl/cpu_v01_cap_mem_core.sv", cap_mem.source_files)
        self.assertIn("rtl/cpu_v01_cap_mem_tb.sv", cap_mem.source_files)
        self.assertIn("--binary --timing", cap_mem.command)
        self.assertIn("--top-module cpu_v01_cap_mem_tb", cap_mem.command)
        scalar_control = by_top["cpu_v01_scalar_control_tb"]
        self.assertIn("rtl/cpu_v01_scalar_control_core.sv", scalar_control.source_files)
        self.assertIn("--top-module cpu_v01_scalar_control_tb", scalar_control.command)
        mmu_tlb = by_top["cpu_v01_mmu_tlb_tb"]
        self.assertIn("rtl/cpu_v01_mmu_tlb_core.sv", mmu_tlb.source_files)
        self.assertIn("--top-module cpu_v01_mmu_tlb_tb", mmu_tlb.command)
        atomic_cache = by_top["cpu_v01_atomic_cache_tb"]
        self.assertIn("rtl/cpu_v01_atomic_cache_core.sv", atomic_cache.source_files)
        self.assertIn("--top-module cpu_v01_atomic_cache_tb", atomic_cache.command)
        control_trap = by_top["cpu_v01_control_trap_tb"]
        self.assertIn("rtl/cpu_v01_control_trap_core.sv", control_trap.source_files)
        self.assertIn("--top-module cpu_v01_control_trap_tb", control_trap.command)

    def test_golden_coverage_names_every_case_and_current_rtl_status(self) -> None:
        report = rtl_readiness.rtl_readiness_report()
        coverage = {row.case_id: row for row in report.golden_coverage}

        self.assertEqual(
            set(coverage),
            {case.case_id for case in golden_traces.golden_trace_corpus()},
        )
        self.assertEqual(coverage["reset_smoke.add_slot0"].rtl_status, "`I20-S05` RTL smoke slice")
        self.assertEqual(
            coverage["memory_tag_ops.csc_clc_st48_ld48"].rtl_status,
            "`I20-S06` RTL capability/memory slice",
        )
        self.assertEqual(
            coverage["traps.sys_iret_return"].rtl_status,
            "`I20-S07` RTL fault/trap slice",
        )
        self.assertIn("I21-S01", coverage["integer_ops.add_mul"].rtl_status)

    def test_unsupported_mnemonics_and_interfaces_are_visible(self) -> None:
        report = rtl_readiness.rtl_readiness_report()
        unsupported = set(report.unsupported_mnemonics)

        self.assertGreater(len(unsupported), 0)
        self.assertLess(len(unsupported), len(opcodes.mandatory_mnemonics()))
        self.assertNotIn("MUL", unsupported)
        self.assertNotIn("CSRRD", unsupported)
        self.assertNotIn("CCSRWR", unsupported)
        self.assertNotIn("SFENCE.VM", unsupported)
        self.assertNotIn("SFENCE.VM.VA_ASID", unsupported)
        self.assertNotIn("LL48", unsupported)
        self.assertNotIn("SC48", unsupported)
        self.assertNotIn("FENCE.I", unsupported)
        self.assertNotIn("CACHE.CLEAN", unsupported)
        self.assertNotIn("CALLC", unsupported)
        for mnemonic in ("WFI", "CINCADDR", "CSETBOUNDS"):
            with self.subTest(mnemonic=mnemonic):
                self.assertIn(mnemonic, unsupported)
        self.assertIn("No integrated `cpu_v01_core` top-level is implemented.", report.unsupported_interfaces)
        self.assertIn("Multicore execution.", report.known_deferrals)
        self.assertIn("Integrated page-table walker ports, remote TLB shootdown, and MMU replay timing.", report.known_deferrals)

    def test_cli_validates_and_renders_markdown_and_json(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("RTL readiness gap report issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main([])

        self.assertEqual(result, 0)
        markdown = stream.getvalue()
        self.assertIn("Story: I20-S08", markdown)
        self.assertIn("python tools\\local_checks.py", markdown)
        self.assertIn("Unsupported Instructions", markdown)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--format", "json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["gate_command"], "python tools\\local_checks.py")
        self.assertIn("unsupported_mnemonics", parsed)
        self.assertIn("verilator_fixture_commands", parsed)

    def test_documentation_artifact_names_required_gap_report_sections(self) -> None:
        text = (ROOT / "docs" / "implementation" / "rtl-readiness-gap-report.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I20-S08", text)
        self.assertIn("python tools\\local_checks.py", text)
        self.assertIn("Implemented RTL Surface", text)
        self.assertIn("Verilator fixture build commands", text)
        self.assertIn("cpu_v01_cap_mem_tb", text)
        self.assertIn("cpu_v01_scalar_control_tb", text)
        self.assertIn("cpu_v01_mmu_tlb_tb", text)
        self.assertIn("cpu_v01_atomic_cache_tb", text)
        self.assertIn("cpu_v01_control_trap_tb", text)
        self.assertIn("Golden Corpus Coverage", text)
        self.assertIn("Unsupported Instructions", text)
        self.assertIn("Unsupported Interfaces", text)
        self.assertIn("Known Deferrals", text)
        self.assertIn("`WFI`", text)
        self.assertIn("`I21-S01`", text)
        self.assertIn("`I21-S02`", text)
        self.assertIn("`I21-S03`", text)
        self.assertIn("`I21-S04`", text)
        self.assertIn("`I21-S05`", text)
        self.assertIn("Multicore execution.", text)


if __name__ == "__main__":
    unittest.main()
