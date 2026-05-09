"""I26-S03 conformance tests for FPGA image update flow."""

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
TOOL = ROOT / "tools" / "fpga_image_update_flow.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_gowin_build, fpga_image_update_flow


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_image_update_flow_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def passed_gowin_audit() -> fpga_gowin_build.GowinReportAudit:
    return fpga_gowin_build.GowinReportAudit(
        status="passed",
        message="passed",
        build_root="build/fpga/tang_mega_138k/first_test",
        identity_status="confirmed",
        constraints_status="confirmed",
        missing_reports=(),
        token_issues=(),
        failure_markers=(),
        bitstreams=("build/fpga/tang_mega_138k/first_test/impl/pnr/first.fs",),
        actions=(),
    )


class FpgaImageUpdateFlowTests(unittest.TestCase):
    def test_image_update_flow_self_validation_passes(self) -> None:
        self.assertEqual(fpga_image_update_flow.validate_fpga_image_update_flow(ROOT), ())

    def test_profile_plans_cover_programs_and_default_to_gowin_rebuild(self) -> None:
        profile = fpga_image_update_flow.fpga_image_update_profile()

        self.assertEqual(profile.story, "I26-S03")
        self.assertEqual(profile.bram_image_gate, "python tools\\fpga_bram_images.py --check")
        self.assertEqual(profile.gowin_build_gate, "python tools\\fpga_gowin_build.py --check")
        self.assertIn("gowin_rebuild", profile.supported_modes)
        self.assertIn("memory_update", profile.supported_modes)
        self.assertGreaterEqual(len(profile.plans), 3)
        for plan in profile.plans:
            self.assertEqual(plan.default_mode, "gowin_rebuild")
            self.assertEqual(plan.memory_update_status, "blocked_until_tool_support_verified")
            self.assertIn("rom.mem", plan.required_artifacts)
            self.assertIn("data.mem", plan.required_artifacts)
            self.assertIn("tags.mem", plan.required_artifacts)
            self.assertEqual(len(plan.image_sha256), 64)
            self.assertTrue(any("fpga_bram_images.py --write" in command for command in plan.rebuild_commands))
            self.assertTrue(any("fpga_gowin_build.py --audit-reports" in command for command in plan.rebuild_commands))

    def test_complete_rebuild_evidence_is_accepted(self) -> None:
        plan = fpga_image_update_flow.fpga_image_update_profile().plan_by_program_id(
            "reset_smoke.reset_to_trap_fpga"
        )
        record = fpga_image_update_flow.parse_image_update_evidence(
            "\n".join(
                (
                    "story=I26-S03",
                    f"program_id={plan.program_id}",
                    f"image_sha256={plan.image_sha256}",
                    "update_mode=gowin_rebuild",
                    "bram_images_verified=yes",
                    "generated_artifacts=rom.mem,data.mem,tags.mem",
                    "gowin_build_root=build/fpga/tang_mega_138k/first_test",
                    "gowin_audit_status=passed",
                    "bitstream_path=build/fpga/tang_mega_138k/first_test/impl/pnr/first.fs",
                    "bitstream_sha256=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
                    "memory_update_support_verified=no",
                    "memory_update_tool=none",
                    "memory_update_log=none",
                    "image_identity_recorded=yes",
                    "report_path=docs/implementation/evidence/i26_s03_image_update_report.json",
                    "recorded_at=2026-05-09T00:00:00",
                )
            )
        )

        audit = fpga_image_update_flow.audit_image_update(record, gowin_audit=passed_gowin_audit())

        self.assertTrue(audit.passed)
        self.assertEqual(audit.status, "passed")

    def test_wrong_hash_fails_and_missing_gowin_audit_blocks_rebuild(self) -> None:
        plan = fpga_image_update_flow.fpga_image_update_profile().plans[0]
        record = fpga_image_update_flow.parse_image_update_evidence(
            fpga_image_update_flow.image_update_evidence_template(plan.program_id)
            .replace(f"image_sha256={plan.image_sha256}", "image_sha256=" + "0" * 64)
            .replace("bram_images_verified=", "bram_images_verified=yes")
            .replace("generated_artifacts=", "generated_artifacts=rom.mem,data.mem,tags.mem")
            .replace("gowin_audit_status=", "gowin_audit_status=blocked")
            .replace("bitstream_path=", "bitstream_path=build/fpga/tang_mega_138k/first_test/impl/pnr/first.fs")
            .replace("bitstream_sha256=", "bitstream_sha256=" + "1" * 64)
            .replace("image_identity_recorded=", "image_identity_recorded=yes")
            .replace("report_path=", "report_path=docs/implementation/evidence/i26_s03_report.json")
            .replace("recorded_at=", "recorded_at=2026-05-09T00:00:00")
        )

        audit = fpga_image_update_flow.audit_image_update(record)

        self.assertEqual(audit.status, "failed")
        self.assertIn("image_sha256 does not match", " ".join(audit.identity_issues))

        record = fpga_image_update_flow.parse_image_update_evidence(
            fpga_image_update_flow.image_update_evidence_template(plan.program_id)
            .replace("bram_images_verified=", "bram_images_verified=yes")
            .replace("generated_artifacts=", "generated_artifacts=rom.mem,data.mem,tags.mem")
            .replace("gowin_audit_status=", "gowin_audit_status=blocked")
            .replace("bitstream_path=", "bitstream_path=build/fpga/tang_mega_138k/first_test/impl/pnr/first.fs")
            .replace("bitstream_sha256=", "bitstream_sha256=" + "1" * 64)
            .replace("image_identity_recorded=", "image_identity_recorded=yes")
            .replace("report_path=", "report_path=docs/implementation/evidence/i26_s03_report.json")
            .replace("recorded_at=", "recorded_at=2026-05-09T00:00:00")
        )

        audit = fpga_image_update_flow.audit_image_update(record)

        self.assertEqual(audit.status, "blocked")
        self.assertIn("gowin_audit_status must be passed", " ".join(audit.artifact_issues))

    def test_memory_update_mode_is_blocked_until_support_is_verified(self) -> None:
        plan = fpga_image_update_flow.fpga_image_update_profile().plans[0]
        record = fpga_image_update_flow.parse_image_update_evidence(
            fpga_image_update_flow.image_update_evidence_template(plan.program_id)
            .replace("update_mode=gowin_rebuild", "update_mode=memory_update")
            .replace("bram_images_verified=", "bram_images_verified=yes")
            .replace("generated_artifacts=", "generated_artifacts=rom.mem,data.mem,tags.mem")
            .replace("bitstream_sha256=", "bitstream_sha256=" + "2" * 64)
            .replace("image_identity_recorded=", "image_identity_recorded=yes")
            .replace("report_path=", "report_path=docs/implementation/evidence/i26_s03_report.json")
            .replace("recorded_at=", "recorded_at=2026-05-09T00:00:00")
        )

        audit = fpga_image_update_flow.audit_image_update(record)

        self.assertEqual(audit.status, "blocked")
        self.assertIn("memory-update mode is blocked", " ".join(audit.artifact_issues))

    def test_cli_check_json_plan_template_and_audit(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA image update issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I26-S03")
        self.assertIn("plans", parsed)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--plan"])

        self.assertEqual(result, 0)
        self.assertIn("gowin_rebuild", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--template", "reset_smoke.reset_to_trap_fpga"])

        self.assertEqual(result, 0)
        self.assertIn("story=I26-S03", stream.getvalue())
        self.assertIn("program_id=reset_smoke.reset_to_trap_fpga", stream.getvalue())

    def test_documentation_names_modes_commands_artifacts_and_handoffs(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-image-update-flow.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I26-S03", text)
        self.assertIn("python tools\\fpga_image_update_flow.py --check", text)
        self.assertIn("python tools\\fpga_bram_images.py --check", text)
        self.assertIn("python tools\\fpga_gowin_build.py --check", text)
        self.assertIn("python tools\\fpga_image_update_flow.py --template", text)
        self.assertIn("python tools\\fpga_image_update_flow.py --audit-evidence", text)
        self.assertIn("gowin_rebuild", text)
        self.assertIn("memory_update", text)
        self.assertIn("rom.mem", text)
        self.assertIn("data.mem", text)
        self.assertIn("tags.mem", text)
        self.assertIn("image_sha256", text)
        self.assertIn("bitstream_sha256", text)
        self.assertIn("I24-S04", text)
        self.assertIn("I26-S04", text)


if __name__ == "__main__":
    unittest.main()
