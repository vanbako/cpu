"""I18-S03 conformance tests for the user/kernel syscall demo."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import capabilities as caps
from cpu_v01 import csrs, instructions, state, syscall_demo, user_process, vm
from cpu_v01.cells import BASE_PAGE_CELLS, INTEGER_OBJECT_CELLS


class UserKernelSyscallDemoTests(unittest.TestCase):
    def test_syscall_round_trip_preserves_frame_and_returns_scalar_and_capability(self) -> None:
        fixture = syscall_demo.prepare_syscall_demo_fixture()

        report = syscall_demo.run_syscall_demo(fixture)

        self.assertTrue(report.trap_entry.entered)
        self.assertTrue(report.accepted)
        self.assertEqual(report.status, syscall_demo.SyscallDemoStatus.OK)
        self.assertEqual(report.saved_frame.cause, int(instructions.ExceptionCause.SYSCALL_TRAP))
        self.assertEqual(report.saved_frame.epcc.payload.cursor, user_process.USER_ENTRY_CELL)
        self.assertEqual(report.saved_frame.epcc.slot, state.SLOT_0)
        self.assertTrue(report.saved_frame.sr & (1 << csrs.SR_PRIV_BIT))
        self.assertTrue(report.saved_frame.sr & (1 << csrs.SR_EXL_BIT))
        self.assertEqual(report.return_frame.epcc.payload.cursor, user_process.USER_ENTRY_CELL)
        self.assertEqual(report.return_frame.epcc.slot, state.SLOT_1)
        self.assertEqual(report.service_number, syscall_demo.SYSCALL_DEMO_SERVICE)
        self.assertEqual(
            report.integer_arguments,
            (syscall_demo.SYSCALL_DEMO_ARG0, syscall_demo.SYSCALL_DEMO_ARG1),
        )
        self.assertEqual(report.loaded_user_value, syscall_demo.SYSCALL_DEMO_USER_VALUE)
        expected_sum = (
            syscall_demo.SYSCALL_DEMO_ARG0
            + syscall_demo.SYSCALL_DEMO_ARG1
            + syscall_demo.SYSCALL_DEMO_USER_VALUE
        )
        self.assertEqual(report.return_d0, int(syscall_demo.SyscallDemoStatus.OK))
        self.assertEqual(report.return_d1, expected_sum)
        self.assertTrue(report.return_c0.is_valid)
        self.assertEqual(
            report.return_c0.payload.cursor,
            vm.USER_VM_ADDRESS + INTEGER_OBJECT_CELLS,
        )
        self.assertTrue(report.iret_result.is_normal_retire)
        self.assertTrue(report.final_user_mode)
        self.assertFalse(report.final_sr & (1 << csrs.SR_EXL_BIT))
        self.assertEqual(report.final_pcc.payload.cursor, user_process.USER_ENTRY_CELL)
        self.assertEqual(report.final_pcc.slot, state.SLOT_1)

    def test_bad_service_number_rejects_without_user_pointer_load(self) -> None:
        fixture = syscall_demo.prepare_syscall_demo_fixture(service_number=0xBAD)

        report = syscall_demo.run_syscall_demo(fixture)

        self.assertFalse(report.accepted)
        self.assertEqual(report.status, syscall_demo.SyscallDemoStatus.BAD_SERVICE)
        self.assertIsNone(report.pointer_load)
        self.assertIsNone(report.pointer_fault)
        self.assertIsNone(report.loaded_user_value)
        self.assertEqual(report.return_d0, int(syscall_demo.SyscallDemoStatus.BAD_SERVICE))
        self.assertEqual(report.return_d1, 0xBAD)
        self.assertTrue(report.return_c0.is_invalid)
        self.assertTrue(report.iret_result.is_normal_retire)
        self.assertTrue(report.final_user_mode)

    def test_bad_scalar_argument_rejects_before_user_pointer_load(self) -> None:
        fixture = syscall_demo.prepare_syscall_demo_fixture(
            arg0=syscall_demo.SYSCALL_DEMO_MAX_ARGUMENT + 1,
        )

        report = syscall_demo.run_syscall_demo(fixture)

        self.assertFalse(report.accepted)
        self.assertEqual(report.status, syscall_demo.SyscallDemoStatus.BAD_ARGUMENT)
        self.assertIsNone(report.pointer_load)
        self.assertEqual(report.return_d0, int(syscall_demo.SyscallDemoStatus.BAD_ARGUMENT))
        self.assertEqual(report.return_d1, syscall_demo.SYSCALL_DEMO_MAX_ARGUMENT + 1)
        self.assertTrue(report.return_c0.is_invalid)
        self.assertTrue(report.final_user_mode)

    def test_unmapped_user_pointer_rejects_with_page_fault_detail(self) -> None:
        pointer = vm.virtual_authority(
            vm.USER_VM_PAGE + BASE_PAGE_CELLS + vm.USER_VM_OFFSET,
            permissions=caps.CapabilityPermission.LD,
        )
        fixture = syscall_demo.prepare_syscall_demo_fixture(user_pointer=pointer)

        report = syscall_demo.run_syscall_demo(fixture)

        self.assertFalse(report.accepted)
        self.assertEqual(report.status, syscall_demo.SyscallDemoStatus.BAD_USER_POINTER)
        self.assertIsNotNone(report.pointer_load)
        self.assertIsNotNone(report.pointer_fault)
        assert report.pointer_fault is not None
        self.assertEqual(report.pointer_fault.cause, instructions.ExceptionCause.PAGE_FAULT)
        self.assertEqual(report.pointer_fault.tval, pointer.payload.cursor)
        self.assertEqual(report.return_d0, int(syscall_demo.SyscallDemoStatus.BAD_USER_POINTER))
        self.assertEqual(report.return_d1, int(instructions.ExceptionCause.PAGE_FAULT))
        self.assertTrue(report.return_c0.is_invalid)
        self.assertTrue(report.final_user_mode)

    def test_invalid_capability_argument_rejects_with_tag_fault_detail(self) -> None:
        pointer = vm.virtual_authority(
            vm.USER_VM_ADDRESS,
            permissions=caps.CapabilityPermission.LD,
            tag=False,
        )
        fixture = syscall_demo.prepare_syscall_demo_fixture()
        fixture.core.write_c(0, pointer)

        report = syscall_demo.run_syscall_demo(fixture)

        self.assertFalse(report.accepted)
        self.assertEqual(report.status, syscall_demo.SyscallDemoStatus.BAD_USER_POINTER)
        self.assertIsNotNone(report.pointer_fault)
        assert report.pointer_fault is not None
        self.assertEqual(
            report.pointer_fault.cause,
            instructions.ExceptionCause.CAPABILITY_TAG_FAULT,
        )
        self.assertEqual(report.pointer_fault.capcause, instructions.CapCause.TAG)
        self.assertEqual(report.pointer_fault.fault_cap_idx, instructions.FaultCapIndex.C0)
        self.assertEqual(
            report.return_d0,
            int(syscall_demo.SyscallDemoStatus.BAD_USER_POINTER),
        )
        self.assertEqual(
            report.return_d1,
            int(instructions.ExceptionCause.CAPABILITY_TAG_FAULT),
        )
        self.assertTrue(report.return_c0.is_invalid)
        self.assertTrue(report.final_user_mode)

    def test_documentation_artifact_names_syscall_validation_and_returns(self) -> None:
        text = (ROOT / "docs" / "implementation" / "user-syscall-demo.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Story: I18-S03", text)
        self.assertIn("service numbers", text)
        self.assertIn("capability results", text)
        self.assertIn("bad user pointers", text)


if __name__ == "__main__":
    unittest.main()
