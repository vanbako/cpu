"""I08-S01 conformance tests for the minimal test-platform profile."""

from __future__ import annotations

from dataclasses import replace
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import capabilities as caps
from cpu_v01 import csrs, mmu, platform, state


class TestPlatformProfileTests(unittest.TestCase):
    def test_profile_self_validation_passes(self) -> None:
        self.assertEqual(platform.validate_profile(), ())

    def test_memory_map_binds_reset_rom_ram_and_devices(self) -> None:
        profile = platform.TEST_PLATFORM_PROFILE
        rom = profile.region_by_name("boot_rom")
        ram = profile.region_by_name("main_ram")
        devices = profile.region_by_name("platform_devices")
        mailbox = profile.region_by_name("secondary_mailbox")

        self.assertEqual(profile.reset_vector, platform.RESET_VECTOR)
        self.assertIs(profile.region_for(profile.reset_vector), rom)
        self.assertEqual(rom.kind, platform.MemoryRegionKind.ROM)
        self.assertTrue(rom.executable)
        self.assertFalse(rom.writable)
        self.assertEqual(rom.memory_type, mmu.MEMORY_TYPE_NORMAL_COHERENT)

        self.assertEqual(ram.kind, platform.MemoryRegionKind.RAM)
        self.assertTrue(ram.readable)
        self.assertTrue(ram.writable)
        self.assertTrue(ram.permissions & caps.CapabilityPermission.LC)
        self.assertTrue(ram.permissions & caps.CapabilityPermission.SC)
        self.assertTrue(ram.permissions & caps.CapabilityPermission.SL)

        self.assertEqual(devices.kind, platform.MemoryRegionKind.DEVICE)
        self.assertEqual(devices.memory_type, mmu.MEMORY_TYPE_DEVICE_ORDERED)
        self.assertEqual(mailbox.kind, platform.MemoryRegionKind.MAILBOX)
        self.assertEqual(mailbox.memory_type, mmu.MEMORY_TYPE_DEVICE_ORDERED)
        self.assertFalse(any(a.overlaps(b) for a in profile.memory_regions for b in profile.memory_regions if a != b))

    def test_cold_reset_installs_bounded_rom_pcc_on_boot_core_only(self) -> None:
        cores = platform.cold_reset_cores()
        profile = platform.TEST_PLATFORM_PROFILE
        rom = profile.reset_rom_region

        self.assertEqual(len(cores), profile.core_count)
        boot = cores[0]
        self.assertEqual(boot.lifecycle, state.CoreLifecycle.RUNNING)
        self.assertEqual(boot.read_csr(csrs.CSR_COREID), 0)
        self.assertEqual(boot.read_csr(csrs.CSR_SR), csrs.SR_RESET_VALUE)
        self.assertEqual(boot.read_csr(csrs.CSR_SATP), 0)
        self.assertEqual(boot.read_csr(csrs.CSR_ASID), 0)
        self.assertEqual(boot.read_csr(csrs.CSR_DEBUGCTL), 0)

        pcc = boot.pcc
        self.assertTrue(pcc.is_valid)
        self.assertEqual(pcc.slot, state.SLOT_0)
        self.assertEqual(pcc.payload.cursor, profile.reset_vector)
        self.assertTrue(pcc.payload.bounds.contains_cursor(profile.reset_vector))
        self.assertEqual(pcc.payload.bounds.base, rom.base)
        self.assertEqual(pcc.payload.bounds.top, rom.end)
        self.assertEqual(pcc.payload.permission_set, caps.CapabilityPermission.EX)
        self.assertTrue(pcc.capability.is_unsealed)
        self.assertTrue(pcc.capability.is_global)

        for core_id, core in enumerate(cores[1:], start=1):
            self.assertEqual(core.lifecycle, profile.secondary_lifecycle)
            self.assertEqual(core.read_csr(csrs.CSR_COREID), core_id)
            self.assertTrue(core.pcc.is_invalid)
            self.assertTrue(all(capability.is_invalid for capability in core.general_capabilities))

    def test_profile_documents_fatal_entry_and_debug_reset_policy(self) -> None:
        profile = platform.TEST_PLATFORM_PROFILE

        self.assertEqual(profile.fatal_entry_policy, platform.FatalEntryPolicy.DEBUG_HALT)
        self.assertEqual(profile.debug_transport, platform.DebugTransportPolicy.SIMULATED_MMIO)
        self.assertFalse(profile.halt_on_reset)
        self.assertEqual(profile.cache_reset_policy, platform.CacheResetPolicy.DISABLED)
        self.assertEqual(profile.ram_reset_policy, platform.RamResetPolicy.UNINITIALIZED)
        self.assertFalse(profile.external_interrupt_pending_on_reset)

    def test_invalid_profiles_report_concrete_issues(self) -> None:
        profile = platform.TEST_PLATFORM_PROFILE
        outside_rom = replace(profile, reset_vector=platform.RAM_BASE)
        bad_core_count = replace(profile, core_count=1)
        halt_on_reset = replace(profile, halt_on_reset=True)

        self.assertIn("reset vector is not in a ROM region", "; ".join(platform.validate_profile(outside_rom)))
        self.assertIn("core_count must be 4", "; ".join(platform.validate_profile(bad_core_count)))
        self.assertIn("must not enter debug halt", "; ".join(platform.validate_profile(halt_on_reset)))


if __name__ == "__main__":
    unittest.main()
