#!/usr/bin/env python3
"""Executable numeric consistency model for the CPU v0.1 specs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Field:
    name: str
    high: int
    low: int

    @property
    def width(self) -> int:
        return self.high - self.low + 1


class Checks:
    def __init__(self) -> None:
        self.total = 0
        self.issues: list[str] = []

    def require(self, condition: bool, name: str, detail: str = "") -> None:
        self.total += 1
        if not condition:
            self.issues.append(f"{name}: {detail}".rstrip(": "))

    def no_duplicate_values(self, name: str, values: dict[str, int]) -> None:
        seen: dict[int, str] = {}
        for item_name, value in values.items():
            if value in seen:
                self.require(False, name, f"{item_name} collides with {seen[value]} at 0x{value:X}")
            else:
                seen[value] = item_name
        self.require(True, name, f"{len(values)} values checked")

    def field_layout(self, name: str, width: int, fields: list[Field], exact: bool = True) -> None:
        used: dict[int, str] = {}
        for field in fields:
            self.require(
                0 <= field.low <= field.high < width,
                f"{name}.{field.name}",
                f"invalid range {field.high}:{field.low} for {width}-bit field",
            )
            for bit in range(field.low, field.high + 1):
                previous = used.get(bit)
                self.require(previous is None, name, f"bit {bit} overlaps {previous} and {field.name}")
                used[bit] = field.name
        if exact:
            missing = [bit for bit in range(width) if bit not in used]
            self.require(not missing, name, f"uncovered bits: {missing}")


def hex48(value: int) -> str:
    digits = f"{value:012X}"
    return "0x" + "_".join(digits[i:i + 4] for i in range(0, 12, 4))


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def main() -> int:
    checks = Checks()

    cell_bits = 24
    cell_bytes = 3
    address_bits = 48
    integer_bits = 48
    integer_cells = 2
    capability_payload_bits = 96
    capability_cells = 4
    fetch_group_bits = 48
    fetch_group_cells = 2
    base_page_bits = 11
    base_page_cells = 1 << base_page_bits
    pte_bits = 48
    pte_cells = 2
    cache_line_cells = 16

    checks.require(cell_bits == cell_bytes * 8, "cell size", "24-bit cell must be 3 bytes for host serialization")
    checks.require(integer_bits == integer_cells * cell_bits, "integer object size", "48-bit integer must occupy 2 cells")
    checks.require(capability_payload_bits == capability_cells * cell_bits, "capability object size", "96-bit capability must occupy 4 cells")
    checks.require(fetch_group_bits == fetch_group_cells * cell_bits, "fetch group size", "48-bit fetch group must occupy 2 cells")
    checks.require(cache_line_cells * cell_bytes == 48, "cache line byte size", "16 cells must equal 48 bytes")
    checks.require(cache_line_cells // capability_cells == 4, "capability slots per cache line", "16-cell line must hold 4 capability slots")
    checks.require(cache_line_cells // integer_cells == 8, "integer slots per cache line", "16-cell line must hold 8 integer slots")
    checks.require(cache_line_cells // fetch_group_cells == 8, "fetch groups per cache line", "16-cell line must hold 8 fetch groups")

    integer_registers = {f"D{i}": i for i in range(16)}
    capability_registers = {f"C{i}": i for i in range(8)}
    checks.no_duplicate_values("integer register numbers", integer_registers)
    checks.no_duplicate_values("general capability register numbers", capability_registers)
    checks.require(len(integer_registers) == 16, "integer register count")
    checks.require(len(capability_registers) == 8, "general capability register count")

    capability_layout = {
        "cursor/address": 48,
        "bounds metadata": 30,
        "permissions": 8,
        "object type": 8,
        "flags": 2,
    }
    checks.require(sum(capability_layout.values()) == capability_payload_bits, "capability payload field sum")
    checks.require(len(["LD", "ST", "EX", "LC", "SC", "SL", "SEAL", "UNSEAL"]) == capability_layout["permissions"], "capability permission count")

    checks.require(base_page_cells == 2048, "base page cell count")
    checks.require(base_page_cells // pte_cells == 1024, "PTEs per page-table page")
    checks.require((base_page_cells // pte_cells).bit_length() - 1 == 10, "PTE index bits")
    checks.require(address_bits - base_page_bits == 37, "VPN bit count")
    checks.require(sum([7, 10, 10, 10]) == 37, "VPN split sum")
    checks.require(37 + base_page_bits == address_bits, "PPN plus page offset width")

    checks.field_layout("SR", 48, [
        Field("Z", 0, 0),
        Field("N", 1, 1),
        Field("C", 2, 2),
        Field("V", 3, 3),
        Field("IE", 4, 4),
        Field("PIE", 5, 5),
        Field("PRIV", 6, 6),
        Field("PPRIV", 7, 7),
        Field("EXL", 8, 8),
        Field("SLOT", 9, 9),
        Field("RES0", 47, 10),
    ])

    checks.field_layout("SATP", 48, [
        Field("MODE", 47, 45),
        Field("ASID", 44, 37),
        Field("ROOT_PPN", 36, 0),
    ])

    satp_modes = {"BARE": 0b000, "RADIX4": 0b001}
    checks.no_duplicate_values("SATP mode values", satp_modes)

    def satp(mode: int, asid: int, root_ppn: int) -> int:
        return (mode << 45) | (asid << 37) | root_ppn

    satp_examples = {
        "Translation off, ASID 0": satp(0, 0, 0),
        "Translation off, ASID 7": satp(0, 7, 0),
        "RADIX4, ASID 0, root PPN 0": satp(1, 0, 0),
        "RADIX4, ASID 1, root PPN 0x12345": satp(1, 1, 0x12345),
        "RADIX4, ASID 255, root PPN all ones": satp(1, 255, (1 << 37) - 1),
    }
    checks.require(satp_examples["Translation off, ASID 7"] == 0x00E000000000, "SATP ASID shift example")
    checks.require(satp_examples["RADIX4, ASID 1, root PPN 0x12345"] == 0x202000012345, "SATP RADIX4 ASID/root example")
    checks.require(satp_examples["RADIX4, ASID 255, root PPN all ones"] == 0x3FFFFFFFFFFF, "SATP max example")

    checks.field_layout("PTE", 48, [
        Field("PPN", 47, 11),
        Field("RES0", 10, 10),
        Field("MT", 9, 8),
        Field("SW", 7, 7),
        Field("A", 6, 6),
        Field("G", 5, 5),
        Field("X", 4, 4),
        Field("W", 3, 3),
        Field("R", 2, 2),
        Field("U", 1, 1),
        Field("V", 0, 0),
    ])

    memory_types = {
        "NORMAL_COHERENT": 0b00,
        "NORMAL_UNCACHEABLE": 0b01,
        "DEVICE_ORDERED": 0b10,
        "RESERVED": 0b11,
    }
    checks.no_duplicate_values("PTE memory types", memory_types)

    ppn = 0x12345
    pte_examples = {
        "Invalid": 0,
        "Non-leaf table pointer": (ppn << 11) | 0x001,
        "Kernel read/write normal coherent leaf, accessed": (ppn << 11) | 0x04D,
        "User read/execute normal coherent leaf, accessed": (ppn << 11) | 0x057,
        "Global kernel execute leaf, accessed": (ppn << 11) | 0x071,
        "Device ordered kernel read/write leaf, accessed": (ppn << 11) | 0x24D,
    }
    checks.require(pte_examples["Non-leaf table pointer"] == 0x0000091A2801, "PTE non-leaf example")
    checks.require(pte_examples["Device ordered kernel read/write leaf, accessed"] == 0x0000091A2A4D, "PTE device leaf example")

    mandatory_csrs = {
        "SR": 0x00,
        "COREID": 0x01,
        "CYCLE": 0x02,
        "INSTRET": 0x03,
        "TVEC": 0x04,
        "CAUSE": 0x05,
        "TVAL": 0x06,
        "SCRATCH": 0x07,
        "IENABLE": 0x08,
        "IPENDING": 0x09,
        "TIMER": 0x0A,
        "TIMECMP": 0x0B,
        "SATP": 0x0C,
        "ASID": 0x0D,
        "DEBUGCTL": 0x0E,
        "PERFSEL": 0x0F,
    }
    checks.no_duplicate_values("mandatory CSR numbers", mandatory_csrs)
    checks.require(sorted(mandatory_csrs.values()) == list(range(16)), "mandatory CSR fast window")

    extended_csrs = {
        **{f"PMC{i}": 0x40 + i for i in range(8)},
        "CACHECTL": 0x48,
        "TLBCTL": 0x49,
        "FAULTCAPIDX": 0x4A,
        "CAPCAUSE": 0x4B,
        "IBP0ADDR": 0x4C,
        "IBP0CTL": 0x4D,
        "IBP1ADDR": 0x4E,
        "IBP1CTL": 0x4F,
        "DWP0ADDR": 0x50,
        "DWP0CTL": 0x51,
        "DWP1ADDR": 0x52,
        "DWP1CTL": 0x53,
    }
    checks.no_duplicate_values("extended CSR assigned numbers", extended_csrs)
    checks.require(all(0x10 <= value <= 0xFF for value in extended_csrs.values()), "extended CSR range")

    ccsr = {
        "PCC": 0,
        "DSC": 1,
        "RSC": 2,
        "DDC": 3,
        "EPCC": 4,
        "TVC": 5,
        "KSC": 6,
        "KRC": 7,
    }
    checks.no_duplicate_values("CCSR indices", ccsr)
    checks.require(sorted(ccsr.values()) == list(range(8)), "implemented CCSR range")

    causes = {
        "NONE": 0x0000,
        "ILLEGAL_INSTRUCTION": 0x0001,
        "BREAKPOINT": 0x0002,
        "PRIVILEGE_FAULT": 0x0003,
        "DIVIDE_BY_ZERO": 0x0004,
        "ALIGN_FAULT": 0x0005,
        "ACCESS_FAULT": 0x0006,
        "PAGE_FAULT": 0x0007,
        "SYSCALL_TRAP": 0x0008,
        "CAPABILITY_TAG_FAULT": 0x0009,
        "CAPABILITY_BOUNDS_FAULT": 0x000A,
        "CAPABILITY_PERMISSION_FAULT": 0x000B,
        "CAPABILITY_SEAL_TYPE_FAULT": 0x000C,
        "CAPABILITY_LOCAL_STORE_FAULT": 0x000D,
        "DEBUG_HALT": 0x000E,
        "RESERVED_CSR_FAULT": 0x0020,
        "ILLEGAL_CSR_READ": 0x0021,
        "ILLEGAL_CSR_WRITE": 0x0022,
        "CSR_PRIVILEGE_FAULT": 0x0023,
        "RESERVED_CCSR_FAULT": 0x0024,
        "ILLEGAL_CCSR_ACCESS": 0x0025,
        "CCSR_PRIVILEGE_FAULT": 0x0026,
        "RETURN_STACK_UNDERFLOW": 0x0030,
        "RETURN_STACK_OVERFLOW": 0x0031,
        "RETURN_STACK_PERMISSION_FAULT": 0x0032,
    }
    checks.no_duplicate_values("exception cause values", causes)
    checks.require(all(0 <= value <= 0x00FF for value in causes.values()), "exception cause assigned range")

    interrupts = {
        "TIMER_INTERRUPT": (0x0001, 0, 1),
        "SOFTWARE_IPI_INTERRUPT": (0x0002, 1, 2),
        "EXTERNAL_INTERRUPT": (0x0003, 2, 3),
    }
    checks.no_duplicate_values("interrupt cause codes", {name: value[0] for name, value in interrupts.items()})
    checks.no_duplicate_values("interrupt pending bits", {name: value[1] for name, value in interrupts.items()})
    checks.no_duplicate_values("interrupt vector indexes", {name: value[2] for name, value in interrupts.items()})
    for name, (code, _bit, _index) in interrupts.items():
        checks.require(((1 << 47) | code) & (1 << 47) != 0, f"{name} interrupt high bit")

    capcause = {
        "NONE": 0x0,
        "TAG": 0x1,
        "BOUNDS": 0x2,
        "PERMISSION": 0x3,
        "SEAL_TYPE": 0x4,
        "LOCAL_STORE": 0x5,
    }
    checks.no_duplicate_values("CAPCAUSE values", capcause)
    checks.require(all(0 <= value <= 0xF for value in capcause.values()), "CAPCAUSE field width")

    faultcapidx = {
        "NONE": 0x00,
        "UNKNOWN": 0x01,
        **{f"C{i}": 0x10 + i for i in range(8)},
        "PCC": 0x20,
        "DDC": 0x21,
        "DSC": 0x22,
        "RSC": 0x23,
        "KSC": 0x24,
        "KRC": 0x25,
        "EPCC": 0x26,
        "TVC": 0x27,
    }
    checks.no_duplicate_values("FAULTCAPIDX values", faultcapidx)
    checks.require(all(0 <= value <= 0xFF for value in faultcapidx.values()), "FAULTCAPIDX field width")

    checks.field_layout("DEBUGCTL final", 48, [
        Field("BRKHALT", 0, 0),
        Field("MONITOR", 1, 1),
        Field("HALTREQ", 2, 2),
        Field("RESUME", 3, 3),
        Field("HALTED", 4, 4),
        Field("STEP", 5, 5),
        Field("RES0", 7, 6),
        Field("DCAUSE", 11, 8),
        Field("RES0", 47, 12),
    ])
    dcause = {
        "NONE": 0x0,
        "EXTERNAL_HALT": 0x1,
        "HALTREQ": 0x2,
        "BRK": 0x3,
        "ENTRY_FAILURE": 0x4,
        "HW_BREAKPOINT": 0x5,
        "WATCHPOINT": 0x6,
        "SINGLE_STEP": 0x7,
    }
    checks.no_duplicate_values("DCAUSE values", dcause)

    checks.field_layout("PERFSEL", 48, [
        Field("IDX", 2, 0),
        Field("RES0", 7, 3),
        Field("EVENT", 15, 8),
        Field("EN", 16, 16),
        Field("CLR", 17, 17),
        Field("CFGW", 18, 18),
        Field("RES0", 47, 19),
    ])
    perf_events = {
        "NONE": 0x00,
        "ICACHE_MISS": 0x01,
        "DCACHE_MISS": 0x02,
        "L2_MISS": 0x03,
        "ITLB_MISS": 0x04,
        "DTLB_MISS": 0x05,
        "BRANCH_MISPREDICT": 0x06,
        "TRAP_TAKEN": 0x07,
        "LLSC_FAILURE": 0x08,
        "CAPABILITY_FAULT": 0x09,
    }
    checks.no_duplicate_values("PERFSEL event selectors", perf_events)
    checks.require(all(0 <= value <= 0xFF for value in perf_events.values()), "PERFSEL event width")

    checks.field_layout("IBPCTL", 48, [
        Field("EN", 0, 0),
        Field("SLOTEN", 1, 1),
        Field("SLOT", 2, 2),
        Field("MATCH_U", 3, 3),
        Field("MATCH_K", 4, 4),
        Field("ASIDEN", 5, 5),
        Field("RES0", 7, 6),
        Field("ASID", 15, 8),
        Field("RES0", 47, 16),
    ])
    checks.field_layout("DWPCTL", 48, [
        Field("EN", 0, 0),
        Field("MATCH_LOAD", 1, 1),
        Field("MATCH_STORE", 2, 2),
        Field("MATCH_ATOMIC", 3, 3),
        Field("MATCH_CAP", 4, 4),
        Field("ASIDEN", 5, 5),
        Field("LEN", 7, 6),
        Field("ASID", 15, 8),
        Field("MATCH_U", 16, 16),
        Field("MATCH_K", 17, 17),
        Field("RES0", 47, 18),
    ])

    e09_s02 = read("spec/E09-S02-satp-layout.md")
    for expected in satp_examples.values():
        checks.require(hex48(expected) in e09_s02, "SATP example text", f"missing {hex48(expected)}")
    checks.require("0x000E_0000_0000" not in e09_s02, "SATP stale ASID example")
    checks.require("0x2002_0001_2345" not in e09_s02, "SATP stale RADIX4 example")

    e09_s05 = read("spec/E09-S05-pte-format.md")
    for expected in pte_examples.values():
        checks.require(hex48(expected) in e09_s05, "PTE example text", f"missing {hex48(expected)}")

    stale_scan_paths = [
        ROOT / "agile-v0.1.md",
        *sorted(path for path in (ROOT / "spec").glob("*.md") if path.name != "E15-S02-numeric-encoding-audit.md"),
        *sorted((ROOT / "spikes").glob("*.md")),
    ]
    all_markdown = "\n".join(path.read_text(encoding="utf-8") for path in stale_scan_paths)
    checks.require("C0-C15" not in all_markdown, "general capability register range text", "C0-C15 should not appear in v0.1")

    print("CPU v0.1 constants model")
    print(f"Checks: {checks.total}")
    print(f"Issues: {len(checks.issues)}")
    for issue in checks.issues:
        print(f"- {issue}")
    print("Derived values:")
    print(f"- Base page cells: {base_page_cells}")
    print(f"- PTEs per page-table page: {base_page_cells // pte_cells}")
    print(f"- VPN split: 7 + 10 + 10 + 10 = {sum([7, 10, 10, 10])}")
    print(f"- Cache line: {cache_line_cells} cells = {cache_line_cells * cell_bytes} bytes")
    print(f"- SATP RADIX4 ASID 1 root 0x12345: {hex48(satp_examples['RADIX4, ASID 1, root PPN 0x12345'])}")

    return 1 if checks.issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
