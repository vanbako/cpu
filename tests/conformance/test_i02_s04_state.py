"""I02-S04 conformance tests for architectural core-state containers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import capabilities as caps
from cpu_v01 import state


def sample_capability(cursor: int = 0x1000, tag: bool = True) -> caps.Capability:
    payload = caps.CapabilityPayload(
        cursor=cursor,
        bounds_metadata=0x1234567,
        permissions=caps.CapabilityPermission.LD | caps.CapabilityPermission.EX,
        otype=caps.OTYPE_UNSEALED,
        flags=caps.CapabilityFlag.G,
    )
    return caps.Capability(payload=payload, tag=tag)


class CoreStateTests(unittest.TestCase):
    def test_register_counts_and_ccsr_map_match_e01(self) -> None:
        self.assertEqual(state.INTEGER_REGISTER_BITS, 48)
        self.assertEqual(state.INTEGER_REGISTER_COUNT, 16)
        self.assertEqual(state.GENERAL_CAPABILITY_REGISTER_COUNT, 8)
        self.assertEqual(
            state.SPECIAL_CAPABILITY_NAMES,
            ("PCC", "DSC", "RSC", "DDC", "EPCC", "TVC", "KSC", "KRC"),
        )
        self.assertEqual(state.CCSR_INDEX_TO_SPECIAL_NAME[0], "PCC")
        self.assertEqual(state.CCSR_INDEX_TO_SPECIAL_NAME[4], "EPCC")
        self.assertEqual(state.CCSR_INDEX_TO_SPECIAL_NAME[7], "KRC")
        self.assertEqual(state.SPECIAL_NAME_TO_CCSR_INDEX["TVC"], 5)

    def test_d0_through_d15_are_writable_48_bit_registers(self) -> None:
        registers = state.IntegerRegisterFile()
        self.assertEqual(len(registers), 16)

        for index in range(16):
            registers.write(index, index + 1)
            self.assertEqual(registers.read(index), index + 1)

        registers.write(0, 0x123456789ABC)
        self.assertEqual(registers.read(0), 0x123456789ABC)

        with self.assertRaises(IndexError):
            registers.read(16)
        with self.assertRaises(ValueError):
            registers.write(1, 1 << 48)
        with self.assertRaises(TypeError):
            registers.write(1, True)

    def test_c0_through_c7_preserve_payload_and_tag(self) -> None:
        registers = state.CapabilityRegisterFile()
        self.assertEqual(len(registers), 8)
        self.assertTrue(all(capability.is_invalid for capability in registers))

        valid_cap = sample_capability(cursor=0x2000, tag=True)
        invalid_cap = sample_capability(cursor=0x3000, tag=False)

        registers.write(0, valid_cap)
        registers.write(7, invalid_cap)

        self.assertEqual(registers.read(0), valid_cap)
        self.assertEqual(registers.read(7), invalid_cap)
        self.assertTrue(registers.read(0).tag)
        self.assertFalse(registers.read(7).tag)

        with self.assertRaises(IndexError):
            registers.read(8)
        with self.assertRaises(TypeError):
            registers.write(1, valid_cap.payload)  # type: ignore[arg-type]

    def test_pcc_and_epcc_carry_hidden_slot_state(self) -> None:
        cap = sample_capability(cursor=0x4000)
        slotted = state.SlottedCapability.from_capability(cap, state.SLOT_1)

        self.assertEqual(slotted.without_slot(), cap)
        self.assertEqual(slotted.payload, cap.payload)
        self.assertEqual(slotted.tag, cap.tag)
        self.assertEqual(slotted.slot, state.SLOT_1)

        with self.assertRaises(ValueError):
            state.SlottedCapability.from_capability(cap, 2)
        with self.assertRaises(TypeError):
            state.SlottedCapability.from_capability(cap, False)  # type: ignore[arg-type]

    def test_special_capability_registers_read_and_write_by_name(self) -> None:
        registers = state.SpecialCapabilityRegisters()
        pcc_cap = sample_capability(cursor=0x5000)
        epcc_cap = sample_capability(cursor=0x6000)
        ddc_cap = sample_capability(cursor=0x7000, tag=False)

        registers.write_slotted(
            "PCC",
            state.SlottedCapability.from_capability(pcc_cap, state.SLOT_1),
        )
        registers.write_slotted(
            "EPCC",
            state.SlottedCapability.from_capability(epcc_cap, state.SLOT_1),
        )
        registers.write("DDC", ddc_cap)

        self.assertEqual(registers.read("PCC"), pcc_cap)
        self.assertEqual(registers.read_slotted("PCC").slot, state.SLOT_1)
        self.assertEqual(registers.read("EPCC"), epcc_cap)
        self.assertEqual(registers.read_slotted("EPCC").slot, state.SLOT_1)
        self.assertEqual(registers.read("DDC"), ddc_cap)

        with self.assertRaises(TypeError):
            registers.read_slotted("DDC")
        with self.assertRaises(KeyError):
            registers.read("NOT_A_REGISTER")

    def test_ccsr_payload_tag_writes_reset_only_pcc_and_epcc_slots(self) -> None:
        registers = state.SpecialCapabilityRegisters()
        pcc_cap = sample_capability(cursor=0x8000)
        epcc_cap = sample_capability(cursor=0x9000)
        ddc_cap = sample_capability(cursor=0xA000)

        registers.write_slotted(
            "PCC",
            state.SlottedCapability.from_capability(pcc_cap, state.SLOT_1),
        )
        registers.write_slotted(
            "EPCC",
            state.SlottedCapability.from_capability(epcc_cap, state.SLOT_1),
        )

        registers.write_ccsr(3, ddc_cap)
        self.assertEqual(registers.read("DDC"), ddc_cap)
        self.assertEqual(registers.read_slotted("PCC").slot, state.SLOT_1)
        self.assertEqual(registers.read_slotted("EPCC").slot, state.SLOT_1)

        new_pcc = sample_capability(cursor=0xB000, tag=False)
        new_epcc = sample_capability(cursor=0xC000, tag=False)
        registers.write_ccsr(0, new_pcc)
        registers.write_ccsr(4, new_epcc)

        self.assertEqual(registers.read_ccsr(0), new_pcc)
        self.assertEqual(registers.read_ccsr(4), new_epcc)
        self.assertEqual(registers.read_slotted("PCC").slot, state.SLOT_0)
        self.assertEqual(registers.read_slotted("EPCC").slot, state.SLOT_0)

        with self.assertRaises(KeyError):
            registers.read_ccsr(8)
        with self.assertRaises(ValueError):
            registers.read_ccsr(256)

    def test_core_state_keeps_per_core_registers_independent(self) -> None:
        core0 = state.CoreState(core_id=0)
        core1 = state.CoreState(core_id=1)
        cap = sample_capability(cursor=0xD000)

        core0.write_d(0, 0x1234)
        core0.write_c(0, cap)
        core0.special_capabilities.write_slotted(
            "PCC",
            state.SlottedCapability.from_capability(cap, state.SLOT_1),
        )

        self.assertEqual(core0.read_d(0), 0x1234)
        self.assertEqual(core0.read_c(0), cap)
        self.assertEqual(core0.pcc.slot, state.SLOT_1)

        self.assertEqual(core1.read_d(0), 0)
        self.assertTrue(core1.read_c(0).is_invalid)
        self.assertTrue(core1.pcc.is_invalid)
        self.assertEqual(core1.pcc.slot, state.SLOT_0)

    def test_core_state_rejects_invalid_core_id(self) -> None:
        with self.assertRaises(ValueError):
            state.CoreState(core_id=-1)
        with self.assertRaises(TypeError):
            state.CoreState(core_id=True)


if __name__ == "__main__":
    unittest.main()
