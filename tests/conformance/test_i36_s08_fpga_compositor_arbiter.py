"""I36-S08 conformance tests for CPU/compositor memory arbitration."""

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
TOOL = ROOT / "tools" / "fpga_compositor_arbiter.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_compositor_arbiter


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_compositor_arbiter_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaCompositorArbiterTests(unittest.TestCase):
    def test_compositor_arbiter_self_validation_passes(self) -> None:
        self.assertEqual(fpga_compositor_arbiter.validate_fpga_compositor_arbiter(ROOT), ())

    def test_profile_names_dependencies_policy_counters_and_handoffs(self) -> None:
        profile = fpga_compositor_arbiter.fpga_compositor_arbiter_profile()

        self.assertEqual(profile.story, "I36-S08")
        self.assertEqual(profile.fetch_gate, "python tools\\fpga_compositor_fetch.py --check")
        self.assertEqual(profile.decoder_gate, "python tools\\fpga_soc_top_decoder.py --check")
        self.assertEqual(profile.ddr_wrapper_gate, "python tools\\fpga_ddr_wrapper.py --check")
        self.assertEqual(profile.video_mmio_gate, "python tools\\fpga_video_mmio.py --check")
        self.assertEqual(profile.arbiter_module, "cpu_v01_fpga_compositor_mem_arbiter")
        self.assertEqual(profile.testbench_module, "cpu_v01_fpga_compositor_mem_arbiter_tb")
        self.assertIn("CPU-first", profile.arbitration_policy)
        self.assertIn("single-outstanding", profile.arbitration_policy)
        self.assertIn("cpu_data_mmio", profile.request_sources)
        self.assertIn("compositor_scanout_read", profile.request_sources)
        for counter in (
            "cpu_grant_count",
            "video_grant_count",
            "video_starvation_count",
            "video_underflow_count",
            "descriptor_update_count",
        ):
            self.assertIn(counter, profile.counters)
        self.assertIn("I36-S06", " ".join(profile.handoffs))
        self.assertIn("I36-S07", " ".join(profile.handoffs))
        self.assertIn("multi_outstanding_ddr_scheduler", profile.non_goals)

    def test_demo_grants_cpu_first_then_video_and_reports_faults_underflow(self) -> None:
        run = fpga_compositor_arbiter.simulate_arbitration_demo()

        self.assertEqual(run.steps[0].grant, fpga_compositor_arbiter.OWNER_CPU)
        self.assertTrue(run.steps[0].cpu_ready)
        self.assertFalse(run.steps[0].video_ready)
        self.assertTrue(run.steps[0].video_starved)
        self.assertTrue(run.steps[0].descriptor_update_seen)
        self.assertIsNotNone(run.steps[0].memory_request)
        self.assertTrue(run.steps[0].memory_request.write)
        self.assertEqual(run.steps[1].grant, fpga_compositor_arbiter.OWNER_VIDEO)
        self.assertTrue(run.steps[1].video_response_valid)
        self.assertTrue(run.steps[2].cpu_fault)
        self.assertGreaterEqual(run.video_starvation_count, 3)
        self.assertGreaterEqual(run.video_underflow_count, 1)
        self.assertEqual(run.descriptor_update_count, 1)

    def test_arbitration_state_rejects_misrouted_requests(self) -> None:
        state = fpga_compositor_arbiter.ArbitrationState()

        with self.assertRaises(ValueError):
            state.step(
                cpu_request=fpga_compositor_arbiter.ArbitrationRequest(
                    fpga_compositor_arbiter.OWNER_VIDEO,
                    addr_cell=0,
                    write=False,
                )
            )

        with self.assertRaises(ValueError):
            state.step(
                video_request=fpga_compositor_arbiter.ArbitrationRequest(
                    fpga_compositor_arbiter.OWNER_CPU,
                    addr_cell=0,
                    write=False,
                )
            )

    def test_rtl_testbench_names_arbitration_fault_and_counter_contract(self) -> None:
        rtl = (ROOT / "rtl" / "cpu_v01_fpga_compositor_mem_arbiter.sv").read_text(
            encoding="utf-8"
        )
        tb = (ROOT / "rtl" / "cpu_v01_fpga_compositor_mem_arbiter_tb.sv").read_text(
            encoding="utf-8"
        )

        for token in (
            "module cpu_v01_fpga_compositor_mem_arbiter",
            "CPU_FIRST_SINGLE_OUTSTANDING",
            "cpu_req_mmio_i",
            "video_req_valid_i",
            "descriptor_update_i",
            "assign cpu_req_ready_o =",
            "assign video_req_ready_o =",
            "assign mem_req_owner_o =",
            "video_starvation_count_o",
            "video_underflow_count_o",
            "descriptor_update_count_o",
            "cpu_rsp_fault_o <= mem_rsp_error_i",
            "video_rsp_error_o <= mem_rsp_error_i",
        ):
            with self.subTest(token=token):
                self.assertIn(token, rtl)

        for token in (
            "module cpu_v01_fpga_compositor_mem_arbiter_tb",
            "cpu_v01_fpga_compositor_mem_arbiter dut",
            "compositor arbiter did not grant CPU before video",
            "compositor arbiter did not route video response",
            "compositor arbiter did not preserve CPU fault response",
            "compositor arbiter did not expose video starvation counter",
            "compositor arbiter did not count descriptor update",
            "compositor arbiter did not report underflow after bounded video stall",
        ):
            with self.subTest(token=token):
                self.assertIn(token, tb)

    def test_cli_validates_json_demo_counters_and_plan(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA compositor arbiter issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I36-S08")
        self.assertIn("video_underflow_count", parsed["counters"])

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--demo"])

        self.assertEqual(result, 0)
        demo = json.loads(stream.getvalue())
        self.assertEqual(demo["steps"][0]["grant"], "cpu")
        self.assertGreaterEqual(demo["video_underflow_count"], 1)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--counters"])

        self.assertEqual(result, 0)
        self.assertIn("descriptor_update_count", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--plan"])

        self.assertEqual(result, 0)
        self.assertIn("cpu_v01_fpga_compositor_mem_arbiter_tb", stream.getvalue())

    def test_documentation_names_arbitration_contract_and_handoffs(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-compositor-arbiter.md").read_text(
            encoding="utf-8"
        )

        for token in (
            "Story: I36-S08",
            "python tools\\fpga_compositor_arbiter.py --check",
            "python tools\\fpga_compositor_fetch.py --check",
            "python tools\\fpga_soc_top_decoder.py --check",
            "python tools\\fpga_ddr_wrapper.py --check",
            "python tools\\fpga_video_mmio.py --check",
            "cpu_v01_fpga_compositor_mem_arbiter",
            "CPU-first",
            "single-outstanding",
            "video_starvation_count",
            "video_underflow_count",
            "descriptor_update_count",
            "CPU fault responses",
            "simultaneous CPU writes",
            "descriptor updates",
            "scanout fetches",
            "I36-S06",
            "I36-S07",
            "Acceptance Review",
        ):
            with self.subTest(token=token):
                self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
