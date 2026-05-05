"""I15-S01 property-style tests for capability monotonicity invariants."""

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


DESTINATION = 0
SOURCE = 1
AUTHORITY = 2
VALUE = 0


def capability(
    *,
    base: int = 0x1000,
    top: int = 0x2000,
    cursor: int = 0x1000,
    permissions: int = int(caps.ALL_PERMISSIONS),
    tag: bool = True,
    otype: int = caps.OTYPE_UNSEALED,
    flags: int = int(caps.CapabilityFlag.G),
) -> caps.Capability:
    payload = caps.CapabilityPayload(
        cursor=cursor,
        permissions=permissions,
        otype=otype,
        flags=flags,
    ).with_bounds(base, top)
    return caps.Capability(payload=payload, tag=tag)


def execute_and_commit(core, mnemonic: str, operands: tuple[object, ...]):
    result = capability_ops.execute_capability(
        core,
        capability_ops.capability_instruction(mnemonic, operands),
    )
    if result.is_normal_retire:
        execution.commit_normal_result(core, result)
    return result


def assert_not_wider(
    test: unittest.TestCase,
    derived: caps.Capability,
    parent: caps.Capability,
    *,
    allow_object_type_change: bool = False,
) -> None:
    derived_bounds = derived.payload.bounds
    parent_bounds = parent.payload.bounds

    test.assertTrue(derived.tag <= parent.tag)
    test.assertTrue(parent_bounds.contains_range(derived_bounds.base, derived_bounds.top))
    test.assertEqual(derived.payload.permissions & ~parent.payload.permissions, 0)
    test.assertEqual(derived.payload.flags, parent.payload.flags)
    if not allow_object_type_change:
        test.assertEqual(derived.payload.otype, parent.payload.otype)


class CapabilityMonotonicityPropertyTests(unittest.TestCase):
    def test_cursor_derivation_preserves_authority_within_bounds(self) -> None:
        parents = (
            capability(base=0x1000, top=0x1800, cursor=0x1000),
            capability(base=0x0800, top=0x2000, cursor=0x1000, permissions=0x95),
            capability(base=0x0000, top=0x0400, cursor=0x0200, permissions=0x0F),
        )

        for parent in parents:
            bounds = parent.payload.bounds
            candidates = (
                bounds.base,
                parent.payload.cursor,
                bounds.top - 1,
            )
            for candidate in candidates:
                with self.subTest(parent=parent, candidate=candidate, mnemonic="CSETADDR"):
                    core = reset.cold_reset_core(0, 0x1000)
                    sentinel = capability(cursor=0x1000, permissions=0)
                    core.write_c(DESTINATION, sentinel)
                    core.write_c(SOURCE, parent)
                    core.write_d(VALUE, candidate)

                    result = execute_and_commit(
                        core,
                        "CSETADDR",
                        (DESTINATION, SOURCE, VALUE),
                    )

                    self.assertTrue(result.is_normal_retire)
                    derived = core.read_c(DESTINATION)
                    self.assertEqual(derived.payload.cursor, candidate)
                    assert_not_wider(self, derived, parent)

            offsets = (
                0,
                (bounds.top - 1) - parent.payload.cursor,
                bounds.base - parent.payload.cursor,
            )
            for offset in offsets:
                with self.subTest(parent=parent, offset=offset, mnemonic="CINCADDR"):
                    core = reset.cold_reset_core(0, 0x1000)
                    core.write_c(DESTINATION, capability(cursor=0x1000, permissions=0))
                    core.write_c(SOURCE, parent)
                    core.write_d(VALUE, offset & ((1 << 48) - 1))

                    result = execute_and_commit(
                        core,
                        "CINCADDR",
                        (DESTINATION, SOURCE, VALUE),
                    )

                    self.assertTrue(result.is_normal_retire)
                    derived = core.read_c(DESTINATION)
                    self.assertEqual(derived.payload.cursor, parent.payload.cursor + offset)
                    assert_not_wider(self, derived, parent)

    def test_bounds_derivation_only_narrows_parent_bounds(self) -> None:
        cases = (
            (capability(base=0x1000, top=0x3000, cursor=0x1000), (0x80, 0x400, 0x800)),
            (capability(base=0x1000, top=0x3000, cursor=0x1800), (0x100, 0x400, 0x800)),
            (
                capability(base=0x0000, top=0x1000, cursor=0x0400, permissions=0x33),
                (1, 0x200, 0xC00),
            ),
        )

        for parent, lengths in cases:
            for length in lengths:
                with self.subTest(parent=parent, length=length):
                    core = reset.cold_reset_core(0, 0x1000)
                    core.write_c(DESTINATION, capability(cursor=0x1000, permissions=0))
                    core.write_c(SOURCE, parent)
                    core.write_d(VALUE, length)

                    result = execute_and_commit(
                        core,
                        "CSETBOUNDS",
                        (DESTINATION, SOURCE, VALUE),
                    )

                    self.assertTrue(result.is_normal_retire)
                    derived = core.read_c(DESTINATION)
                    self.assertEqual(derived.payload.cursor, parent.payload.cursor)
                    self.assertEqual(derived.payload.bounds.base, parent.payload.cursor)
                    self.assertEqual(derived.payload.bounds.top, parent.payload.cursor + length)
                    assert_not_wider(self, derived, parent)

    def test_permission_derivation_cannot_set_new_permission_bits(self) -> None:
        permission_sets = (
            int(caps.ALL_PERMISSIONS),
            int(caps.CapabilityPermission.LD | caps.CapabilityPermission.LC),
            int(
                caps.CapabilityPermission.ST
                | caps.CapabilityPermission.SC
                | caps.CapabilityPermission.SL
            ),
            0,
        )
        masks = (0x00, 0x01, 0x55, 0xAA, 0xFF, 0x1FF)

        for permissions in permission_sets:
            parent = capability(permissions=permissions)
            for mask in masks:
                with self.subTest(permissions=permissions, mask=mask):
                    core = reset.cold_reset_core(0, 0x1000)
                    core.write_c(DESTINATION, capability(cursor=0x1000, permissions=0xFF))
                    core.write_c(SOURCE, parent)
                    core.write_d(VALUE, mask)

                    result = execute_and_commit(
                        core,
                        "CANDPERM",
                        (DESTINATION, SOURCE, VALUE),
                    )

                    self.assertTrue(result.is_normal_retire)
                    derived = core.read_c(DESTINATION)
                    self.assertEqual(derived.payload.permissions, permissions & (mask & 0xFF))
                    assert_not_wider(self, derived, parent)

    def test_seal_and_unseal_change_only_authorized_object_type_state(self) -> None:
        sources = (
            capability(cursor=0x1100, permissions=0x37),
            capability(base=0x1000, top=0x1800, cursor=0x1400, permissions=0x80),
        )
        object_types = (0x22, 0x44)

        for source in sources:
            for object_type in object_types:
                with self.subTest(source=source, object_type=object_type):
                    core = reset.cold_reset_core(0, 0x1000)
                    seal_authority = capability(
                        cursor=object_type,
                        permissions=int(caps.CapabilityPermission.SEAL),
                    )
                    unseal_authority = capability(
                        cursor=object_type,
                        permissions=int(caps.CapabilityPermission.UNSEAL),
                    )
                    core.write_c(SOURCE, source)
                    core.write_c(AUTHORITY, seal_authority)

                    seal = execute_and_commit(
                        core,
                        "CSEAL",
                        (DESTINATION, SOURCE, AUTHORITY),
                    )

                    self.assertTrue(seal.is_normal_retire)
                    sealed = core.read_c(DESTINATION)
                    self.assertTrue(sealed.is_sealed)
                    self.assertEqual(sealed.payload.otype, object_type)
                    assert_not_wider(
                        self,
                        sealed,
                        source,
                        allow_object_type_change=True,
                    )

                    core.write_c(SOURCE, sealed)
                    core.write_c(AUTHORITY, unseal_authority)
                    unseal = execute_and_commit(
                        core,
                        "CUNSEAL",
                        (DESTINATION, SOURCE, AUTHORITY),
                    )

                    self.assertTrue(unseal.is_normal_retire)
                    unsealed = core.read_c(DESTINATION)
                    self.assertTrue(unsealed.is_unsealed)
                    self.assertEqual(unsealed.payload.cursor, source.payload.cursor)
                    self.assertEqual(unsealed.payload.bounds, source.payload.bounds)
                    self.assertEqual(unsealed.payload.permissions, source.payload.permissions)
                    assert_not_wider(
                        self,
                        unsealed,
                        sealed,
                        allow_object_type_change=True,
                    )
                    assert_not_wider(self, unsealed, source)

    def test_faulting_derivations_leave_destination_unchanged(self) -> None:
        fault_cases = (
            ("CSETADDR", capability(), 0x2000, instructions.CapCause.BOUNDS),
            (
                "CINCADDR",
                capability(cursor=0x1000),
                (1 << 48) - 1,
                instructions.CapCause.BOUNDS,
            ),
            ("CSETBOUNDS", capability(cursor=0x1800), 0x1000, instructions.CapCause.BOUNDS),
            ("CSETBOUNDS", capability(cursor=0x1000), 1, instructions.CapCause.BOUNDS),
            ("CSETBOUNDS", capability(cursor=0x1000), 0, instructions.CapCause.BOUNDS),
        )
        sentinel = capability(cursor=0x1010, permissions=0x11)

        for mnemonic, source, value, capcause in fault_cases:
            with self.subTest(mnemonic=mnemonic, source=source, value=value):
                core = reset.cold_reset_core(0, 0x1000)
                core.write_c(DESTINATION, sentinel)
                core.write_c(SOURCE, source)
                core.write_d(VALUE, value)

                result = capability_ops.execute_capability(
                    core,
                    capability_ops.capability_instruction(
                        mnemonic,
                        (DESTINATION, SOURCE, VALUE),
                    ),
                )

                self.assertTrue(result.is_fault)
                self.assertEqual(result.fault_packet.capcause, capcause)
                self.assertEqual(core.read_c(DESTINATION), sentinel)

        core = reset.cold_reset_core(0, 0x1000)
        core.write_c(DESTINATION, sentinel)
        core.write_c(SOURCE, capability(otype=0x22))
        core.write_c(
            AUTHORITY,
            capability(cursor=0x44, permissions=int(caps.CapabilityPermission.UNSEAL)),
        )
        mismatch = capability_ops.execute_capability(
            core,
            capability_ops.capability_instruction(
                "CUNSEAL",
                (DESTINATION, SOURCE, AUTHORITY),
            ),
        )
        self.assertTrue(mismatch.is_fault)
        self.assertEqual(mismatch.fault_packet.capcause, instructions.CapCause.SEAL_TYPE)
        self.assertEqual(core.read_c(DESTINATION), sentinel)

    def test_invalid_tags_cannot_synthesize_valid_capabilities(self) -> None:
        invalid_sources = (
            capability(tag=False),
            capability(tag=False, otype=0x22),
        )
        derivation_cases = (
            ("CSETADDR", (DESTINATION, SOURCE, VALUE), 0x1000),
            ("CINCADDR", (DESTINATION, SOURCE, VALUE), 0),
            ("CSETBOUNDS", (DESTINATION, SOURCE, VALUE), 1),
            ("CANDPERM", (DESTINATION, SOURCE, VALUE), 0xFF),
            ("CSEAL", (DESTINATION, SOURCE, AUTHORITY), None),
            ("CUNSEAL", (DESTINATION, SOURCE, AUTHORITY), None),
        )
        sentinel = capability(cursor=0x1000, permissions=0x55)

        for source in invalid_sources:
            for mnemonic, operands, value in derivation_cases:
                with self.subTest(source=source, mnemonic=mnemonic):
                    core = reset.cold_reset_core(0, 0x1000)
                    core.write_c(DESTINATION, sentinel)
                    core.write_c(SOURCE, source)
                    core.write_c(
                        AUTHORITY,
                        capability(
                            cursor=0x22,
                            permissions=int(
                                caps.CapabilityPermission.SEAL
                                | caps.CapabilityPermission.UNSEAL
                            ),
                        ),
                    )
                    if value is not None:
                        core.write_d(VALUE, value)

                    result = capability_ops.execute_capability(
                        core,
                        capability_ops.capability_instruction(mnemonic, operands),
                    )

                    self.assertTrue(result.is_fault)
                    self.assertEqual(result.fault_packet.capcause, instructions.CapCause.TAG)
                    self.assertEqual(core.read_c(DESTINATION), sentinel)

        core = reset.cold_reset_core(0, 0x1000)
        invalid = capability(tag=False, permissions=0xFF)
        core.write_c(SOURCE, invalid)
        execute_and_commit(core, "CMOVE", (DESTINATION, SOURCE))
        self.assertEqual(core.read_c(DESTINATION), invalid)
        self.assertFalse(core.read_c(DESTINATION).tag)


if __name__ == "__main__":
    unittest.main()
