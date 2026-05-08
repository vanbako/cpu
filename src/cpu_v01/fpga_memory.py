"""FPGA BRAM adapter inventory for CPU v0.1.

Owner stories:
- I23-S03: FPGA ROM, RAM, and tag-memory adapters.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


JsonValue = Any

FPGA_MEMORY_SOURCE_FILES = (
    Path("rtl/cpu_v01_pkg.sv"),
    Path("rtl/cpu_v01_fpga_memories.sv"),
    Path("rtl/cpu_v01_fpga_memory_tb.sv"),
)
FPGA_MEMORY_TOP_SOURCE_FILES = (
    Path("rtl/cpu_v01_pkg.sv"),
    Path("rtl/cpu_v01_core.sv"),
    Path("rtl/cpu_v01_fpga_memories.sv"),
    Path("rtl/cpu_v01_fpga_top.sv"),
    Path("rtl/cpu_v01_fpga_top_tb.sv"),
)
FPGA_MEMORY_DOC = Path("docs/implementation/fpga-memory-adapters.md")


@dataclass(frozen=True)
class FpgaMemoryAdapter:
    module: str
    role: str
    request_ready: str
    response_latency: str
    initialization: str
    tag_policy: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "module": self.module,
            "role": self.role,
            "request_ready": self.request_ready,
            "response_latency": self.response_latency,
            "initialization": self.initialization,
            "tag_policy": self.tag_policy,
        }


def fpga_memory_adapters() -> tuple[FpgaMemoryAdapter, ...]:
    return (
        FpgaMemoryAdapter(
            module="cpu_v01_fpga_imem_rom",
            role="instruction_rom",
            request_ready="ready unless holding an unaccepted instruction response",
            response_latency="one cycle",
            initialization="built-in PAUSE smoke image, optional readmemh INIT_FILE",
            tag_policy="no capability tags",
        ),
        FpgaMemoryAdapter(
            module="cpu_v01_fpga_data_ram",
            role="data_ram",
            request_ready="always ready",
            response_latency="one cycle for reads, no response for writes",
            initialization="zero-filled, optional readmemh INIT_FILE",
            tag_policy="payload cells only",
        ),
        FpgaMemoryAdapter(
            module="cpu_v01_fpga_tag_ram",
            role="tag_ram",
            request_ready="always ready",
            response_latency="one cycle for reads, no response for writes",
            initialization="configuration-cleared tag bits",
            tag_policy="CSC writes preserve req_wtag; integer stores clear with req_wtag=0",
        ),
    )


def fpga_memory_adapters_json(*, indent: int = 2) -> str:
    return json.dumps(
        tuple(adapter.as_dict() for adapter in fpga_memory_adapters()),
        indent=indent,
        sort_keys=True,
    )


def fpga_memory_verilator_command() -> str:
    sources = " ".join(path.as_posix() for path in FPGA_MEMORY_SOURCE_FILES)
    return (
        "verilator --lint-only --timing --top-module "
        f"cpu_v01_fpga_memory_tb {sources}"
    )


def fpga_top_with_memory_verilator_command() -> str:
    sources = " ".join(path.as_posix() for path in FPGA_MEMORY_TOP_SOURCE_FILES)
    return (
        "verilator --lint-only --timing --top-module "
        f"cpu_v01_fpga_top_tb {sources}"
    )


def validate_fpga_memory_adapters(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    issues: list[str] = []

    for path in (*FPGA_MEMORY_SOURCE_FILES, *FPGA_MEMORY_TOP_SOURCE_FILES):
        if not (root / path).exists():
            issues.append(f"missing FPGA memory source {path.as_posix()}")

    memories = _read_if_exists(root / "rtl" / "cpu_v01_fpga_memories.sv")
    memory_tb = _read_if_exists(root / "rtl" / "cpu_v01_fpga_memory_tb.sv")
    top = _read_if_exists(root / "rtl" / "cpu_v01_fpga_top.sv")
    doc = _read_if_exists(root / FPGA_MEMORY_DOC)

    for token in (
        "module cpu_v01_fpga_imem_rom",
        "parameter bit USE_INIT_FILE = 1'b0",
        "parameter string INIT_FILE = \"\"",
        "$readmemh(INIT_FILE, rom_q)",
        "rom_q[i] = 24'h05B05B",
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
        if token not in memories:
            issues.append(f"cpu_v01_fpga_memories.sv missing {token}")

    for token in (
        "module cpu_v01_fpga_memory_tb",
        "FPGA instruction ROM tiny image contents mismatch",
        "FPGA data RAM read/write contents mismatch",
        "FPGA tag RAM did not preserve CSC-style tag write",
        "FPGA tag RAM did not clear tag on integer-store clear write",
        "24'h00CAFE",
        "24'h0BEEF0",
    ):
        if token not in memory_tb:
            issues.append(f"cpu_v01_fpga_memory_tb.sv missing {token}")

    for token in (
        "cpu_v01_fpga_imem_rom",
        "cpu_v01_fpga_data_ram",
        "cpu_v01_fpga_tag_ram",
        ".USE_INIT_FILE(USE_ROM_INIT_FILE)",
        ".USE_INIT_FILE(USE_DATA_INIT_FILE)",
        ".BASE_CELL(DATA_RAM_BASE)",
        ".ENABLE_FETCH(ENABLE_FETCH)",
    ):
        if token not in top:
            issues.append(f"cpu_v01_fpga_top.sv missing {token}")

    try:
        json.dumps(tuple(adapter.as_dict() for adapter in fpga_memory_adapters()), sort_keys=True)
    except TypeError as exc:
        issues.append(f"FPGA memory adapter inventory is not JSON serializable: {exc}")

    for token in (
        "Story: I23-S03",
        "rtl/cpu_v01_fpga_memories.sv",
        "rtl/cpu_v01_fpga_memory_tb.sv",
        "python tools\\fpga_memory_adapters.py --check",
        "cpu_v01_fpga_imem_rom",
        "cpu_v01_fpga_data_ram",
        "cpu_v01_fpga_tag_ram",
        "hex24-cells-v1",
        "readmemh",
        "integer-store clear",
        "I23-S04",
    ):
        if token not in doc:
            issues.append(f"{FPGA_MEMORY_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")
