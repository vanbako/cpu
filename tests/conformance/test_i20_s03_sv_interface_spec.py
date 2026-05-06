"""I20-S03 conformance tests for the generated SystemVerilog interface spec."""

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
TOOL = ROOT / "tools" / "sv_interface_spec.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import capabilities as caps
from cpu_v01 import cells, csrs, opcodes, sv_contract


def load_tool_module():
    spec = importlib.util.spec_from_file_location("sv_interface_spec_tool", TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SystemVerilogInterfaceSpecTests(unittest.TestCase):
    def test_contract_self_validation_passes_and_covers_required_surfaces(self) -> None:
        contract = sv_contract.systemverilog_contract()

        self.assertEqual(sv_contract.validate_systemverilog_contract(contract), ())
        rendered = json.loads(sv_contract.systemverilog_contract_json())
        self.assertEqual(rendered["package_name"], "cpu_v01_pkg")

    def test_constants_are_derived_from_semantic_model(self) -> None:
        constants = {
            constant.name: constant
            for constant in sv_contract.systemverilog_contract().constants
        }

        self.assertEqual(constants["CELL_BITS"].value, cells.CELL_BITS)
        self.assertEqual(constants["ADDR_BITS"].value, cells.ADDRESS_BITS)
        self.assertEqual(constants["CAP_PAYLOAD_BITS"].value, caps.CAPABILITY_PAYLOAD_BITS)
        self.assertEqual(constants["CAP_TAG_BITS"].value, caps.CAPABILITY_TAG_BITS)
        self.assertEqual(constants["CSR_NUMBER_BITS"].value, csrs.CSR_NUMBER_BITS)

    def test_opcode_constants_cover_mandatory_opcode_forms(self) -> None:
        contract = sv_contract.systemverilog_contract()
        opcode_constants = {constant.name: constant.value for constant in contract.opcode_constants}

        self.assertEqual(len(opcode_constants), len(opcodes.all_opcode_forms()))
        self.assertEqual(opcode_constants["OPC_ADD_24"], opcodes.opcode_form_for("ADD").opcode_id)
        self.assertEqual(opcode_constants["OPC_LD48_24"], opcodes.opcode_form_for("LD48").opcode_id)
        self.assertEqual(opcode_constants["OPC_CLC_24"], opcodes.opcode_form_for("CLC").opcode_id)
        self.assertEqual(opcode_constants["OPC_CSETADDR_48"], opcodes.opcode_form_for("CSETADDR").opcode_id)
        self.assertEqual(opcode_constants["OPC_SYS_12"], opcodes.opcode_form_for("SYS").opcode_id)

    def test_packed_types_name_capability_fault_and_retire_fields(self) -> None:
        structs = {struct.name: struct for struct in sv_contract.systemverilog_contract().structs}

        cap_payload_fields = {field.name for field in structs["cap_payload_t"].fields}
        self.assertEqual(
            cap_payload_fields,
            {"cursor", "bounds_metadata", "permissions", "otype", "flags"},
        )
        cap_fields = {field.name for field in structs["cap_t"].fields}
        self.assertEqual(cap_fields, {"payload", "tag"})

        fault_fields = {field.name for field in structs["fault_packet_t"].fields}
        self.assertGreaterEqual(
            fault_fields,
            {"valid", "cause", "pc_cell", "slot", "tval", "capcause", "fault_cap_idx"},
        )
        retire_fields = {field.name for field in structs["retire_packet_t"].fields}
        self.assertGreaterEqual(
            retire_fields,
            {
                "valid",
                "sequence",
                "pc_cell",
                "slot",
                "instruction_length",
                "decoded",
                "normal_valid",
                "fault",
                "redirect_valid",
                "redirect_target",
                "redirect_slot",
            },
        )

    def test_top_level_interfaces_cover_memory_tag_and_retire_ports(self) -> None:
        interfaces = {
            interface.name: interface
            for interface in sv_contract.systemverilog_contract().interfaces
        }

        self.assertEqual(
            set(interfaces),
            {
                "cpu_v01_imem_if",
                "cpu_v01_dmem_if",
                "cpu_v01_tagmem_if",
                "cpu_v01_retire_if",
            },
        )
        self.assertIn("rsp_cells", {signal.name for signal in interfaces["cpu_v01_imem_if"].signals})
        self.assertIn("req_wdata", {signal.name for signal in interfaces["cpu_v01_dmem_if"].signals})
        self.assertIn("rsp_rtag", {signal.name for signal in interfaces["cpu_v01_tagmem_if"].signals})
        self.assertIn("packet", {signal.name for signal in interfaces["cpu_v01_retire_if"].signals})

    def test_cli_renders_markdown_and_json(self) -> None:
        tool = load_tool_module()
        stream = StringIO()

        with contextlib.redirect_stdout(stream):
            result = tool.main([])

        self.assertEqual(result, 0)
        markdown = stream.getvalue()
        self.assertIn("Package: `cpu_v01_pkg`", markdown)
        self.assertIn("`cpu_v01_tagmem_if`", markdown)

        stream = StringIO()
        with contextlib.redirect_stdout(stream):
            result = tool.main(["--format", "json"])

        self.assertEqual(result, 0)
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed["package_name"], "cpu_v01_pkg")
        self.assertTrue(parsed["interfaces"])

    def test_documentation_artifact_names_command_and_required_surfaces(self) -> None:
        text = (ROOT / "docs" / "implementation" / "systemverilog-interface-spec.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I20-S03", text)
        self.assertIn("python tools\\sv_interface_spec.py", text)
        self.assertIn("`cpu_v01_imem_if`", text)
        self.assertIn("`cpu_v01_dmem_if`", text)
        self.assertIn("`cpu_v01_tagmem_if`", text)
        self.assertIn("`retire_packet_t`", text)


if __name__ == "__main__":
    unittest.main()
