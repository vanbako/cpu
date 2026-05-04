"""I02-S05 conformance tests for reset state and CSR/CCSR storage."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import capabilities as caps
from cpu_v01 import csrs, reset, state


def sample_capability(cursor: int = 0x1000, tag: bool = True) -> caps.Capability:
    payload = caps.CapabilityPayload(
        cursor=cursor,
        permissions=caps.CapabilityPermission.LD | caps.CapabilityPermission.EX,
        flags=caps.CapabilityFlag.G,
    )
    return caps.Capability(payload=payload, tag=tag)


class ResetAndCsrStorageTests(unittest.TestCase):
    def test_mandatory_fast_csr_map_matches_e02_s02(self) -> None:
        self.assertEqual(csrs.CSR_BITS, 48)
        self.assertEqual(csrs.CSR_NUMBER_COUNT, 256)
        self.assertEqual(csrs.FAST_CSR_COUNT, 16)
        self.assertEqual(
            csrs.MANDATORY_CSR_NAMES,
            (
                "SR",
                "COREID",
                "CYCLE",
                "INSTRET",
                "TVEC",
                "CAUSE",
                "TVAL",
                "SCRATCH",
                "IENABLE",
                "IPENDING",
                "TIMER",
                "TIMECMP",
                "SATP",
                "ASID",
                "DEBUGCTL",
                "PERFSEL",
            ),
        )
        self.assertEqual(csrs.csr_name(0), "SR")
        self.assertEqual(csrs.csr_name(0x0F), "PERFSEL")
        self.assertEqual(csrs.csr_number("timecmp"), 0x0B)

        with self.assertRaises(KeyError):
            csrs.csr_name(0x10)
        with self.assertRaises(ValueError):
            csrs.csr_name(0x100)

    def test_scalar_csr_reset_values_are_per_core(self) -> None:
        csr_file = csrs.ScalarCsrFile.reset(core_id=2)

        self.assertEqual(csr_file.read(csrs.CSR_SR), csrs.SR_RESET_VALUE)
        self.assertEqual(csr_file.read(csrs.CSR_COREID), 2)
        self.assertEqual(csr_file.read(csrs.CSR_CYCLE), 0)
        self.assertEqual(csr_file.read(csrs.CSR_INSTRET), 0)
        self.assertEqual(csr_file.read(csrs.CSR_TVEC), 0)
        self.assertEqual(csr_file.read(csrs.CSR_CAUSE), 0)
        self.assertEqual(csr_file.read(csrs.CSR_TVAL), 0)
        self.assertEqual(csr_file.read(csrs.CSR_SCRATCH), 0)
        self.assertEqual(csr_file.read(csrs.CSR_IENABLE), 0)
        self.assertEqual(csr_file.read(csrs.CSR_IPENDING), 0)
        self.assertEqual(csr_file.read(csrs.CSR_TIMER), 0)
        self.assertEqual(csr_file.read(csrs.CSR_TIMECMP), csrs.CSR_MASK)
        self.assertEqual(csr_file.read(csrs.CSR_SATP), 0)
        self.assertEqual(csr_file.read(csrs.CSR_ASID), 0)
        self.assertEqual(csr_file.read(csrs.CSR_DEBUGCTL), 0)
        self.assertEqual(csr_file.read(csrs.CSR_PERFSEL), 0)

        csr_file.write_raw(csrs.CSR_SCRATCH, 0x123456789ABC)
        self.assertEqual(csr_file.read_name("SCRATCH"), 0x123456789ABC)
        with self.assertRaises(ValueError):
            csr_file.write_raw(csrs.CSR_SCRATCH, 1 << 48)
        with self.assertRaises(TypeError):
            csr_file.write_raw(csrs.CSR_SCRATCH, True)  # type: ignore[arg-type]

    def test_sr_slot_helpers_mirror_pcc_slot(self) -> None:
        core = state.CoreState(core_id=0)
        cap = sample_capability(cursor=0x2000)

        self.assertEqual(csrs.sr_slot(core.read_csr(csrs.CSR_SR)), state.SLOT_0)
        core.install_pcc(state.SlottedCapability.from_capability(cap, state.SLOT_1))
        self.assertEqual(core.pcc.slot, state.SLOT_1)
        self.assertEqual(csrs.sr_slot(core.read_csr(csrs.CSR_SR)), state.SLOT_1)

        core.write_csr_raw(csrs.CSR_SR, 0)
        self.assertEqual(csrs.sr_slot(core.read_csr(csrs.CSR_SR)), state.SLOT_1)

        core.write_ccsr(state.SPECIAL_NAME_TO_CCSR_INDEX["PCC"], cap)
        self.assertEqual(core.pcc.slot, state.SLOT_0)
        self.assertEqual(csrs.sr_slot(core.read_csr(csrs.CSR_SR)), state.SLOT_0)

    def test_boot_core_cold_reset_installs_rom_pcc_and_invalid_baseline(self) -> None:
        reset_vector = 0x1000
        core = reset.cold_reset_core(0, reset_vector)

        self.assertEqual(core.lifecycle, state.CoreLifecycle.RUNNING)
        self.assertEqual(core.read_csr(csrs.CSR_COREID), 0)
        self.assertEqual(core.read_csr(csrs.CSR_SR), csrs.SR_RESET_VALUE)
        self.assertEqual(core.read_csr(csrs.CSR_SATP), 0)
        self.assertEqual(core.read_csr(csrs.CSR_ASID), 0)
        self.assertTrue(all(value == 0 for value in core.integer_registers))
        self.assertTrue(all(capability.is_invalid for capability in core.general_capabilities))

        pcc = core.pcc
        self.assertTrue(pcc.is_valid)
        self.assertEqual(pcc.slot, state.SLOT_0)
        self.assertEqual(pcc.payload.cursor, reset_vector)
        self.assertTrue(pcc.payload.has_permissions(caps.CapabilityPermission.EX))
        self.assertFalse(pcc.payload.has_permissions(caps.CapabilityPermission.ST))
        self.assertFalse(pcc.payload.has_permissions(caps.CapabilityPermission.SC))
        self.assertFalse(pcc.payload.has_permissions(caps.CapabilityPermission.SEAL))
        self.assertFalse(pcc.payload.has_permissions(caps.CapabilityPermission.UNSEAL))
        self.assertTrue(pcc.capability.is_unsealed)
        self.assertTrue(pcc.capability.is_global)

        for name in ("DSC", "RSC", "DDC", "EPCC", "TVC", "KSC", "KRC"):
            self.assertTrue(core.special_capabilities.read(name).is_invalid)

    def test_cold_reset_cores_assign_lifecycle_and_coreid(self) -> None:
        cores = reset.cold_reset_cores(0x1000, state.CoreLifecycle.WFI_PARKED)

        self.assertEqual(len(cores), 4)
        self.assertEqual(cores[0].lifecycle, state.CoreLifecycle.RUNNING)
        self.assertTrue(cores[0].pcc.is_valid)

        for core_id, core in enumerate(cores[1:], start=1):
            self.assertEqual(core.lifecycle, state.CoreLifecycle.WFI_PARKED)
            self.assertEqual(core.read_csr(csrs.CSR_COREID), core_id)
            self.assertTrue(core.pcc.is_invalid)
            self.assertEqual(core.pcc.slot, state.SLOT_0)

    def test_ccsr_storage_copies_existing_capability_tags_only(self) -> None:
        core = reset.cold_reset_core(0, 0x1000)
        valid_cap = sample_capability(cursor=0x3000, tag=True)
        invalid_cap = sample_capability(cursor=0x4000, tag=False)

        core.write_c(1, valid_cap)
        core.write_ccsr(state.SPECIAL_NAME_TO_CCSR_INDEX["TVC"], core.read_c(1))
        self.assertEqual(core.read_ccsr(state.SPECIAL_NAME_TO_CCSR_INDEX["TVC"]), valid_cap)

        core.write_c(2, invalid_cap)
        core.write_ccsr(state.SPECIAL_NAME_TO_CCSR_INDEX["PCC"], core.read_c(2))
        self.assertEqual(core.read_ccsr(state.SPECIAL_NAME_TO_CCSR_INDEX["PCC"]), invalid_cap)
        self.assertTrue(core.pcc.is_invalid)
        self.assertEqual(core.pcc.slot, state.SLOT_0)

    def test_reset_rejects_invalid_core_ids_and_secondary_lifecycle(self) -> None:
        with self.assertRaises(ValueError):
            reset.cold_reset_core(4, 0x1000)
        with self.assertRaises(ValueError):
            reset.cold_reset_core(1, 0x1000, state.CoreLifecycle.RUNNING)
        with self.assertRaises(ValueError):
            reset.cold_reset_core(0, 1 << 48)


if __name__ == "__main__":
    unittest.main()
