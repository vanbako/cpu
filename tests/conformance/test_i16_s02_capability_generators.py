"""I16-S02 conformance tests for deterministic capability property generators."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import capabilities as caps
from cpu_v01 import capability_ops, execution, invariant_cases, instructions, reset


DESTINATION = 0
SOURCE = 1
AUTHORITY = 2
VALUE = 0
DATA_ADDRESS = 0x1000


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
    child: caps.Capability,
    parent: caps.Capability,
    *,
    allow_object_type_change: bool = False,
) -> None:
    test.assertTrue(child.tag <= parent.tag)
    test.assertTrue(
        parent.payload.bounds.contains_range(
            child.payload.bounds.base,
            child.payload.bounds.top,
        )
    )
    test.assertEqual(child.payload.permissions & ~parent.payload.permissions, 0)
    test.assertEqual(child.payload.flags, parent.payload.flags)
    if not allow_object_type_change:
        test.assertEqual(child.payload.otype, parent.payload.otype)


class CapabilityPropertyGeneratorTests(unittest.TestCase):
    def test_generator_self_validation_passes_and_names_are_stable(self) -> None:
        self.assertEqual(invariant_cases.validate_capability_derivation_cases(), ())
        self.assertEqual(
            tuple(case.name for case in invariant_cases.capability_derivation_cases()),
            (
                "full_permissions_low_cursor",
                "limited_permissions_mid_cursor",
                "local_store_authority",
            ),
        )
        self.assertEqual(
            tuple(case.name for case in invariant_cases.invalid_capability_cases()),
            (
                "invalid_unsealed_payload",
                "invalid_sealed_payload",
                "invalid_local_payload",
            ),
        )

    def test_generated_cursor_and_bounds_samples_stay_inside_parent_authority(self) -> None:
        for case in invariant_cases.capability_derivation_cases():
            parent_bounds = case.parent.payload.bounds
            for candidate in case.candidate_addresses:
                with self.subTest(case=case.name, candidate=candidate):
                    self.assertTrue(parent_bounds.contains_cursor(candidate))
            for offset in case.offsets:
                with self.subTest(case=case.name, offset=offset):
                    self.assertTrue(
                        parent_bounds.contains_cursor(case.parent.payload.cursor + offset)
                    )
            for length in case.bounds_lengths:
                with self.subTest(case=case.name, length=length):
                    child_top = case.parent.payload.cursor + length
                    self.assertTrue(
                        parent_bounds.contains_range(case.parent.payload.cursor, child_top)
                    )
                    caps.encode_bounds_metadata(case.parent.payload.cursor, child_top)

    def test_generated_cases_drive_capability_derivation_without_widening(self) -> None:
        for case in invariant_cases.capability_derivation_cases():
            for candidate in case.candidate_addresses:
                with self.subTest(case=case.name, mnemonic="CSETADDR", candidate=candidate):
                    core = reset.cold_reset_core(0, 0x1000)
                    core.write_c(SOURCE, case.parent)
                    core.write_d(VALUE, candidate)

                    result = execute_and_commit(core, "CSETADDR", (DESTINATION, SOURCE, VALUE))

                    self.assertTrue(result.is_normal_retire)
                    self.assertEqual(core.read_c(DESTINATION).payload.cursor, candidate)
                    assert_not_wider(self, core.read_c(DESTINATION), case.parent)

            for offset in case.offsets:
                with self.subTest(case=case.name, mnemonic="CINCADDR", offset=offset):
                    core = reset.cold_reset_core(0, 0x1000)
                    core.write_c(SOURCE, case.parent)
                    core.write_d(VALUE, invariant_cases.signed_48_cell(offset))

                    result = execute_and_commit(core, "CINCADDR", (DESTINATION, SOURCE, VALUE))

                    self.assertTrue(result.is_normal_retire)
                    self.assertEqual(
                        core.read_c(DESTINATION).payload.cursor,
                        case.parent.payload.cursor + offset,
                    )
                    assert_not_wider(self, core.read_c(DESTINATION), case.parent)

            for length in case.bounds_lengths:
                with self.subTest(case=case.name, mnemonic="CSETBOUNDS", length=length):
                    core = reset.cold_reset_core(0, 0x1000)
                    core.write_c(SOURCE, case.parent)
                    core.write_d(VALUE, length)

                    result = execute_and_commit(core, "CSETBOUNDS", (DESTINATION, SOURCE, VALUE))

                    self.assertTrue(result.is_normal_retire)
                    child = core.read_c(DESTINATION)
                    self.assertEqual(child.payload.bounds.base, case.parent.payload.cursor)
                    self.assertEqual(child.payload.bounds.top, case.parent.payload.cursor + length)
                    assert_not_wider(self, child, case.parent)

            for mask in case.permission_masks:
                with self.subTest(case=case.name, mnemonic="CANDPERM", mask=mask):
                    core = reset.cold_reset_core(0, 0x1000)
                    core.write_c(SOURCE, case.parent)
                    core.write_d(VALUE, mask)

                    result = execute_and_commit(core, "CANDPERM", (DESTINATION, SOURCE, VALUE))

                    self.assertTrue(result.is_normal_retire)
                    child = core.read_c(DESTINATION)
                    self.assertEqual(
                        child.payload.permissions,
                        case.parent.payload.permissions & (mask & 0xFF),
                    )
                    assert_not_wider(self, child, case.parent)

    def test_generated_seal_cases_change_only_authorized_object_type_state(self) -> None:
        for case in invariant_cases.capability_derivation_cases():
            for otype in case.seal_object_types:
                with self.subTest(case=case.name, otype=otype):
                    core = reset.cold_reset_core(0, 0x1000)
                    seal_authority = invariant_cases.capability(
                        otype,
                        base=0,
                        top=0x1000,
                        permissions=int(caps.CapabilityPermission.SEAL),
                    )
                    unseal_authority = invariant_cases.capability(
                        otype,
                        base=0,
                        top=0x1000,
                        permissions=int(caps.CapabilityPermission.UNSEAL),
                    )
                    core.write_c(SOURCE, case.parent)
                    core.write_c(AUTHORITY, seal_authority)

                    seal = execute_and_commit(core, "CSEAL", (DESTINATION, SOURCE, AUTHORITY))

                    self.assertTrue(seal.is_normal_retire)
                    sealed = core.read_c(DESTINATION)
                    self.assertEqual(sealed.payload.otype, otype)
                    assert_not_wider(
                        self,
                        sealed,
                        case.parent,
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
                    assert_not_wider(
                        self,
                        unsealed,
                        sealed,
                        allow_object_type_change=True,
                    )
                    assert_not_wider(self, unsealed, case.parent)

    def test_generated_invalid_sources_cannot_promote_tags(self) -> None:
        for case in invariant_cases.invalid_capability_cases():
            for mnemonic, operands, value in (
                ("CSETADDR", (DESTINATION, SOURCE, VALUE), DATA_ADDRESS),
                ("CINCADDR", (DESTINATION, SOURCE, VALUE), 0),
                ("CSETBOUNDS", (DESTINATION, SOURCE, VALUE), 1),
                ("CANDPERM", (DESTINATION, SOURCE, VALUE), 0xFF),
                ("CSEAL", (DESTINATION, SOURCE, AUTHORITY), None),
                ("CUNSEAL", (DESTINATION, SOURCE, AUTHORITY), None),
            ):
                with self.subTest(case=case.name, mnemonic=mnemonic):
                    core = reset.cold_reset_core(0, 0x1000)
                    sentinel = invariant_cases.capability(
                        DATA_ADDRESS,
                        base=0x1000,
                        top=0x2000,
                    )
                    core.write_c(DESTINATION, sentinel)
                    core.write_c(SOURCE, case.source)
                    core.write_c(
                        AUTHORITY,
                        invariant_cases.capability(
                            0x22,
                            base=0,
                            top=0x1000,
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


if __name__ == "__main__":
    unittest.main()
