"""I22-S07 conformance tests for integrated core atomic/cache execution."""

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
TOOL = ROOT / "tools" / "rtl_core_atomic_cache.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import rtl_atomic_cache, rtl_core_atomic_cache


def load_tool_module():
    spec = importlib.util.spec_from_file_location("rtl_core_atomic_cache_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RtlCoreAtomicCacheTests(unittest.TestCase):
    def test_rtl_core_atomic_cache_sources_exist_and_self_validate(self) -> None:
        self.assertEqual(rtl_core_atomic_cache.validate_rtl_core_atomic_cache(ROOT), ())
        for path in rtl_core_atomic_cache.RTL_CORE_ATOMIC_CACHE_SOURCE_FILES:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).exists())

    def test_projection_covers_i21_atomic_cache_cases(self) -> None:
        rows = rtl_core_atomic_cache.integrated_atomic_cache_coverage_rows()
        by_case = {row.case_id: row for row in rows}
        covered = {row.mnemonic for row in rows}

        self.assertGreaterEqual(covered, set(rtl_atomic_cache.ATOMIC_CACHE_MNEMONICS))
        self.assertEqual(
            by_case["llsc.ll48_install"].retire_effects,
            ("reservation:install", "memory:integer_load"),
        )
        self.assertEqual(
            by_case["llsc.sc48_success_store_clear"].retire_effects,
            ("reservation:clear", "memory:store_tag_clear", "sc_success"),
        )
        self.assertEqual(
            by_case["llsc.sc48_failure_clear"].retire_effects,
            ("reservation:clear", "sc_failure"),
        )
        self.assertIn(
            "reservation:conflict_clear",
            by_case["llsc.conflicting_store_clear"].retire_effects,
        )
        self.assertEqual(
            by_case["reservation.sfence_clear"].retire_effects,
            ("reservation:fence_clear", "tlb_invalidate:ALL"),
        )
        self.assertEqual(
            by_case["cache.clean_device_access_fault"].retire_effects,
            ("fault:ACCESS_FAULT", "translation_fault:DEVICE_ORDERED"),
        )

    def test_core_names_atomic_reservation_fence_and_cache_paths(self) -> None:
        core = (ROOT / "rtl" / "cpu_v01_core.sv").read_text(encoding="utf-8")

        for token in (
            "ATOMIC_CACHE_DEVICE_PA",
            "reservation_valid_q",
            "reservation_overlaps",
            "commit_reservation_install",
            "commit_reservation_clear_if_valid",
            "commit_reservation_clear_at",
            "OPC_LL48_24",
            "OPC_SC48_24",
            "OPC_FENCE_24",
            "OPC_FENCE_I_24",
            "OPC_CACHE_CLEAN_24",
            "OPC_CACHE_INVAL_24",
            "OPC_CACHE_CLEANINVAL_24",
            "retire_packet_q.reservation_install_valid",
            "retire_packet_q.reservation_clear_valid",
            "retire_packet_q.sc_success",
            "retire_packet_q.fence_order_valid",
            "retire_packet_q.fence_i_valid",
            "retire_packet_q.cache_maintenance_valid",
            "MEMORY_TYPE_DEVICE_ORDERED",
            "EXC_ACCESS_FAULT",
        ):
            with self.subTest(token=token):
                self.assertIn(token, core)

    def test_atomic_cache_testbench_checks_success_fault_and_maintenance_paths(self) -> None:
        tb = (ROOT / "rtl" / "cpu_v01_core_atomic_cache_tb.sv").read_text(
            encoding="utf-8"
        )

        for token in (
            "module cpu_v01_core_atomic_cache_tb",
            "cpu_v01_core_atomic_cache_fixture",
            "CCSRRD C1, PCC",
            "LL48 D2, C1, D0",
            "SC48 D3, C1, D0, D4",
            "CACHE.CLEAN C1, D0, D7",
            "CSRWR ASID, D7",
            "SFENCE.VM",
            "BRK",
            "integrated atomic/cache LL48/SC48 success result mismatch",
            "integrated atomic/cache SC48 failure result mismatch",
            "integrated atomic/cache LL/SC conflict clear result mismatch",
            "integrated atomic/cache faulting LL48 reservation clear result mismatch",
            "integrated atomic/cache trap CSR fence reservation clear result mismatch",
            "integrated atomic/cache FENCE/FENCE.I ordering result mismatch",
            "integrated atomic/cache CACHE maintenance access result mismatch",
            "integrated atomic/cache CACHE device access fault result mismatch",
        ):
            with self.subTest(token=token):
                self.assertIn(token, tb)

    def test_cli_validates_and_renders_integrated_atomic_cache_json(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("RTL integrated core atomic/cache issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        by_case = {row["case_id"]: row for row in parsed}
        self.assertIn("llsc.ll48_install", by_case)
        self.assertIn("cache.cleaninval_clears_reservation", by_case)
        self.assertEqual(
            by_case["cache.clean_device_access_fault"]["retire_effects"],
            ["fault:ACCESS_FAULT", "translation_fault:DEVICE_ORDERED"],
        )

    def test_documentation_artifact_names_sources_commands_and_deferrals(self) -> None:
        text = (
            ROOT
            / "docs"
            / "implementation"
            / "rtl-integrated-core-atomic-cache.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Story: I22-S07", text)
        self.assertIn("rtl/cpu_v01_core.sv", text)
        self.assertIn("rtl/cpu_v01_core_atomic_cache_tb.sv", text)
        self.assertIn("python tools\\rtl_core_atomic_cache.py --check", text)
        self.assertIn("cpu_v01_core_atomic_cache_tb", text)
        self.assertIn("LL48", text)
        self.assertIn("SC48", text)
        self.assertIn("reservation", text)
        self.assertIn("FENCE.I", text)
        self.assertIn("CACHE.CLEANINVAL", text)
        self.assertIn("ACCESS_FAULT", text)
        self.assertIn("DEVICE_ORDERED", text)
        self.assertIn("I22-S08", text)

    def test_verilator_command_names_integrated_atomic_cache_top(self) -> None:
        command = rtl_core_atomic_cache.core_atomic_cache_verilator_command()

        self.assertIn("--top-module cpu_v01_core_atomic_cache_tb", command)
        self.assertIn("rtl/cpu_v01_core.sv", command)
        self.assertIn("rtl/cpu_v01_core_atomic_cache_tb.sv", command)


if __name__ == "__main__":
    unittest.main()
