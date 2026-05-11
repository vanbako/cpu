"""I32-S01 conformance tests for the interactive FPGA monitor profile."""

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
TOOL = ROOT / "tools" / "fpga_monitor_profile.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_monitor_profile, fpga_program_loader


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_monitor_profile_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaMonitorProfileTests(unittest.TestCase):
    def test_monitor_profile_self_validation_passes(self) -> None:
        self.assertEqual(fpga_monitor_profile.validate_fpga_monitor_profile(ROOT), ())

    def test_profile_names_dependencies_transports_and_commands(self) -> None:
        profile = fpga_monitor_profile.fpga_monitor_profile()

        self.assertEqual(profile.story, "I32-S01")
        self.assertEqual(profile.status, "monitor_command_profile_defined")
        self.assertEqual(profile.board, "Sipeed Tang Mega Dock with 138K SOM")
        self.assertEqual(profile.loader_gate, "python tools\\fpga_program_loader.py --check")
        self.assertEqual(profile.soc_loader_gate, "python tools\\fpga_soc_loader_handoff.py --check")

        transport_names = {transport.name for transport in profile.transports}
        self.assertIn("uart_mmio_monitor", transport_names)
        self.assertIn("jtag_assisted_monitor", transport_names)

        command_names = {command.name for command in profile.commands}
        for command in (
            "HELLO",
            "HALT",
            "RESUME",
            "LOAD_IMAGE",
            "READ_STATUS",
            "READ_MEMORY",
            "WRITE_MEMORY",
        ):
            self.assertIn(command, command_names)

    def test_memory_policy_bounds_reads_writes_and_tags(self) -> None:
        profile = fpga_monitor_profile.fpga_monitor_profile()

        self.assertIn("instruction_rom", profile.memory_policy.read_memories)
        self.assertIn("data_ram", profile.memory_policy.read_memories)
        self.assertEqual(profile.memory_policy.write_memories, ("data_ram",))
        self.assertEqual(profile.memory_policy.max_transfer_cells, fpga_program_loader.MAX_CHUNK_CELLS)
        self.assertIn("tag_bits_all_zero", profile.memory_policy.tag_policy)
        self.assertIn("tag_ram", profile.memory_policy.protected_memories)

    def test_command_audit_enforces_halt_write_protection_and_tag_policy(self) -> None:
        self.assertTrue(fpga_monitor_profile.audit_monitor_command("HELLO", halted=False).passed)

        load_running = fpga_monitor_profile.audit_monitor_command(
            "LOAD_IMAGE",
            halted=False,
            cell_count=1,
        )
        self.assertEqual(load_running.status_name, "NOT_HALTED")

        write_data = fpga_monitor_profile.audit_monitor_command(
            "WRITE_MEMORY",
            target_memory="data_ram",
            cell_count=1,
            halted=True,
        )
        self.assertTrue(write_data.passed)

        write_rom = fpga_monitor_profile.audit_monitor_command(
            "WRITE_MEMORY",
            target_memory="instruction_rom",
            cell_count=1,
            halted=True,
        )
        self.assertEqual(write_rom.status_name, "WRITE_PROTECTED")

        tagged = fpga_monitor_profile.audit_monitor_command(
            "WRITE_MEMORY",
            target_memory="data_ram",
            cell_count=1,
            halted=True,
            tag_bits_all_zero=False,
        )
        self.assertEqual(tagged.status_name, "TAG_POLICY")

        read_rom = fpga_monitor_profile.audit_monitor_command(
            "READ_MEMORY",
            target_memory="instruction_rom",
            cell_count=1,
            halted=True,
        )
        self.assertTrue(read_rom.passed)

        unknown = fpga_monitor_profile.audit_monitor_command("NOPE")
        self.assertEqual(unknown.status_name, "BAD_COMMAND")

    def test_cli_validates_json_commands_status_codes_and_audit(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA monitor profile issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["story"], "I32-S01")
        self.assertIn("commands", parsed)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--commands"])

        self.assertEqual(result, 0)
        self.assertIn("LOAD_IMAGE", stream.getvalue())
        self.assertIn("WRITE_MEMORY", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--status-codes"])

        self.assertEqual(result, 0)
        self.assertIn("BAD_COMMAND", stream.getvalue())
        self.assertIn("TAG_POLICY", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(
                [
                    "--audit-command",
                    "WRITE_MEMORY",
                    "--target-memory",
                    "data_ram",
                    "--cell-count",
                    "1",
                ]
            )

        self.assertEqual(result, 0)
        audit = json.loads(stream.getvalue())
        self.assertEqual(audit["status_name"], "OK")

    def test_documentation_names_transports_commands_status_codes_and_handoffs(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-monitor-command-profile.md").read_text(
            encoding="utf-8"
        )

        for token in (
            "Story: I32-S01",
            "python tools\\fpga_monitor_profile.py --check",
            "python tools\\fpga_program_loader.py --check",
            "python tools\\fpga_soc_loader_handoff.py --check",
            "uart_mmio_monitor",
            "jtag_assisted_monitor",
            "HELLO",
            "HALT",
            "RESUME",
            "LOAD_IMAGE",
            "READ_STATUS",
            "READ_MEMORY",
            "WRITE_MEMORY",
            "BAD_COMMAND",
            "NOT_HALTED",
            "WRITE_PROTECTED",
            "TAG_POLICY",
            "data_ram",
            "instruction_rom",
            "tag_bits_all_zero",
            "I32-S02",
            "I32-S04",
            "Acceptance Review",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
