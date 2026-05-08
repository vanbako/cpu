"""I23-S03 conformance tests for FPGA memory adapters."""

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
TOOL = ROOT / "tools" / "fpga_memory_adapters.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_memory


def load_tool_module():
    spec = importlib.util.spec_from_file_location("fpga_memory_adapters_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FpgaMemoryAdapterTests(unittest.TestCase):
    def test_fpga_memory_sources_exist_and_self_validate(self) -> None:
        self.assertEqual(fpga_memory.validate_fpga_memory_adapters(ROOT), ())
        for path in fpga_memory.FPGA_MEMORY_SOURCE_FILES:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).exists())

    def test_adapter_inventory_covers_rom_data_ram_and_tag_ram(self) -> None:
        adapters = {adapter.module: adapter for adapter in fpga_memory.fpga_memory_adapters()}

        self.assertEqual(set(adapters), {
            "cpu_v01_fpga_imem_rom",
            "cpu_v01_fpga_data_ram",
            "cpu_v01_fpga_tag_ram",
        })
        self.assertIn("readmemh", adapters["cpu_v01_fpga_imem_rom"].initialization)
        self.assertEqual(adapters["cpu_v01_fpga_data_ram"].request_ready, "always ready")
        self.assertIn("integer stores clear", adapters["cpu_v01_fpga_tag_ram"].tag_policy)

    def test_memory_rtl_defines_initialized_rom_data_ram_and_tag_clear(self) -> None:
        rtl = (ROOT / "rtl" / "cpu_v01_fpga_memories.sv").read_text(encoding="utf-8")

        for token in (
            "module cpu_v01_fpga_imem_rom",
            "parameter bit USE_INIT_FILE = 1'b0",
            "parameter string INIT_FILE = \"\"",
            "$readmemh(INIT_FILE, rom_q)",
            "rom_q[0] = 24'h05B05B",
            "assign req_ready = !rsp_valid || rsp_ready",
            "rsp_fault <= access_fault(req_addr)",
            "module cpu_v01_fpga_data_ram",
            "$readmemh(INIT_FILE, ram_q)",
            "assign req_ready = 1'b1",
            "ram_q[offset] <= req_wdata[0]",
            "rsp_rdata[0] <= req_len_cells >= 3'd1 ? ram_q[offset] : '0",
            "module cpu_v01_fpga_tag_ram",
            "tag_q[i] = 1'b0",
            "tag_q[offset] <= req_wtag",
            "rsp_rtag <= tag_q[offset]",
        ):
            with self.subTest(token=token):
                self.assertIn(token, rtl)

    def test_fpga_top_instantiates_memory_adapters(self) -> None:
        top = (ROOT / "rtl" / "cpu_v01_fpga_top.sv").read_text(encoding="utf-8")

        for token in (
            "cpu_v01_fpga_imem_rom",
            "cpu_v01_fpga_data_ram",
            "cpu_v01_fpga_tag_ram",
            ".BASE_CELL(RESET_VECTOR)",
            ".BASE_CELL(DATA_RAM_BASE)",
            ".DEPTH_CELLS(INSTRUCTION_ROM_CELLS)",
            ".DEPTH_CELLS(DATA_RAM_CELLS)",
            ".USE_INIT_FILE(USE_ROM_INIT_FILE)",
            ".USE_INIT_FILE(USE_DATA_INIT_FILE)",
            ".ENABLE_FETCH(ENABLE_FETCH)",
        ):
            with self.subTest(token=token):
                self.assertIn(token, top)

    def test_memory_testbench_checks_rom_ram_and_tag_behavior(self) -> None:
        tb = (ROOT / "rtl" / "cpu_v01_fpga_memory_tb.sv").read_text(encoding="utf-8")

        self.assertIn("module cpu_v01_fpga_memory_tb", tb)
        self.assertIn("FPGA instruction ROM tiny image contents mismatch", tb)
        self.assertIn("FPGA data RAM read/write contents mismatch", tb)
        self.assertIn("FPGA tag RAM did not preserve CSC-style tag write", tb)
        self.assertIn("FPGA tag RAM did not clear tag on integer-store clear write", tb)
        self.assertIn("24'h00CAFE", tb)
        self.assertIn("24'h0BEEF0", tb)

    def test_cli_validates_and_renders_adapter_inventory_json(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main(["--check"])

        self.assertEqual(result, 0)
        self.assertIn("FPGA memory adapter issues: 0", stream.getvalue())

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        modules = {row["module"] for row in parsed}
        self.assertIn("cpu_v01_fpga_imem_rom", modules)
        self.assertIn("cpu_v01_fpga_data_ram", modules)
        self.assertIn("cpu_v01_fpga_tag_ram", modules)

    def test_documentation_artifact_names_sources_commands_and_deferrals(self) -> None:
        text = (ROOT / "docs" / "implementation" / "fpga-memory-adapters.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I23-S03", text)
        self.assertIn("rtl/cpu_v01_fpga_memories.sv", text)
        self.assertIn("rtl/cpu_v01_fpga_memory_tb.sv", text)
        self.assertIn("python tools\\fpga_memory_adapters.py --check", text)
        self.assertIn("cpu_v01_fpga_imem_rom", text)
        self.assertIn("cpu_v01_fpga_data_ram", text)
        self.assertIn("cpu_v01_fpga_tag_ram", text)
        self.assertIn("hex24-cells-v1", text)
        self.assertIn("readmemh", text)
        self.assertIn("integer-store clear", text)
        self.assertIn("I23-S04", text)

    def test_verilator_commands_name_adapter_and_top_sources(self) -> None:
        adapter_command = fpga_memory.fpga_memory_verilator_command()
        top_command = fpga_memory.fpga_top_with_memory_verilator_command()

        self.assertIn("--top-module cpu_v01_fpga_memory_tb", adapter_command)
        self.assertIn("rtl/cpu_v01_pkg.sv", adapter_command)
        self.assertIn("rtl/cpu_v01_fpga_memories.sv", adapter_command)
        self.assertIn("rtl/cpu_v01_fpga_memory_tb.sv", adapter_command)

        self.assertIn("--top-module cpu_v01_fpga_top_tb", top_command)
        self.assertIn("rtl/cpu_v01_core.sv", top_command)
        self.assertIn("rtl/cpu_v01_fpga_memories.sv", top_command)
        self.assertIn("rtl/cpu_v01_fpga_top.sv", top_command)


if __name__ == "__main__":
    unittest.main()
