#!/usr/bin/env python3
"""Prototype protected return-stack trap and debug interactions.

This is a spike prototype for E14-S05, not a cycle-accurate pipeline model.
It checks the architectural behavior that matters for v0.1:

- `CALL` and `RET` build a return-stack transaction and commit it at retire.
- Trap, interrupt, or debug requests cannot observe a partial `CALL` or `RET`.
- Return-stack overflow and underflow leave architectural state unchanged.
- Debug unwind access happens only at a precise halted boundary.
- Debug peek, drop, and replace operations use whole capability slots.
"""

from __future__ import annotations

from dataclasses import dataclass, field


ENTRY_CELLS = 4
OTYPE_RETURN = 0xFF
FAULTCAPIDX_RSC = "RSC"


class ModelError(ValueError):
    """Raised when the prototype is used with invalid setup."""


class ReturnStackFault(RuntimeError):
    def __init__(self, cause: str, capcause: str, tval: int, faultcapidx: str = FAULTCAPIDX_RSC) -> None:
        super().__init__(cause)
        self.cause = cause
        self.capcause = capcause
        self.tval = tval
        self.faultcapidx = faultcapidx

    def describe(self) -> str:
        return f"{self.cause} CAPCAUSE={self.capcause} TVAL=0x{self.tval:X} FAULTCAPIDX={self.faultcapidx}"


@dataclass(frozen=True)
class ReturnCapability:
    cursor: int
    tag: bool = True
    sealed: bool = True
    otype: int = OTYPE_RETURN
    ex: bool = True
    global_bit: bool = False

    def snapshot(self) -> tuple[int, bool, bool, int, bool, bool]:
        return (self.cursor, self.tag, self.sealed, self.otype, self.ex, self.global_bit)


@dataclass
class Rsc:
    base: int
    top: int
    cursor: int
    tag: bool = True
    sealed: bool = False
    permissions: frozenset[str] = field(
        default_factory=lambda: frozenset({"LD", "ST", "LC", "SC", "SL"})
    )

    def snapshot(self) -> tuple[int, int, int, bool, bool, tuple[str, ...]]:
        return (self.base, self.top, self.cursor, self.tag, self.sealed, tuple(sorted(self.permissions)))


@dataclass(frozen=True)
class Transaction:
    kind: str
    phases: tuple[str, ...]
    slot: int | None = None
    write_cap: ReturnCapability | None = None
    new_cursor: int | None = None
    new_pcc: int | None = None


class ReturnStackModel:
    def __init__(self, base: int = 0x1000, top: int = 0x1020, pcc: int = 0x0100) -> None:
        if base % ENTRY_CELLS or top % ENTRY_CELLS or top - base < ENTRY_CELLS * 2:
            raise ModelError("return-stack bounds must be aligned and include at least one entry plus anchor")
        self.empty_anchor = top - ENTRY_CELLS
        self.rsc = Rsc(base=base, top=top, cursor=self.empty_anchor)
        self.pcc = pcc
        self.debug_halted = False
        self.memory: dict[int, ReturnCapability | None] = {
            slot: None for slot in range(base, top, ENTRY_CELLS)
        }

    def snapshot(self) -> tuple[tuple[int, int, int, bool, bool, tuple[str, ...]], int, bool, tuple[tuple[int, tuple[int, bool, bool, int, bool, bool] | None], ...]]:
        memory_snapshot = tuple(
            (slot, cap.snapshot() if cap is not None else None) for slot, cap in sorted(self.memory.items())
        )
        return (self.rsc.snapshot(), self.pcc, self.debug_halted, memory_snapshot)

    def _slot_in_bounds(self, slot: int) -> bool:
        return slot % ENTRY_CELLS == 0 and self.rsc.base <= slot and slot + ENTRY_CELLS <= self.rsc.top

    def _cursor_in_bounds(self, cursor: int) -> bool:
        return cursor % ENTRY_CELLS == 0 and self.rsc.base <= cursor < self.rsc.top

    def _require_rsc(self, permissions: set[str], tval: int) -> None:
        if not self.rsc.tag:
            raise ReturnStackFault("RETURN_STACK_PERMISSION_FAULT", "TAG", tval)
        if self.rsc.sealed:
            raise ReturnStackFault("RETURN_STACK_PERMISSION_FAULT", "SEAL_TYPE", tval)
        missing = permissions - set(self.rsc.permissions)
        if missing:
            capcause = "LOCAL_STORE" if "SL" in missing else "PERMISSION"
            raise ReturnStackFault("RETURN_STACK_PERMISSION_FAULT", capcause, tval)

    @staticmethod
    def _validate_return_cap(cap: ReturnCapability | None, tval: int, underflow: bool = False) -> ReturnCapability:
        if cap is None or not cap.tag:
            cause = "RETURN_STACK_UNDERFLOW" if underflow else "CAPABILITY_TAG_FAULT"
            raise ReturnStackFault(cause, "TAG", tval)
        if not cap.sealed or cap.otype != OTYPE_RETURN:
            cause = "RETURN_STACK_UNDERFLOW" if underflow else "CAPABILITY_SEAL_TYPE_FAULT"
            raise ReturnStackFault(cause, "SEAL_TYPE", tval)
        if not cap.ex:
            raise ReturnStackFault("CAPABILITY_PERMISSION_FAULT", "PERMISSION", tval)
        if cap.global_bit:
            raise ReturnStackFault("RETURN_STACK_PERMISSION_FAULT", "LOCAL_STORE", tval)
        return cap

    def begin_call(self, call_target: int) -> Transaction:
        target_slot = self.rsc.cursor - ENTRY_CELLS
        self._require_rsc({"ST", "SC", "SL"}, target_slot)
        if not self._slot_in_bounds(target_slot):
            raise ReturnStackFault("RETURN_STACK_OVERFLOW", "BOUNDS", target_slot)
        return_cap = ReturnCapability(cursor=self.pcc + 1)
        return Transaction(
            kind="CALL",
            phases=("derive_return_cap", "check_rsc", "buffer_slot_write", "compute_redirect", "retire"),
            slot=target_slot,
            write_cap=return_cap,
            new_cursor=target_slot,
            new_pcc=call_target,
        )

    def begin_ret(self) -> Transaction:
        target_slot = self.rsc.cursor
        result_cursor = self.rsc.cursor + ENTRY_CELLS
        self._require_rsc({"LD", "LC"}, target_slot)
        if not self._slot_in_bounds(target_slot) or not self._cursor_in_bounds(result_cursor):
            raise ReturnStackFault("RETURN_STACK_UNDERFLOW", "BOUNDS", target_slot)
        return_cap = self._validate_return_cap(
            self.memory.get(target_slot),
            target_slot,
            underflow=target_slot == self.empty_anchor,
        )
        return Transaction(
            kind="RET",
            phases=("read_slot", "validate_return_cap", "compute_cursor", "compute_redirect", "retire"),
            slot=target_slot,
            new_cursor=result_cursor,
            new_pcc=return_cap.cursor,
        )

    def halt_for_debug(self) -> None:
        self.debug_halted = True

    def resume_from_debug(self) -> None:
        self.debug_halted = False

    def _require_debug_boundary(self) -> None:
        if not self.debug_halted:
            raise ReturnStackFault("DEBUG_HALT", "NONE", 0, "NONE")

    def begin_debug_peek(self, depth: int) -> ReturnCapability:
        self._require_debug_boundary()
        if depth < 0:
            raise ModelError("debug peek depth must be nonnegative")
        slot = self.rsc.cursor + (depth * ENTRY_CELLS)
        if slot >= self.empty_anchor or not self._slot_in_bounds(slot):
            raise ReturnStackFault("RETURN_STACK_UNDERFLOW", "BOUNDS", slot)
        return self._validate_return_cap(self.memory.get(slot), slot, underflow=True)

    def begin_debug_drop(self) -> Transaction:
        self._require_debug_boundary()
        slot = self.rsc.cursor
        if slot >= self.empty_anchor or not self._slot_in_bounds(slot):
            raise ReturnStackFault("RETURN_STACK_UNDERFLOW", "BOUNDS", slot)
        self._validate_return_cap(self.memory.get(slot), slot, underflow=True)
        return Transaction(
            kind="DEBUG_DROP",
            phases=("read_slot", "validate_return_cap", "compute_cursor", "retire"),
            slot=slot,
            new_cursor=slot + ENTRY_CELLS,
        )

    def begin_debug_replace(self, depth: int, replacement: ReturnCapability) -> Transaction:
        self._require_debug_boundary()
        if depth < 0:
            raise ModelError("debug replace depth must be nonnegative")
        slot = self.rsc.cursor + (depth * ENTRY_CELLS)
        if slot >= self.empty_anchor or not self._slot_in_bounds(slot):
            raise ReturnStackFault("RETURN_STACK_UNDERFLOW", "BOUNDS", slot)
        self._validate_return_cap(replacement, slot)
        return Transaction(
            kind="DEBUG_REPLACE",
            phases=("validate_replacement", "buffer_slot_write", "retire"),
            slot=slot,
            write_cap=replacement,
        )

    def commit(self, transaction: Transaction) -> None:
        if transaction.write_cap is not None:
            if transaction.slot is None:
                raise ModelError("write transaction requires a slot")
            self.memory[transaction.slot] = transaction.write_cap
        if transaction.new_cursor is not None:
            self.rsc.cursor = transaction.new_cursor
        if transaction.new_pcc is not None:
            self.pcc = transaction.new_pcc


def assert_equal(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def assert_fault(fn: object, cause: str, label: str) -> ReturnStackFault:
    try:
        fn()  # type: ignore[misc]
    except ReturnStackFault as fault:
        assert_equal(fault.cause, cause, label)
        return fault
    raise AssertionError(f"{label}: expected {cause}")


def check_transaction_windows(model: ReturnStackModel, transaction: Transaction, label: str) -> None:
    before = model.snapshot()
    for phase in transaction.phases:
        if phase == "retire":
            break
        assert_equal(model.snapshot(), before, f"{label} phase {phase} remains uncommitted")
    model.commit(transaction)
    if model.snapshot() == before:
        raise AssertionError(f"{label}: retire did not change architectural state")


def run_scenarios() -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []

    model = ReturnStackModel()
    call_txn = model.begin_call(call_target=0x0200)
    check_transaction_windows(model, call_txn, "CALL")
    assert_equal(model.rsc.cursor, model.empty_anchor - ENTRY_CELLS, "CALL cursor update")
    assert_equal(model.memory[model.rsc.cursor] is not None, True, "CALL writes return slot")
    results.append(("CALL trap windows", "no architectural return-stack or PCC update before retire"))

    ret_txn = model.begin_ret()
    check_transaction_windows(model, ret_txn, "RET")
    assert_equal(model.rsc.cursor, model.empty_anchor, "RET cursor update")
    assert_equal(model.pcc, 0x0101, "RET installs return PCC")
    results.append(("RET trap windows", "no architectural pop or PCC update before retire"))

    underflow_model = ReturnStackModel()
    before_underflow = underflow_model.snapshot()
    underflow = assert_fault(underflow_model.begin_ret, "RETURN_STACK_UNDERFLOW", "empty RET")
    assert_equal(underflow_model.snapshot(), before_underflow, "underflow leaves state unchanged")
    results.append(("RET underflow", underflow.describe()))

    overflow_model = ReturnStackModel(base=0x3000, top=0x3008)
    overflow_model.commit(overflow_model.begin_call(call_target=0x0400))
    before_overflow = overflow_model.snapshot()
    overflow = assert_fault(
        lambda: overflow_model.begin_call(call_target=0x0500),
        "RETURN_STACK_OVERFLOW",
        "full CALL",
    )
    assert_equal(overflow_model.snapshot(), before_overflow, "overflow leaves state unchanged")
    results.append(("CALL overflow", overflow.describe()))

    debug_model = ReturnStackModel()
    debug_model.commit(debug_model.begin_call(call_target=0x0200))
    debug_model.commit(debug_model.begin_call(call_target=0x0300))
    debug_model.halt_for_debug()
    before_replace = debug_model.snapshot()
    replacement = ReturnCapability(cursor=0x0BAD)
    replace_txn = debug_model.begin_debug_replace(depth=0, replacement=replacement)
    assert_equal(debug_model.snapshot(), before_replace, "debug replace remains uncommitted before retire")
    debug_model.commit(replace_txn)
    assert_equal(debug_model.begin_debug_peek(depth=0), replacement, "debug peek sees replacement")
    drop_txn = debug_model.begin_debug_drop()
    debug_model.commit(drop_txn)
    next_cap = debug_model.begin_debug_peek(depth=0)
    assert_equal(next_cap.cursor, 0x0101, "debug drop exposes next return frame")
    debug_model.resume_from_debug()
    results.append(("Debug unwind", "halted debug can peek, replace, and drop whole return slots"))

    return results


def main() -> None:
    print("| scenario | result |")
    print("| --- | --- |")
    for scenario, result in run_scenarios():
        print(f"| {scenario} | {result} |")


if __name__ == "__main__":
    main()
