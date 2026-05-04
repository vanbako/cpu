"""RTL handoff checklist derived from the CPU v0.1 semantic model.

Owner stories:
- E13-S01: pipeline stage and trace vocabulary.
- E15-S07: implementation handoff checklist.
- I10-S01: RTL handoff checklist from simulator results.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import opcodes


@dataclass(frozen=True)
class DecoderRow:
    mnemonic: str
    size_bits: int
    opcode_id: int
    fixed_mask: int
    fixed_value: int
    binary_format: str
    privilege: str


@dataclass(frozen=True)
class RtlChecklistItem:
    name: str
    owner: str
    requirement: str


DECODER_TABLE: tuple[DecoderRow, ...] = tuple(
    DecoderRow(
        form.mnemonic,
        form.size.bits,
        form.opcode_id,
        form.fixed_mask,
        form.fixed_value,
        form.binary_format,
        form.privilege.value,
    )
    for form in opcodes.all_opcode_forms()
)

COMMIT_POINT_CHECKLIST: tuple[RtlChecklistItem, ...] = (
    RtlChecklistItem(
        "normal_retire_packet",
        "E07-S03/E13-S01",
        "Commit integer, capability, CSR, CCSR, memory, TLB, reservation, and redirect effects atomically at RT.",
    ),
    RtlChecklistItem(
        "fault_packet_priority",
        "E07-S02/E15-S04",
        "Select exactly one fault/debug/redirect result and suppress all normal effects on fault.",
    ),
    RtlChecklistItem(
        "debug_event_packet",
        "E12-S01/E12-S03",
        "Report debug halt and single-step events precisely without partial architectural effects.",
    ),
    RtlChecklistItem(
        "control_redirect",
        "E04-S04/E06-S03",
        "Install slot-0 redirects for branches/calls and slot-aware `IRET` restores.",
    ),
    RtlChecklistItem(
        "payload_tag_memory_commit",
        "E03-S04/E10-S03",
        "Move capability payload and tag together, and clear overlapped tags with integer stores.",
    ),
    RtlChecklistItem(
        "protected_return_stack_transaction",
        "E05-S04/E06-S04",
        "Commit protected return-stack memory, tag, RSC, and PCC effects as one transaction.",
    ),
    RtlChecklistItem(
        "reservation_update",
        "E08-S01/E08-S02",
        "Install, clear, consume, and conflict-clear LL/SC reservations at architectural boundaries.",
    ),
    RtlChecklistItem(
        "tlb_cache_maintenance",
        "E08-S04/E10-S05",
        "Apply local TLB invalidation and cache-maintenance effects only after privilege and range checks.",
    ),
)

FAULT_PACKET_FIELDS = (
    "cause",
    "faulting_location",
    "tval",
    "capcause",
    "fault_cap_idx",
)

TAG_PATH_CHECKLIST: tuple[RtlChecklistItem, ...] = (
    RtlChecklistItem(
        "register_capability_tags",
        "E03-S01/E04-S05",
        "Carry one tag with every general and special capability register payload.",
    ),
    RtlChecklistItem(
        "memory_capability_tags",
        "E03-S04",
        "Carry one tag per naturally aligned four-cell capability slot.",
    ),
    RtlChecklistItem(
        "capability_load_store_tags",
        "E04-S03",
        "`CLC` and `CSC` transfer payload and tag together.",
    ),
    RtlChecklistItem(
        "ccsr_tag_copy",
        "E02-S05",
        "`CCSRRD` and `CCSRWR` copy payload and tag exactly without synthesizing tags.",
    ),
    RtlChecklistItem(
        "debug_tag_observability",
        "E12-S01",
        "Debug inspection may observe tags but must not create authority from integer payloads.",
    ),
)

CONFORMANCE_HOOKS = (
    "python -m unittest discover -s tests\\conformance -p \"test_*.py\"",
    "python -m unittest discover -s tests\\litmus -p \"test_*.py\"",
    "python tools\\spec_reference_check.py",
    "python tools\\spec_constants_model.py",
)


def decoder_row_for(mnemonic: str) -> tuple[DecoderRow, ...]:
    canonical = opcodes.canonical_mnemonic(mnemonic)
    return tuple(row for row in DECODER_TABLE if row.mnemonic == canonical)


def validate_rtl_handoff() -> tuple[str, ...]:
    issues: list[str] = list(opcodes.validate_opcode_table())
    if len(DECODER_TABLE) != len(opcodes.all_opcode_forms()):
        issues.append("decoder table does not cover every opcode form")
    if not COMMIT_POINT_CHECKLIST:
        issues.append("commit-point checklist is empty")
    if set(FAULT_PACKET_FIELDS) != {
        "cause",
        "faulting_location",
        "tval",
        "capcause",
        "fault_cap_idx",
    }:
        issues.append("fault-packet interface fields are incomplete")
    tag_names = {item.name for item in TAG_PATH_CHECKLIST}
    for required in ("register_capability_tags", "memory_capability_tags", "capability_load_store_tags"):
        if required not in tag_names:
            issues.append(f"missing RTL tag-path item {required}")
    if not any("tests\\conformance" in hook for hook in CONFORMANCE_HOOKS):
        issues.append("missing conformance-suite hook")
    if not any("tests\\litmus" in hook for hook in CONFORMANCE_HOOKS):
        issues.append("missing litmus-suite hook")
    return tuple(issues)
