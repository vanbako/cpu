"""I03-S03 conformance tests for first capability derivation operations."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import capabilities as caps
from cpu_v01 import capability_ops, execution, instructions, reset


def bounded_capability(
    base: int = 0x1000,
    top: int = 0x2000,
    cursor: int = 0x1000,
    permissions: int = int(caps.ALL_PERMISSIONS),
    *,
    tag: bool = True,
    otype: int = caps.OTYPE_UNSEALED,
    flags: int = int(caps.CapabilityFlag.G),
) -> caps.Capability:
    payload = caps.CapabilityPayload(
        cursor=cursor,
        bounds_metadata=caps.encode_bounds_metadata(base, top),
        permissions=permissions,
        otype=otype,
        flags=flags,
    )
    return caps.Capability(payload=payload, tag=tag)


def execute_and_commit(core, decoded):
    result = capability_ops.execute_capability(core, decoded)
    if result.is_normal_retire:
        execution.commit_normal_result(core, result)
    return result


class CapabilityDerivationTests(unittest.TestCase):
    def test_bounds_metadata_codec_supports_full_space_and_exact_ranges(self) -> None:
        full = caps.decode_bounds_metadata(caps.BOUNDS_FULL_ADDRESS_SPACE)
        self.assertEqual(full.base, 0)
        self.assertEqual(full.top, 1 << 48)

        metadata = caps.encode_bounds_metadata(0x1000, 0x2000)
        decoded = caps.decode_bounds_metadata(metadata)
        self.assertEqual(decoded.base, 0x1000)
        self.assertEqual(decoded.top, 0x2000)
        self.assertTrue(decoded.contains_cursor(0x1800))
        self.assertFalse(decoded.contains_cursor(0x2000))

        with self.assertRaises(ValueError):
            caps.encode_bounds_metadata(0x1000, 0x1000)

    def test_cmove_copies_payload_and_tag_even_for_invalid_or_sealed_source(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        source = bounded_capability(tag=False, otype=0x22)
        core.write_c(1, source)

        execute_and_commit(core, capability_ops.capability_instruction("CMOVE", (0, 1)))

        self.assertEqual(core.read_c(0), source)

    def test_cgetaddr_writes_cursor_to_integer_without_requiring_tag(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        source = bounded_capability(cursor=0x1800, tag=False, otype=0x33)
        core.write_c(2, source)

        execute_and_commit(core, capability_ops.capability_instruction("CGETADDR", (0, 2)))

        self.assertEqual(core.read_d(0), 0x1800)
        self.assertEqual(core.read_c(2), source)

    def test_csetaddr_changes_only_cursor_when_candidate_is_in_bounds(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        source = bounded_capability(cursor=0x1000)
        core.write_c(1, source)
        core.write_d(0, 0x1800)

        execute_and_commit(core, capability_ops.capability_instruction("CSETADDR", (2, 1, 0)))
        result = core.read_c(2)

        self.assertTrue(result.tag)
        self.assertEqual(result.payload.cursor, 0x1800)
        self.assertEqual(result.payload.bounds_metadata, source.payload.bounds_metadata)
        self.assertEqual(result.payload.permissions, source.payload.permissions)

    def test_csetaddr_faults_out_of_bounds_and_leaves_destination(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        original = bounded_capability(cursor=0x1100)
        core.write_c(0, original)
        core.write_c(1, bounded_capability(cursor=0x1000))
        core.write_d(0, 0x2000)

        result = capability_ops.execute_capability(
            core,
            capability_ops.capability_instruction("CSETADDR", (0, 1, 0)),
        )

        self.assertTrue(result.is_fault)
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.CAPABILITY_BOUNDS_FAULT)
        self.assertEqual(result.fault_packet.capcause, instructions.CapCause.BOUNDS)
        self.assertEqual(result.fault_packet.fault_cap_idx, instructions.FaultCapIndex.C1)
        self.assertEqual(result.fault_packet.tval, 0x2000)
        self.assertEqual(core.read_c(0), original)

    def test_cincaddr_uses_signed_48_bit_offset_and_faults_underflow(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        core.write_c(1, bounded_capability(cursor=0x1800))
        core.write_d(0, (1 << 48) - 0x100)

        execute_and_commit(core, capability_ops.capability_instruction("CINCADDR", (2, 1, 0)))
        self.assertEqual(core.read_c(2).payload.cursor, 0x1700)

        core.write_d(0, (1 << 48) - 0x2000)
        result = capability_ops.execute_capability(
            core,
            capability_ops.capability_instruction("CINCADDR", (2, 1, 0)),
        )
        self.assertTrue(result.is_fault)
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.CAPABILITY_BOUNDS_FAULT)
        self.assertEqual(result.fault_packet.tval, 0)

    def test_csetbounds_narrows_bounds_and_rejects_zero_length(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        source = bounded_capability(base=0x1000, top=0x3000, cursor=0x1800)
        core.write_c(1, source)
        core.write_d(0, 0x800)

        execute_and_commit(core, capability_ops.capability_instruction("CSETBOUNDS", (2, 1, 0)))
        result_bounds = core.read_c(2).payload.bounds
        self.assertEqual(result_bounds.base, 0x1800)
        self.assertEqual(result_bounds.top, 0x2000)
        self.assertEqual(core.read_c(2).payload.cursor, 0x1800)

        core.write_d(0, 0)
        fault = capability_ops.execute_capability(
            core,
            capability_ops.capability_instruction("CSETBOUNDS", (2, 1, 0)),
        )
        self.assertTrue(fault.is_fault)
        self.assertEqual(fault.fault_packet.capcause, instructions.CapCause.BOUNDS)

    def test_candperm_clears_permissions_but_never_adds_them(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        source_permissions = int(caps.CapabilityPermission.LD | caps.CapabilityPermission.LC)
        source = bounded_capability(permissions=source_permissions)
        core.write_c(1, source)
        core.write_d(0, int(caps.CapabilityPermission.LD | caps.CapabilityPermission.ST))

        execute_and_commit(core, capability_ops.capability_instruction("CANDPERM", (2, 1, 0)))

        self.assertEqual(core.read_c(2).payload.permissions, int(caps.CapabilityPermission.LD))

    def test_invalid_or_sealed_derivation_source_faults_before_destination_write(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        original = bounded_capability(cursor=0x1000)
        core.write_c(0, original)
        core.write_c(1, bounded_capability(tag=False))
        core.write_d(0, 0x1100)

        result = capability_ops.execute_capability(
            core,
            capability_ops.capability_instruction("CSETADDR", (0, 1, 0)),
        )
        self.assertTrue(result.is_fault)
        self.assertEqual(result.fault_packet.capcause, instructions.CapCause.TAG)
        self.assertEqual(core.read_c(0), original)

        sealed = bounded_capability(otype=0x22)
        core.write_c(1, sealed)
        result = capability_ops.execute_capability(
            core,
            capability_ops.capability_instruction("CANDPERM", (0, 1, 0)),
        )
        self.assertTrue(result.is_fault)
        self.assertEqual(result.fault_packet.capcause, instructions.CapCause.SEAL_TYPE)
        self.assertEqual(core.read_c(0), original)

    def test_cseal_and_cunseal_require_authority_and_available_object_type(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        source = bounded_capability(cursor=0x1200)
        seal_auth = bounded_capability(
            cursor=0x34,
            permissions=int(caps.CapabilityPermission.SEAL),
        )
        unseal_auth = bounded_capability(
            cursor=0x34,
            permissions=int(caps.CapabilityPermission.UNSEAL),
        )
        core.write_c(1, source)
        core.write_c(2, seal_auth)
        core.write_c(3, unseal_auth)

        execute_and_commit(core, capability_ops.capability_instruction("CSEAL", (4, 1, 2)))
        sealed = core.read_c(4)
        self.assertTrue(sealed.is_sealed)
        self.assertEqual(sealed.payload.otype, 0x34)
        self.assertEqual(sealed.payload.cursor, source.payload.cursor)

        execute_and_commit(core, capability_ops.capability_instruction("CUNSEAL", (5, 4, 3)))
        self.assertTrue(core.read_c(5).is_unsealed)
        self.assertEqual(core.read_c(5).payload.cursor, source.payload.cursor)

        core.write_c(2, bounded_capability(cursor=caps.OTYPE_RETURN, permissions=int(caps.CapabilityPermission.SEAL)))
        fault = capability_ops.execute_capability(
            core,
            capability_ops.capability_instruction("CSEAL", (6, 1, 2)),
        )
        self.assertTrue(fault.is_fault)
        self.assertEqual(fault.fault_packet.capcause, instructions.CapCause.SEAL_TYPE)

    def test_cseal_missing_permission_and_cunseal_mismatch_fault(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        core.write_c(1, bounded_capability())
        core.write_c(2, bounded_capability(cursor=0x44, permissions=0))

        fault = capability_ops.execute_capability(
            core,
            capability_ops.capability_instruction("CSEAL", (3, 1, 2)),
        )
        self.assertTrue(fault.is_fault)
        self.assertEqual(fault.fault_packet.cause, instructions.ExceptionCause.CAPABILITY_PERMISSION_FAULT)
        self.assertEqual(fault.fault_packet.fault_cap_idx, instructions.FaultCapIndex.C2)

        sealed = bounded_capability(otype=0x44)
        auth = bounded_capability(
            cursor=0x45,
            permissions=int(caps.CapabilityPermission.UNSEAL),
        )
        core.write_c(1, sealed)
        core.write_c(2, auth)
        fault = capability_ops.execute_capability(
            core,
            capability_ops.capability_instruction("CUNSEAL", (3, 1, 2)),
        )
        self.assertTrue(fault.is_fault)
        self.assertEqual(fault.fault_packet.capcause, instructions.CapCause.SEAL_TYPE)

    def test_unknown_or_malformed_capability_instruction_reports_illegal_instruction(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)

        result = capability_ops.execute_capability(
            core,
            instructions.DecodedInstruction("NOPE", instructions.InstructionSize.BITS_48),
        )
        self.assertTrue(result.is_fault)
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.ILLEGAL_INSTRUCTION)

        result = capability_ops.execute_capability(
            core,
            capability_ops.capability_instruction("CMOVE", (0,)),
        )
        self.assertTrue(result.is_fault)
        self.assertEqual(result.fault_packet.cause, instructions.ExceptionCause.ILLEGAL_INSTRUCTION)


if __name__ == "__main__":
    unittest.main()
