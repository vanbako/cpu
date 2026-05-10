"""FPGA top-level wrapper inventory for CPU v0.1.

Owner stories:
- I23-S02: board-neutral FPGA wrapper.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


JsonValue = Any

FPGA_TOP_SOURCE_FILES = (
    Path("rtl/cpu_v01_pkg.sv"),
    Path("rtl/cpu_v01_core.sv"),
    Path("rtl/cpu_v01_fpga_memories.sv"),
    Path("rtl/cpu_v01_fpga_uart_mmio.sv"),
    Path("rtl/cpu_v01_fpga_timer_mmio.sv"),
    Path("rtl/cpu_v01_fpga_gpio_status.sv"),
    Path("rtl/cpu_v01_fpga_top.sv"),
    Path("rtl/cpu_v01_fpga_top_tb.sv"),
)
FPGA_TOP_DOC = Path("docs/implementation/fpga-top-wrapper.md")


@dataclass(frozen=True)
class FpgaTopPort:
    name: str
    direction: str
    width: str
    group: str
    summary: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "direction": self.direction,
            "width": self.width,
            "group": self.group,
            "summary": self.summary,
        }


def fpga_top_ports() -> tuple[FpgaTopPort, ...]:
    return (
        FpgaTopPort("board_clk_i", "input", "1", "clock_reset", "Board clock input."),
        FpgaTopPort("board_reset_n_i", "input", "1", "clock_reset", "Active-low asynchronous board reset."),
        FpgaTopPort("debug_halt_request_i", "input", "1", "debug", "Optional board or probe halt request."),
        FpgaTopPort("uart_rx_i", "input", "1", "debug", "Firmware UART receive input."),
        FpgaTopPort("loader_req_valid_i", "input", "1", "loader", "Board-safe loader request valid."),
        FpgaTopPort("loader_req_ready_o", "output", "1", "loader", "Board-safe loader request acceptance."),
        FpgaTopPort("loader_req_write_i", "input", "1", "loader", "Board-safe loader write command."),
        FpgaTopPort("loader_req_addr_i", "input", "48", "loader", "Board-safe loader target cell address."),
        FpgaTopPort("loader_req_wdata_i", "input", "24", "loader", "Board-safe loader write data cell."),
        FpgaTopPort("loader_req_tag_i", "input", "1", "loader", "Board-safe loader tag-policy input."),
        FpgaTopPort("loader_uart_tx_i", "input", "1", "loader", "Loader UART transmit output before arbitration."),
        FpgaTopPort("uart_tx_o", "output", "1", "debug", "Shared firmware, debug/status, and loader UART transmit output."),
        FpgaTopPort("loader_status_valid_o", "output", "1", "loader", "Latched board-safe loader status valid."),
        FpgaTopPort("loader_status_code_o", "output", "16", "loader", "Latched board-safe loader status code."),
        FpgaTopPort("pass_led_o", "output", "1", "status", "Reset-idle pass indication until I23-S04 firmware status exists."),
        FpgaTopPort("fail_led_o", "output", "1", "status", "Sticky fault indication."),
        FpgaTopPort("heartbeat_led_o", "output", "1", "status", "Retire-sequence heartbeat projection."),
        FpgaTopPort("status_reset_observed_o", "output", "1", "status", "Core reset observation."),
        FpgaTopPort("status_core_idle_o", "output", "1", "status", "Core idle observation."),
        FpgaTopPort("status_retire_valid_o", "output", "1", "status", "Retire-valid observation."),
        FpgaTopPort("status_fault_valid_o", "output", "1", "status", "Sticky fault-valid observation."),
        FpgaTopPort("status_core_port_activity_o", "output", "1", "status", "Core memory/retire port activity summary."),
        FpgaTopPort("status_fault_code_o", "output", "16", "status", "Sticky fault cause code."),
        FpgaTopPort("status_retire_count_o", "output", "32", "status", "Low retire-sequence bits."),
        FpgaTopPort("debug_pcc_valid_o", "output", "1", "debug", "Reset PCC tag and slot projection."),
        FpgaTopPort("debug_pcc_cursor_low_o", "output", "32", "debug", "Low reset PCC cursor bits."),
        FpgaTopPort("debug_pcc_permissions_o", "output", "8", "debug", "Reset PCC permission bits."),
        FpgaTopPort("debug_sr_low_o", "output", "8", "debug", "Low reset SR bits."),
    )


def fpga_top_verilator_command() -> str:
    sources = " ".join(path.as_posix() for path in FPGA_TOP_SOURCE_FILES)
    return (
        "verilator --binary --timing --top-module "
        f"cpu_v01_fpga_top_tb {sources}"
    )


def fpga_top_ports_json(*, indent: int = 2) -> str:
    return json.dumps(
        tuple(port.as_dict() for port in fpga_top_ports()),
        indent=indent,
        sort_keys=True,
    )


def validate_fpga_top_wrapper(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    issues: list[str] = []

    for path in FPGA_TOP_SOURCE_FILES:
        if not (root / path).exists():
            issues.append(f"missing FPGA top source {path.as_posix()}")

    top = _read_if_exists(root / "rtl" / "cpu_v01_fpga_top.sv")
    tb = _read_if_exists(root / "rtl" / "cpu_v01_fpga_top_tb.sv")
    doc = _read_if_exists(root / FPGA_TOP_DOC)

    for token in (
        "module cpu_v01_fpga_top",
        "board_clk_i",
        "board_reset_n_i",
        "parameter int RESET_SYNC_STAGES = 2",
        "parameter bit ENABLE_FETCH = 1'b1",
        "parameter bit UART_STATUS_ENABLE = 1'b1",
        "parameter int UART_STATUS_BAUD = 115_200",
        "parameter int FIRST_TEST_PASS_RETIRE_COUNT = 8",
        "reset_sync_q",
        "core_rst_n",
        "pass_sticky_q",
        "cpu_v01_core #(",
        ".RESET_VECTOR(RESET_VECTOR)",
        ".ENABLE_FETCH(ENABLE_FETCH)",
        "cpu_v01_fpga_imem_rom",
        "cpu_v01_fpga_data_ram",
        "cpu_v01_fpga_tag_ram",
        ".BASE_CELL(RESET_VECTOR)",
        ".BASE_CELL(DATA_RAM_BASE)",
        ".DEPTH_CELLS(INSTRUCTION_ROM_CELLS)",
        ".DEPTH_CELLS(DATA_RAM_CELLS)",
        "assign timer_interrupt_pending = timer_compare_irq;",
        ".timer_interrupt_pending(timer_interrupt_pending)",
        ".software_interrupt_pending(1'b0)",
        "assign external_interrupt_pending = |(irq_pending_enabled & 16'h000B);",
        ".external_interrupt_pending(external_interrupt_pending)",
        ".external_event_valid(1'b0)",
        ".debug_halt_request(debug_halt_request_i)",
        ".retire_ready(1'b1)",
        "assign pass_led_o = pass_sticky_q && !fault_sticky_q",
        "assign fail_led_o = fault_sticky_q",
        "assign uart_tx_o = uart_mmio_tx & status_uart_tx & loader_uart_tx_i;",
        "cpu_v01_fpga_uart_status_streamer #(",
        ".uart_tx_o(status_uart_tx)",
        "status_core_port_activity_o",
        "debug_pcc_cursor_low_o",
        "debug_sr_low_o",
    ):
        if token not in top:
            issues.append(f"cpu_v01_fpga_top.sv missing {token}")

    for token in (
        "module cpu_v01_fpga_top_tb",
        ".ENABLE_FETCH(1'b0)",
        ".UART_STATUS_BAUD(10)",
        "FPGA top wrapper reset synchronization failed",
        "FPGA top wrapper did not expose reset-idle status",
        "FPGA top wrapper should not pass before firmware retires",
        "FPGA top wrapper should not retire while fetch is disabled",
        "FPGA top wrapper should stay memory idle while fetch is disabled",
        "FPGA top wrapper did not stream a UART status packet",
        "FPGA top wrapper reset debug projection mismatch",
        "debug_pcc_cursor_low_o != 32'h0000_1000",
        "debug_sr_low_o != 8'hC0",
    ):
        if token not in tb:
            issues.append(f"cpu_v01_fpga_top_tb.sv missing {token}")

    groups = {port.group for port in fpga_top_ports()}
    for required in ("clock_reset", "status", "debug", "loader"):
        if required not in groups:
            issues.append(f"FPGA top port projection missing group {required}")

    names = {port.name for port in fpga_top_ports()}
    for required in (
        "board_clk_i",
        "board_reset_n_i",
        "debug_halt_request_i",
        "uart_rx_i",
        "loader_req_valid_i",
        "loader_req_ready_o",
        "loader_req_write_i",
        "loader_req_addr_i",
        "loader_req_wdata_i",
        "loader_req_tag_i",
        "loader_uart_tx_i",
        "uart_tx_o",
        "loader_status_valid_o",
        "loader_status_code_o",
        "pass_led_o",
        "fail_led_o",
        "heartbeat_led_o",
        "status_reset_observed_o",
        "status_core_idle_o",
        "status_retire_valid_o",
        "status_fault_valid_o",
        "status_core_port_activity_o",
        "status_fault_code_o",
        "status_retire_count_o",
        "debug_pcc_valid_o",
        "debug_pcc_cursor_low_o",
        "debug_pcc_permissions_o",
        "debug_sr_low_o",
    ):
        if required not in names:
            issues.append(f"FPGA top port projection missing {required}")

    try:
        json.dumps(tuple(port.as_dict() for port in fpga_top_ports()), sort_keys=True)
    except TypeError as exc:
        issues.append(f"FPGA top port projection is not JSON serializable: {exc}")

    for token in (
        "Story: I23-S02",
        "rtl/cpu_v01_fpga_top.sv",
        "rtl/cpu_v01_fpga_top_tb.sv",
        "python tools\\fpga_top_wrapper.py --check",
        "cpu_v01_fpga_top_tb",
        "cpu_v01_core",
        "board_clk_i",
        "board_reset_n_i",
        "pass_led_o",
        "fail_led_o",
        "uart_rx_i",
        "uart_tx_o",
        "I23-S03",
        "BRAM adapters",
    ):
        if token not in doc:
            issues.append(f"{FPGA_TOP_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")
