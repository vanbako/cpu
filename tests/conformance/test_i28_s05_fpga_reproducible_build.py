"""I28-S05 conformance tests for the reproducible FPGA build profile."""

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
TOOL = ROOT / "tools" / "fpga_reproducible_build.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_reproducible_build


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_reproducible_build_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaReproducibleBuildTests(unittest.TestCase):
    def test_reproducible_build_self_validation_passes(self) -> None:
        self.assertEqual(fpga_reproducible_build.validate_fpga_reproducible_build(ROOT), ())

    def test_profile_names_target_defaults_gates_and_blocker_status(self) -> None:
        profile = fpga_reproducible_build.fpga_reproducible_build_profile()

        self.assertEqual(profile.story, "I28-S05")
        self.assertEqual(profile.status, "documented_blocker")
        self.assertEqual(profile.board, "Sipeed Tang Mega 138K Dock")
        self.assertEqual(profile.device, "GW5AST-LV138PG484A")
        self.assertEqual(profile.package, "PBG484A")
        self.assertEqual(profile.top_module, "cpu_v01_fpga_top")
        self.assertEqual(profile.build_root.as_posix(), "build/fpga/tang_mega_138k/first_test")
        self.assertEqual(profile.selected_clock_profile, "debug_direct_25mhz")
        self.assertEqual(profile.selected_debug_default_hz, 25_000_000)
        self.assertEqual(profile.selected_release_default_hz, 25_000_000)
        self.assertIn("i28_s05_reproducible_build_manifest.json", profile.manifest_path.as_posix())
        for gate in (
            "python tools\\fpga_board_identity.py --check",
            "python tools\\fpga_constraints_overlay.py --check",
            "python tools\\fpga_gowin_reports.py --check",
            "python tools\\fpga_reset_cdc.py --check",
            "python tools\\fpga_frequency_margin.py --check",
        ):
            self.assertIn(gate, profile.gates)

    def test_required_tools_and_artifacts_cover_reproducibility_contract(self) -> None:
        profile = fpga_reproducible_build.fpga_reproducible_build_profile()
        tools = {tool.name: tool for tool in profile.tools}
        artifacts = {artifact.name: artifact for artifact in profile.artifacts}

        for tool in ("Gowin EDA", "Gowin Programmer", "Verilator", "Python"):
            with self.subTest(tool=tool):
                self.assertIn(tool, tools)
                self.assertTrue(tools[tool].required)
                self.assertIn("version", tools[tool].version_evidence)

        for artifact in (
            "device_package_evidence",
            "constraints_cst_sdc",
            "gowin_tcl",
            "gowin_reports",
            "bitstream_identity",
            "clock_profile",
            "reset_cdc_audit",
            "frequency_margin",
            "board_evidence",
        ):
            with self.subTest(artifact=artifact):
                self.assertIn(artifact, artifacts)
                self.assertTrue(artifacts[artifact].required)

        self.assertIn("bitstream_sha256", artifacts["bitstream_identity"].purpose)
        self.assertIn("fpga_first_board_archive.py", artifacts["board_evidence"].producer_gate)
        self.assertEqual(artifacts["frequency_margin"].captured_status, "documented_blocker")

    def test_manifest_template_contains_version_hash_clock_and_board_fields(self) -> None:
        template = json.loads(fpga_reproducible_build.reproducible_build_manifest_template())

        self.assertEqual(template["story"], "I28-S05")
        self.assertEqual(template["status"], "documented_blocker")
        self.assertIn("repository_commit", template)
        self.assertIn("gowin_eda_version", template)
        self.assertIn("gowin_programmer_version", template)
        self.assertIn("verilator_version", template)
        self.assertIn("python_version", template)
        self.assertIn("bitstream_sha256", template)
        self.assertEqual(template["selected_clock_profile"], "debug_direct_25mhz")
        self.assertIn("board_evidence_path", template)

    def test_cli_validates_json_template_steps_and_artifacts(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA reproducible build issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I28-S05")
        self.assertEqual(parsed["status"], "documented_blocker")

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--template"])

        self.assertEqual(result, 0)
        self.assertIn("bitstream_sha256", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--steps"])

        self.assertEqual(result, 0)
        self.assertIn("gw_sh build/fpga/tang_mega_138k/first_test/run_gowin.tcl", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--artifacts"])

        self.assertEqual(result, 0)
        self.assertIn("device_package_evidence", stream.getvalue())
        self.assertIn("bitstream_identity", stream.getvalue())

    def test_documentation_names_manifest_tools_artifacts_and_handoffs(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-reproducible-build.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I28-S05", text)
        self.assertIn("python tools\\fpga_reproducible_build.py --check", text)
        self.assertIn("python tools\\fpga_reset_cdc.py --check", text)
        self.assertIn("python tools\\fpga_gowin_reports.py --check", text)
        self.assertIn("python tools\\fpga_frequency_margin.py --check", text)
        self.assertIn("tool version", text)
        self.assertIn("device/package", text)
        self.assertIn("constraints", text)
        self.assertIn("Tcl", text)
        self.assertIn("reports", text)
        self.assertIn("bitstream_sha256", text)
        self.assertIn("board evidence", text)
        self.assertIn("debug_direct_25mhz", text)
        self.assertIn("documented_blocker", text)
        self.assertIn("I24-S05", text)
        self.assertIn("I29", text)


if __name__ == "__main__":
    unittest.main()
