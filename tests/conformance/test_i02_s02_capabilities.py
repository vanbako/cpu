"""I02-S02 conformance tests for E03 capability data types."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import capabilities as caps


class CapabilityDataTypeTests(unittest.TestCase):
    def test_capability_field_widths_match_e03_s01(self) -> None:
        self.assertEqual(caps.CAPABILITY_PAYLOAD_BITS, 96)
        self.assertEqual(caps.CAPABILITY_CURSOR_BITS, 48)
        self.assertEqual(caps.CAPABILITY_BOUNDS_METADATA_BITS, 30)
        self.assertEqual(caps.CAPABILITY_PERMISSION_BITS, 8)
        self.assertEqual(caps.CAPABILITY_OBJECT_TYPE_BITS, 8)
        self.assertEqual(caps.CAPABILITY_FLAG_BITS, 2)
        self.assertEqual(
            caps.CAPABILITY_CURSOR_BITS
            + caps.CAPABILITY_BOUNDS_METADATA_BITS
            + caps.CAPABILITY_PERMISSION_BITS
            + caps.CAPABILITY_OBJECT_TYPE_BITS
            + caps.CAPABILITY_FLAG_BITS,
            caps.CAPABILITY_PAYLOAD_BITS,
        )

    def test_payload_field_validation_rejects_out_of_range_values(self) -> None:
        payload = caps.CapabilityPayload(
            cursor=(1 << 48) - 1,
            bounds_metadata=(1 << 30) - 1,
            permissions=0xFF,
            otype=0xFF,
            flags=0b11,
        )
        self.assertEqual(payload.cursor, (1 << 48) - 1)

        invalid_cases = [
            {"cursor": 1 << 48},
            {"bounds_metadata": 1 << 30},
            {"permissions": 1 << 8},
            {"otype": 1 << 8},
            {"flags": 1 << 2},
        ]
        for kwargs in invalid_cases:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    payload_kwargs = {"cursor": 0, **kwargs}
                    caps.CapabilityPayload(**payload_kwargs)

        with self.assertRaises(TypeError):
            caps.CapabilityPayload(cursor=True)

    def test_permission_bits_are_named_and_masked(self) -> None:
        self.assertEqual(int(caps.CapabilityPermission.LD), 0x01)
        self.assertEqual(int(caps.CapabilityPermission.ST), 0x02)
        self.assertEqual(int(caps.CapabilityPermission.EX), 0x04)
        self.assertEqual(int(caps.CapabilityPermission.LC), 0x08)
        self.assertEqual(int(caps.CapabilityPermission.SC), 0x10)
        self.assertEqual(int(caps.CapabilityPermission.SL), 0x20)
        self.assertEqual(int(caps.CapabilityPermission.SEAL), 0x40)
        self.assertEqual(int(caps.CapabilityPermission.UNSEAL), 0x80)
        self.assertEqual(int(caps.ALL_PERMISSIONS), 0xFF)
        self.assertEqual(caps.mask_permission_bits(0x1AA), 0xAA)

    def test_permission_sets_are_monotonic_masks(self) -> None:
        payload = caps.CapabilityPayload(
            cursor=0x1000,
            permissions=(
                caps.CapabilityPermission.LD
                | caps.CapabilityPermission.ST
                | caps.CapabilityPermission.LC
                | caps.CapabilityPermission.SC
            ),
        )
        self.assertTrue(
            payload.has_permissions(
                caps.CapabilityPermission.LD | caps.CapabilityPermission.LC
            )
        )
        self.assertFalse(payload.has_permissions(caps.CapabilityPermission.EX))

        reduced = payload.clear_permissions_by_mask(
            caps.CapabilityPermission.LD | caps.CapabilityPermission.LC | 0x100
        )
        self.assertEqual(
            reduced.permission_set,
            caps.CapabilityPermission.LD | caps.CapabilityPermission.LC,
        )

    def test_capability_copy_preserves_payload_and_tag(self) -> None:
        payload = caps.CapabilityPayload(
            cursor=0x1234,
            bounds_metadata=0x1234567,
            permissions=caps.CapabilityPermission.LD | caps.CapabilityPermission.EX,
            otype=caps.OTYPE_ENTRY,
            flags=caps.CapabilityFlag.G,
        )
        valid_cap = caps.Capability.valid(payload)
        self.assertEqual(valid_cap.copy(), valid_cap)
        self.assertTrue(valid_cap.copy().tag)

        invalid_cap = valid_cap.invalidated()
        self.assertEqual(invalid_cap.payload, payload)
        self.assertFalse(invalid_cap.copy().tag)

    def test_invalid_tag_capabilities_still_carry_payload(self) -> None:
        payload = caps.CapabilityPayload(cursor=0x2000, permissions=0xFF)
        invalid_cap = caps.Capability.invalid(payload)
        self.assertTrue(invalid_cap.is_invalid)
        self.assertEqual(invalid_cap.payload.cursor, 0x2000)
        self.assertEqual(invalid_cap.payload.permissions, 0xFF)

    def test_object_type_helpers_model_unsealed_entry_and_return(self) -> None:
        self.assertEqual(caps.OTYPE_UNSEALED, 0x00)
        self.assertEqual(caps.OTYPE_ENTRY, 0xFE)
        self.assertEqual(caps.OTYPE_RETURN, 0xFF)
        self.assertTrue(caps.is_unsealed_otype(0))
        self.assertFalse(caps.is_sealed_otype(0))
        self.assertTrue(caps.is_sealed_otype(1))

        self.assertTrue(caps.is_cseal_available_otype(caps.OTYPE_ENTRY))
        self.assertFalse(caps.is_cseal_available_otype(caps.OTYPE_RETURN))
        self.assertFalse(caps.is_cunseal_available_otype(caps.OTYPE_ENTRY))
        self.assertFalse(caps.is_cunseal_available_otype(caps.OTYPE_RETURN))
        self.assertTrue(caps.is_cunseal_available_otype(0x10))

    def test_global_flag_distinguishes_global_and_local_payloads(self) -> None:
        global_cap = caps.Capability.valid(
            caps.CapabilityPayload(cursor=0x1000, flags=caps.CapabilityFlag.G)
        )
        local_cap = global_cap.as_local()
        self.assertTrue(global_cap.is_global)
        self.assertFalse(global_cap.is_local)
        self.assertFalse(local_cap.is_global)
        self.assertTrue(local_cap.is_local)
        self.assertTrue(local_cap.tag)


if __name__ == "__main__":
    unittest.main()
