"""I29-S04 conformance tests for FPGA external-memory policy."""

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
TOOL = ROOT / "tools" / "fpga_external_memory_policy.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_external_memory_policy, mmu


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_external_memory_policy_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaExternalMemoryPolicyTests(unittest.TestCase):
    def test_external_memory_policy_self_validation_passes(self) -> None:
        self.assertEqual(fpga_external_memory_policy.validate_fpga_external_memory_policy(ROOT), ())

    def test_profile_selects_uncacheable_no_tag_policy_and_dependency_gates(self) -> None:
        profile = fpga_external_memory_policy.fpga_external_memory_policy_profile()

        self.assertEqual(profile.story, "I29-S04")
        self.assertEqual(profile.status, "normal_uncacheable_no_tag_sidecar")
        self.assertEqual(profile.boundary_gate, "python tools\\fpga_external_memory.py --check")
        self.assertEqual(profile.ddr_wrapper_gate, "python tools\\fpga_ddr_wrapper.py --check")
        self.assertEqual(profile.firmware_gate, "python tools\\fpga_external_memory_tests.py --check")
        self.assertEqual(profile.memory_litmus_gate, "python -m unittest tests.litmus.test_i06_s04_memory_litmus")
        self.assertEqual(profile.tag_integrity_gate, "python -m unittest tests.conformance.test_i15_s02_tag_integrity")
        self.assertEqual(profile.external_window_name, "external_ddr_payload")
        self.assertEqual(profile.selected_memory_type, mmu.MEMORY_TYPE_NORMAL_UNCACHEABLE)
        self.assertEqual(profile.selected_memory_type_name, "normal_uncacheable")
        self.assertIn("CPU payload LD/ST", profile.cache_policy)
        self.assertIn("program order", profile.ordering_policy)
        self.assertIn("CLC/CSC", profile.tag_policy)
        self.assertIn("BRAM-resident", profile.firmware_policy)

    def test_rules_cover_memory_type_ordering_cache_tags_and_firmware(self) -> None:
        profile = fpga_external_memory_policy.fpga_external_memory_policy_profile()

        self.assertEqual(
            {rule.area for rule in profile.rules},
            fpga_external_memory_policy.REQUIRED_POLICY_AREAS,
        )
        for rule_name in (
            "select_normal_uncacheable",
            "preserve_program_order_for_payload",
            "no_cache_maintenance_for_cpu_payload",
            "fault_external_clc_csc",
            "payload_writes_do_not_forge_tags",
            "bram_resident_firmware_only",
        ):
            with self.subTest(rule=rule_name):
                self.assertEqual(profile.rule_by_name(rule_name).name, rule_name)

        self.assertIn("ACCESS_FAULT", profile.rule_by_name("fault_external_clc_csc").requirement)
        self.assertIn("I15-S02", profile.rule_by_name("fault_external_clc_csc").evidence)
        self.assertTrue(any("cacheable-DDR" in handoff for handoff in profile.handoffs))
        self.assertTrue(any("external-memory decoder" in blocker for blocker in profile.blockers))

    def test_policy_fixtures_prove_selected_behavior(self) -> None:
        run = fpga_external_memory_policy.run_fpga_external_memory_policy_fixtures()

        self.assertEqual(run.story, "I29-S04")
        self.assertTrue(run.passed)
        self.assertEqual(run.selected_memory_type, mmu.MEMORY_TYPE_NORMAL_UNCACHEABLE)
        self.assertEqual(run.selected_memory_type_name, "normal_uncacheable")
        self.assertFalse(run.capability_tags_supported)
        self.assertFalse(run.cache_maintenance_required_for_cpu_payload)
        self.assertFalse(run.off_bram_execution_allowed)

        memory_type = run.fixture_by_id("memory_type.external_window")
        self.assertTrue(memory_type.passed)
        self.assertIn("normal_uncacheable", memory_type.observed)

        ordering = run.fixture_by_id("ordering.payload_store_then_load")
        self.assertTrue(ordering.passed)
        self.assertIn("112233445566", ordering.observed)

        cache = run.fixture_by_id("cache_maintenance.cpu_payload_not_required")
        self.assertTrue(cache.passed)
        self.assertIn("CACHE.CLEAN=True", cache.observed)
        self.assertIn("tag=False", cache.observed)

        tag = run.fixture_by_id("tag_policy.external_capability_ops_fault")
        self.assertTrue(tag.passed)
        self.assertIn("CLC ACCESS_FAULT", tag.observed)
        self.assertIn("CSC ACCESS_FAULT", tag.observed)
        self.assertIn("dma_tag=False", tag.observed)

        firmware = run.fixture_by_id("firmware_handoff.i29_s03_payload_only")
        self.assertTrue(firmware.passed)
        self.assertIn("run_passed=True", firmware.observed)

    def test_cli_validates_json_run_rules_and_fixtures(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA external-memory policy issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I29-S04")
        self.assertEqual(parsed["selected_memory_type_name"], "normal_uncacheable")

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--run"])

        self.assertEqual(result, 0)
        run = json.loads(stream.getvalue())
        self.assertTrue(run["passed"])
        self.assertFalse(run["capability_tags_supported"])

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--rules"])

        self.assertEqual(result, 0)
        self.assertIn("fault_external_clc_csc", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--fixtures"])

        self.assertEqual(result, 0)
        self.assertIn("tag_policy.external_capability_ops_fault", stream.getvalue())

    def test_documentation_names_policy_commands_and_handoffs(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-external-memory-policy.md").read_text(
            encoding="utf-8"
        )

        for token in (
            "Story: I29-S04",
            "python tools\\fpga_external_memory_policy.py --check",
            "python tools\\fpga_external_memory.py --check",
            "python tools\\fpga_ddr_wrapper.py --check",
            "python tools\\fpga_external_memory_tests.py --check",
            "python -m unittest tests.litmus.test_i06_s04_memory_litmus",
            "python -m unittest tests.conformance.test_i15_s02_tag_integrity",
            "normal_uncacheable",
            "external_ddr_payload",
            "CACHE.CLEAN",
            "CACHE.INVAL",
            "CLC",
            "CSC",
            "ACCESS_FAULT",
            "tag sidecar",
            "BRAM-resident",
            "I29-S05",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
