"""I21-S03 conformance tests for atomic/cache RTL coverage."""

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
TOOL = ROOT / "tools" / "rtl_atomic_cache_slice.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import opcodes, rtl_atomic_cache, sv_contract


def load_tool_module():
    spec = importlib.util.spec_from_file_location("rtl_atomic_cache_slice_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RtlAtomicCacheSliceTests(unittest.TestCase):
    def test_rtl_atomic_cache_sources_exist_and_self_validate(self) -> None:
        self.assertEqual(rtl_atomic_cache.validate_rtl_atomic_cache_slice(ROOT), ())
        for path in rtl_atomic_cache.RTL_ATOMIC_CACHE_SOURCE_FILES:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).exists())

    def test_projection_covers_llsc_reservation_fence_and_cache_cases(self) -> None:
        rows = rtl_atomic_cache.atomic_cache_coverage_rows()
        by_case = {row.case_id: row for row in rows}

        self.assertEqual(by_case["llsc.ll48_install"].reservation_effect, "install")
        self.assertTrue(by_case["llsc.ll48_install"].reservation_after)
        self.assertEqual(
            by_case["llsc.sc48_success_store_clear"].memory_effect,
            "store_tag_clear",
        )
        self.assertFalse(by_case["llsc.sc48_success_store_clear"].reservation_after)
        self.assertEqual(by_case["llsc.sc48_failure_clear"].memory_effect, "none")
        self.assertEqual(
            by_case["llsc.conflicting_store_clear"].reservation_effect,
            "conflict_clear",
        )
        self.assertEqual(
            by_case["llsc.faulting_ll48_clear"].fault_cause,
            "ALIGN_FAULT",
        )
        self.assertEqual(by_case["ordering.fence"].cache_effect, "fence_order")
        self.assertEqual(by_case["ordering.fence_i"].cache_effect, "fence_i")
        self.assertEqual(by_case["cache.inval_clears_reservation"].cache_effect, "inval")
        self.assertEqual(
            by_case["cache.clean_device_access_fault"].fault_cause,
            "ACCESS_FAULT",
        )
        self.assertEqual(
            by_case["cache.clean_device_access_fault"].fault_tval,
            rtl_atomic_cache.DEVICE_PA,
        )

    def test_projection_covers_required_mnemonics_and_deferred_work(self) -> None:
        covered = {row.mnemonic for row in rtl_atomic_cache.atomic_cache_coverage_rows()}

        for mnemonic in rtl_atomic_cache.ATOMIC_CACHE_MNEMONICS:
            with self.subTest(mnemonic=mnemonic):
                self.assertIn(mnemonic, covered)
                self.assertEqual(opcodes.opcode_form_for(mnemonic).size.bits, 24)

        for mnemonic in rtl_atomic_cache.DEFERRED_MNEMONICS:
            with self.subTest(deferred=mnemonic):
                self.assertNotIn(mnemonic, covered)

    def test_package_and_sv_contract_expose_reservation_ordering_and_cache_fields(self) -> None:
        package = (ROOT / "rtl" / "cpu_v01_pkg.sv").read_text(encoding="utf-8")

        for token in (
            "OPC_LL48_24",
            "OPC_SC48_24",
            "OPC_FENCE_24",
            "OPC_FENCE_I_24",
            "OPC_CACHE_CLEAN_24",
            "OPC_CACHE_INVAL_24",
            "OPC_CACHE_CLEANINVAL_24",
            "CACHE_MAINT_CLEAN",
            "CACHE_MAINT_INVAL",
            "CACHE_MAINT_CLEANINVAL",
            "reservation_install_valid",
            "reservation_clear_valid",
            "reservation_word_address",
            "reservation_memory_type",
            "sc_success",
            "fence_order_valid",
            "fence_i_valid",
            "cache_maintenance_valid",
            "cache_maintenance_kind",
            "cache_maintenance_address",
            "cache_maintenance_length",
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
                "reservation_install_valid",
                "reservation_clear_valid",
                "reservation_word_address",
                "reservation_memory_type",
                "sc_success",
                "fence_order_valid",
                "fence_i_valid",
                "cache_maintenance_valid",
                "cache_maintenance_kind",
                "cache_maintenance_address",
                "cache_maintenance_length",
            },
        )

    def test_atomic_cache_core_names_states_and_effect_paths(self) -> None:
        core = (ROOT / "rtl" / "cpu_v01_atomic_cache_core.sv").read_text(
            encoding="utf-8"
        )

        for token in (
            "ST_LL48",
            "ST_SC48_SUCCESS",
            "ST_SC48_FAILURE",
            "ST_CONFLICT_STORE_CLEAR",
            "ST_FAULTING_LL48_CLEAR",
            "ST_CSR_CLEAR",
            "ST_TRAP_CLEAR",
            "ST_SFENCE_CLEAR",
            "ST_FENCE",
            "ST_FENCE_I",
            "ST_CACHE_CLEAN",
            "ST_CACHE_INVAL",
            "ST_CACHE_CLEANINVAL",
            "ST_CACHE_DEVICE_FAULT",
            "retire_packet_q.reservation_install_valid <= 1'b1",
            "retire_packet_q.reservation_clear_valid <= 1'b1",
            "retire_packet_q.sc_success <= success",
            "retire_packet_q.fence_order_valid <= 1'b1",
            "retire_packet_q.fence_i_valid <= 1'b1",
            "retire_packet_q.cache_maintenance_valid <= 1'b1",
            "start_fault_packet(OPC_CACHE_CLEAN_24, EXC_ACCESS_FAULT, DEVICE_PA)",
        ):
            with self.subTest(token=token):
                self.assertIn(token, core)

    def test_testbench_checks_i21_s03_coverage_groups(self) -> None:
        tb = (ROOT / "rtl" / "cpu_v01_atomic_cache_tb.sv").read_text(
            encoding="utf-8"
        )

        self.assertIn("LL48/SC48 success result mismatch", tb)
        self.assertIn("SC48 failure result mismatch", tb)
        self.assertIn("LL/SC conflict clear result mismatch", tb)
        self.assertIn("faulting LL48 reservation clear result mismatch", tb)
        self.assertIn("trap CSR fence reservation clear result mismatch", tb)
        self.assertIn("FENCE/FENCE.I ordering result mismatch", tb)
        self.assertIn("CACHE maintenance access result mismatch", tb)
        self.assertIn("CACHE device access fault result mismatch", tb)

    def test_cli_validates_and_renders_atomic_cache_projection_json(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("RTL atomic/cache slice issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        case_ids = {row["case_id"] for row in parsed}
        self.assertIn("llsc.ll48_install", case_ids)
        self.assertIn("llsc.sc48_success_store_clear", case_ids)
        self.assertIn("cache.clean_device_access_fault", case_ids)

    def test_documentation_artifact_names_sources_commands_and_deferrals(self) -> None:
        text = (
            ROOT / "docs" / "implementation" / "rtl-atomic-cache-slice.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Story: I21-S03", text)
        self.assertIn("rtl/cpu_v01_atomic_cache_core.sv", text)
        self.assertIn("python tools\\rtl_atomic_cache_slice.py --check", text)
        self.assertIn("LL48", text)
        self.assertIn("SC48", text)
        self.assertIn("CACHE.CLEANINVAL", text)
        self.assertIn("ACCESS_FAULT", text)
        self.assertIn("remain for later stories", text)


if __name__ == "__main__":
    unittest.main()
