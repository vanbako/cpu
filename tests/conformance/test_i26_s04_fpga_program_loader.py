"""I26-S04 conformance tests for the FPGA program loader."""

from __future__ import annotations

import contextlib
import importlib.util
from io import StringIO
import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
TOOL = ROOT / "tools" / "fpga_program_loader.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_debug_status, fpga_program_loader


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_program_loader_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaProgramLoaderTests(unittest.TestCase):
    def test_program_loader_self_validation_passes(self) -> None:
        self.assertEqual(fpga_program_loader.validate_fpga_program_loader(ROOT), ())

    def test_profile_names_dependencies_transports_and_bounds(self) -> None:
        profile = fpga_program_loader.fpga_program_loader_profile()

        self.assertEqual(profile.story, "I26-S04")
        self.assertEqual(profile.bram_image_gate, "python tools\\fpga_bram_images.py --check")
        self.assertEqual(profile.uart_mmio_gate, "python tools\\fpga_uart_mmio.py --check")
        self.assertEqual(profile.status_stream_gate, "python tools\\fpga_uart_status_streamer.py --check")
        self.assertEqual(profile.debug_packet_gate, "python tools\\fpga_debug_status_packet.py --check")
        self.assertEqual(set(profile.transports), {"uart_mmio", "jtag_assisted"})
        self.assertEqual(profile.target_memory, "data_ram")
        self.assertEqual(profile.target_base_cell, 0x00010000)
        self.assertEqual(profile.target_size_cells, 0x1000)
        self.assertEqual(profile.max_chunk_cells, 16)
        self.assertEqual(profile.status_codes["OK"], 0)
        self.assertEqual(profile.status_codes["TAG_POLICY"], 0x2605)

    def test_successful_load_installs_ram_clears_tags_and_reports_status(self) -> None:
        state = fpga_program_loader.fpga_program_loader_state()
        request = fpga_program_loader.program_load_request_for_program(
            "relocation.branch_call_data_fpga"
        )

        result = state.install(request)

        self.assertTrue(result.passed)
        self.assertEqual(result.installed_cells, 0x1000)
        self.assertEqual(result.first_loaded_cell, 0x00010000)
        self.assertEqual(result.last_loaded_cell, 0x00010FFF)
        self.assertEqual(state.loaded_program_id, "relocation.branch_call_data_fpga")
        self.assertEqual(sum(state.tag_ram), 0)
        self.assertIn("I26-S04 LOAD OK", result.report.uart_message)
        self.assertEqual(result.report.uart_bytes, tuple(result.report.uart_message.encode("ascii")))
        self.assertEqual(result.report.debug_packet.pass_fail_state, 1)
        self.assertEqual(result.report.debug_packet.fault_code, 0)
        self.assertEqual(fpga_debug_status.validate_debug_status_packet(result.report.debug_packet), ())
        self.assertNotEqual(tuple(state.data_ram[:2]), (0, 0))

    def test_malformed_loads_are_rejected_without_writes(self) -> None:
        good = fpga_program_loader.program_load_request_for_program(
            "relocation.branch_call_data_fpga"
        )
        fixtures = (
            replace(good, program_id="missing.program"),
            replace(good, manifest_image_sha256="0" * 64),
            replace(good, target_memory="instruction_rom"),
            replace(good, base_cell=0x00010FFF),
            replace(good, tag_bits=(1,) + good.tag_bits[1:]),
            replace(good, max_observed_chunk_cells=17),
        )
        expected_codes = {
            fpga_program_loader.LOAD_STATUS_BAD_PROGRAM,
            fpga_program_loader.LOAD_STATUS_BAD_HASH,
            fpga_program_loader.LOAD_STATUS_BAD_TARGET,
            fpga_program_loader.LOAD_STATUS_BOUNDS,
            fpga_program_loader.LOAD_STATUS_TAG_POLICY,
            fpga_program_loader.LOAD_STATUS_OVERRUN,
        }

        observed_codes = set()
        for request in fixtures:
            with self.subTest(request=request.as_dict()):
                state = fpga_program_loader.fpga_program_loader_state()
                result = state.install(request)
                self.assertFalse(result.passed)
                self.assertEqual(result.installed_cells, 0)
                self.assertEqual(state.loaded_program_id, "")
                self.assertEqual(sum(state.data_ram), 0)
                self.assertEqual(sum(state.tag_ram), 0)
                self.assertIn("LOAD ERR", result.report.uart_message)
                self.assertEqual(result.report.debug_packet.pass_fail_state, 4)
                self.assertTrue(
                    result.report.debug_packet.flags
                    & fpga_debug_status.debug_status_flag_mask("fault_valid")
                )
                observed_codes.add(result.report.status_code)

        self.assertEqual(observed_codes, expected_codes)

    def test_cli_validates_lists_runs_rejections_and_json(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA program loader issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--list"])

        self.assertEqual(result, 0)
        self.assertIn("relocation.branch_call_data_fpga", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--run", "relocation.branch_call_data_fpga"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["status"], "passed")
        self.assertEqual(parsed["installed_cells"], 0x1000)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--rejections"])

        self.assertEqual(result, 0)
        parsed_rejections = json.loads(stream.getvalue())
        self.assertGreaterEqual(len(parsed_rejections), 6)
        self.assertTrue(all(item["status"] == "failed" for item in parsed_rejections))

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed_profile = json.loads(stream.getvalue())
        self.assertEqual(parsed_profile["story"], "I26-S04")
        self.assertIn("plans", parsed_profile)

    def test_documentation_names_protocol_rejection_and_handoffs(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-program-loader.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I26-S04", text)
        self.assertIn("python tools\\fpga_program_loader.py --check", text)
        self.assertIn("python tools\\fpga_bram_images.py --check", text)
        self.assertIn("python tools\\fpga_uart_mmio.py --check", text)
        self.assertIn("python tools\\fpga_uart_status_streamer.py --check", text)
        self.assertIn("python tools\\fpga_debug_status_packet.py --check", text)
        for token in (
            "bounded RAM image",
            "data_ram",
            "tag_ram",
            "LOAD_BEGIN",
            "LOAD_CHUNK",
            "LOAD_COMMIT",
            "BAD_HASH",
            "TAG_POLICY",
            "python tools\\fpga_program_loader.py --run",
            "python tools\\fpga_program_loader.py --rejections",
            "I30-S04",
            "I32-S01",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
