"""I08-S02 conformance tests for secondary-core startup binding."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import capabilities as caps
from cpu_v01 import csrs, platform, startup, state


def capability(
    cursor: int,
    base: int,
    top: int,
    permissions: caps.CapabilityPermission,
    *,
    tag: bool = True,
    global_cap: bool = True,
) -> caps.Capability:
    payload = caps.CapabilityPayload(
        cursor=cursor,
        permissions=permissions,
        flags=caps.CapabilityFlag.G if global_cap else caps.CapabilityFlag.NONE,
    ).with_bounds(base, top)
    return caps.Capability(payload, tag)


def entry_pcc(cursor: int = platform.RAM_BASE) -> state.SlottedCapability:
    cap = capability(
        cursor,
        platform.RAM_BASE,
        platform.RAM_BASE + platform.RAM_CELLS,
        caps.CapabilityPermission.EX,
    )
    return state.SlottedCapability.from_capability(cap, state.SLOT_0)


def stack_cap(cursor: int) -> caps.Capability:
    return capability(
        cursor,
        platform.RAM_BASE,
        platform.RAM_BASE + platform.RAM_CELLS,
        caps.CapabilityPermission.LD
        | caps.CapabilityPermission.ST
        | caps.CapabilityPermission.LC
        | caps.CapabilityPermission.SC
        | caps.CapabilityPermission.SL,
        global_cap=False,
    )


class SecondaryStartupBindingTests(unittest.TestCase):
    def test_valid_mailbox_and_start_signal_transition_target_to_started(self) -> None:
        cores = list(platform.cold_reset_cores())
        controller = startup.SecondaryStartupController()
        arg_cap = capability(
            platform.RAM_BASE + 0x80,
            platform.RAM_BASE,
            platform.RAM_BASE + platform.RAM_CELLS,
            caps.CapabilityPermission.LD,
        )

        mailbox = controller.publish_start(
            1,
            1,
            entry_pcc=entry_pcc(platform.RAM_BASE + 0x40),
            dsc=stack_cap(platform.RAM_BASE + 0x400),
            rsc=stack_cap(platform.RAM_BASE + 0x800),
            tvc=entry_pcc(platform.RAM_BASE + 0x100).without_slot(),
            arg0=0x1234,
            arg_cap0=arg_cap,
        )
        result = controller.send_start_signal(cores, 1)

        self.assertTrue(result.accepted)
        self.assertEqual(result.failure_code, startup.StartupFailureCode.NONE)
        self.assertEqual(mailbox.state, startup.MailboxState.CONSUMED)
        self.assertEqual(controller.consumed_generations[1], 1)

        target = cores[1]
        self.assertEqual(target.lifecycle, state.CoreLifecycle.STARTED)
        self.assertEqual(target.pcc.payload.cursor, platform.RAM_BASE + 0x40)
        self.assertEqual(target.pcc.slot, state.SLOT_0)
        self.assertEqual(target.read_csr(csrs.CSR_SR), csrs.SR_RESET_VALUE)
        self.assertEqual(target.read_csr(csrs.CSR_SATP), 0)
        self.assertEqual(target.read_csr(csrs.CSR_ASID), 0)
        self.assertEqual(target.read_d(0), 0x1234)
        self.assertTrue(target.read_c(0).is_valid)
        self.assertEqual(target.read_c(0), arg_cap)
        self.assertTrue(target.special_capabilities.read("DSC").is_valid)
        self.assertTrue(target.special_capabilities.read("RSC").is_valid)
        self.assertTrue(target.special_capabilities.read("TVC").is_valid)
        self.assertTrue(target.special_capabilities.read("DDC").is_invalid)

    def test_invalid_entry_pcc_fails_without_partial_startup_state(self) -> None:
        cores = list(platform.cold_reset_cores())
        controller = startup.SecondaryStartupController()
        invalid_entry = state.SlottedCapability.from_capability(
            entry_pcc().without_slot().with_tag(False),
            state.SLOT_0,
        )

        controller.publish_start(
            2,
            1,
            entry_pcc=invalid_entry,
            dsc=stack_cap(platform.RAM_BASE + 0x400),
            rsc=stack_cap(platform.RAM_BASE + 0x800),
            arg0=0x55,
        )
        result = controller.send_start_signal(cores, 2)

        self.assertFalse(result.accepted)
        self.assertEqual(result.failure_code, startup.StartupFailureCode.INVALID_PCC)
        self.assertEqual(cores[2].lifecycle, state.CoreLifecycle.START_FAILED)
        self.assertTrue(cores[2].pcc.is_invalid)
        self.assertEqual(cores[2].read_d(0), 0)
        self.assertEqual(controller.mailbox(2).state, startup.MailboxState.FAILED)

    def test_wrong_core_and_stale_generation_fail_startup(self) -> None:
        cores = list(platform.cold_reset_cores())
        controller = startup.SecondaryStartupController()
        wrong_core_mailbox = startup.StartMailbox(
            target_coreid=1,
            generation=1,
            state=startup.MailboxState.READY,
            entry_pcc=entry_pcc(),
            dsc=stack_cap(platform.RAM_BASE + 0x400),
            rsc=stack_cap(platform.RAM_BASE + 0x800),
        )

        controller.publish_mailbox(2, wrong_core_mailbox)
        wrong_core = controller.send_start_signal(cores, 2)
        self.assertEqual(wrong_core.failure_code, startup.StartupFailureCode.WRONG_CORE)
        self.assertEqual(cores[2].lifecycle, state.CoreLifecycle.START_FAILED)

        cores = list(platform.cold_reset_cores())
        controller = startup.SecondaryStartupController(consumed_generations={1: 3, 2: 0, 3: 0})
        controller.publish_start(
            1,
            3,
            entry_pcc=entry_pcc(),
            dsc=stack_cap(platform.RAM_BASE + 0x400),
            rsc=stack_cap(platform.RAM_BASE + 0x800),
        )
        stale = controller.send_start_signal(cores, 1)
        self.assertEqual(stale.failure_code, startup.StartupFailureCode.STALE_GENERATION)
        self.assertEqual(cores[1].lifecycle, state.CoreLifecycle.START_FAILED)

    def test_invalid_stack_or_optional_capability_fails_validation(self) -> None:
        cores = list(platform.cold_reset_cores())
        controller = startup.SecondaryStartupController()
        controller.publish_start(
            1,
            1,
            entry_pcc=entry_pcc(),
            dsc=stack_cap(platform.RAM_BASE + 0x402),
            rsc=stack_cap(platform.RAM_BASE + 0x800),
        )
        bad_stack = controller.send_start_signal(cores, 1)
        self.assertEqual(bad_stack.failure_code, startup.StartupFailureCode.INVALID_STACK)

        cores = list(platform.cold_reset_cores())
        controller = startup.SecondaryStartupController()
        controller.publish_start(
            1,
            1,
            entry_pcc=entry_pcc(),
            dsc=stack_cap(platform.RAM_BASE + 0x400),
            rsc=stack_cap(platform.RAM_BASE + 0x800),
            arg_cap0=capability(
                platform.RAM_BASE + 0x80,
                platform.RAM_BASE,
                platform.RAM_BASE + platform.RAM_CELLS,
                caps.CapabilityPermission.LD,
                tag=False,
            ),
        )
        bad_arg_cap = controller.send_start_signal(cores, 1)
        self.assertEqual(bad_arg_cap.failure_code, startup.StartupFailureCode.INVALID_CAPABILITY)

    def test_not_ready_invalid_target_and_already_started_do_not_replace_state(self) -> None:
        cores = list(platform.cold_reset_cores())
        controller = startup.SecondaryStartupController()

        not_ready = controller.send_start_signal(cores, 3)
        self.assertEqual(not_ready.failure_code, startup.StartupFailureCode.NOT_READY)
        self.assertEqual(cores[3].lifecycle, state.CoreLifecycle.START_FAILED)

        boot_target = controller.send_start_signal(cores, 0)
        self.assertEqual(boot_target.failure_code, startup.StartupFailureCode.INVALID_TARGET)
        self.assertEqual(cores[0].lifecycle, state.CoreLifecycle.RUNNING)

        cores = list(platform.cold_reset_cores())
        controller = startup.SecondaryStartupController()
        controller.publish_start(
            1,
            1,
            entry_pcc=entry_pcc(platform.RAM_BASE + 0x40),
            dsc=stack_cap(platform.RAM_BASE + 0x400),
            rsc=stack_cap(platform.RAM_BASE + 0x800),
        )
        self.assertTrue(controller.send_start_signal(cores, 1).accepted)
        original_cursor = cores[1].pcc.payload.cursor

        controller.publish_start(
            1,
            2,
            entry_pcc=entry_pcc(platform.RAM_BASE + 0x1000),
            dsc=stack_cap(platform.RAM_BASE + 0x400),
            rsc=stack_cap(platform.RAM_BASE + 0x800),
        )
        already = controller.send_start_signal(cores, 1)
        self.assertEqual(already.failure_code, startup.StartupFailureCode.ALREADY_STARTED)
        self.assertEqual(cores[1].lifecycle, state.CoreLifecycle.STARTED)
        self.assertEqual(cores[1].pcc.payload.cursor, original_cursor)

    def test_ready_mailbox_cannot_be_updated_in_place(self) -> None:
        controller = startup.SecondaryStartupController()
        controller.publish_start(
            1,
            1,
            entry_pcc=entry_pcc(),
            dsc=stack_cap(platform.RAM_BASE + 0x400),
            rsc=stack_cap(platform.RAM_BASE + 0x800),
        )
        with self.assertRaises(ValueError):
            controller.publish_start(
                1,
                2,
                entry_pcc=entry_pcc(platform.RAM_BASE + 0x1000),
                dsc=stack_cap(platform.RAM_BASE + 0x400),
                rsc=stack_cap(platform.RAM_BASE + 0x800),
            )


if __name__ == "__main__":
    unittest.main()
