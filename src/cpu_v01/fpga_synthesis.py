"""FPGA synthesis, implementation, and timing gate for CPU v0.1.

Owner stories:
- I23-S05: first-test synthesis, implementation, and timing gate.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fpga_first_test, fpga_smoke


JsonValue = Any

FPGA_SYNTHESIS_STORY = "I23-S05"
FPGA_SYNTHESIS_DOC = Path("docs/implementation/fpga-synthesis-gate.md")
FPGA_SYNTHESIS_TOOL = "python tools\\fpga_synthesis_gate.py --check"
FPGA_SYNTHESIS_BUILD_ROOT = Path("build/fpga/tang_mega_138k/first_test")
FPGA_SYNTHESIS_CONSTRAINT_FILE = Path("constraints/tang_mega_138k_first_test.cst")
FPGA_SYNTHESIS_TIMING_FILE = Path("constraints/tang_mega_138k_first_test.sdc")
FPGA_SYNTHESIS_TOP_MODULE = fpga_first_test.FPGA_TOP_MODULE
FPGA_SYNTHESIS_DEVICE = fpga_first_test.TARGET_FPGA_DEVICE
FPGA_SYNTHESIS_IDE_PACKAGE = fpga_first_test.TARGET_IDE_PACKAGE
FPGA_SYNTHESIS_BOARD = fpga_first_test.TARGET_BOARD_NAME
FPGA_SYNTHESIS_TARGET_CLOCK_HZ = 25_000_000

FPGA_SYNTHESIS_SOURCE_FILES = (
    Path("rtl/cpu_v01_pkg.sv"),
    Path("rtl/cpu_v01_core.sv"),
    Path("rtl/cpu_v01_fpga_memories.sv"),
    Path("rtl/cpu_v01_fpga_top.sv"),
)


@dataclass(frozen=True)
class FpgaToolRequirement:
    name: str
    executable: str
    role: str
    required: bool
    note: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "executable": self.executable,
            "role": self.role,
            "required": self.required,
            "note": self.note,
        }


@dataclass(frozen=True)
class FpgaConstraintRequirement:
    logical_signal: str
    constraint_kind: str
    source: str
    fail_if_missing: bool
    note: str

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "logical_signal": self.logical_signal,
            "constraint_kind": self.constraint_kind,
            "source": self.source,
            "fail_if_missing": self.fail_if_missing,
            "note": self.note,
        }


@dataclass(frozen=True)
class FpgaGateStep:
    name: str
    command: str
    purpose: str
    pass_criteria: str
    failure_conditions: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "command": self.command,
            "purpose": self.purpose,
            "pass_criteria": self.pass_criteria,
            "failure_conditions": list(self.failure_conditions),
        }


@dataclass(frozen=True)
class FpgaReportRequirement:
    path: str
    producer_step: str
    must_contain: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "path": self.path,
            "producer_step": self.producer_step,
            "must_contain": list(self.must_contain),
        }


@dataclass(frozen=True)
class FpgaSynthesisGate:
    story: str
    board: str
    device: str
    ide_package: str
    top_module: str
    target_clock_hz: int
    build_root: Path
    source_files: tuple[Path, ...]
    constraint_file: Path
    timing_file: Path
    tool_requirements: tuple[FpgaToolRequirement, ...]
    constraint_requirements: tuple[FpgaConstraintRequirement, ...]
    steps: tuple[FpgaGateStep, ...]
    reports: tuple[FpgaReportRequirement, ...]
    blockers: tuple[str, ...]

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "story": self.story,
            "board": self.board,
            "device": self.device,
            "ide_package": self.ide_package,
            "top_module": self.top_module,
            "target_clock_hz": self.target_clock_hz,
            "build_root": self.build_root.as_posix(),
            "source_files": [path.as_posix() for path in self.source_files],
            "constraint_file": self.constraint_file.as_posix(),
            "timing_file": self.timing_file.as_posix(),
            "tool_requirements": [tool.as_dict() for tool in self.tool_requirements],
            "constraint_requirements": [
                constraint.as_dict() for constraint in self.constraint_requirements
            ],
            "steps": [step.as_dict() for step in self.steps],
            "reports": [report.as_dict() for report in self.reports],
            "blockers": list(self.blockers),
        }


def fpga_synthesis_gate() -> FpgaSynthesisGate:
    return FpgaSynthesisGate(
        story=FPGA_SYNTHESIS_STORY,
        board=FPGA_SYNTHESIS_BOARD,
        device=FPGA_SYNTHESIS_DEVICE,
        ide_package=FPGA_SYNTHESIS_IDE_PACKAGE,
        top_module=FPGA_SYNTHESIS_TOP_MODULE,
        target_clock_hz=FPGA_SYNTHESIS_TARGET_CLOCK_HZ,
        build_root=FPGA_SYNTHESIS_BUILD_ROOT,
        source_files=FPGA_SYNTHESIS_SOURCE_FILES,
        constraint_file=FPGA_SYNTHESIS_CONSTRAINT_FILE,
        timing_file=FPGA_SYNTHESIS_TIMING_FILE,
        tool_requirements=(
            FpgaToolRequirement(
                name="Verilator",
                executable="verilator",
                role="pre-synthesis RTL lint/elaboration for the first-test wrapper",
                required=True,
                note="Already used for the I23-S04 smoke testbench.",
            ),
            FpgaToolRequirement(
                name="Gowin EDA command shell",
                executable="gw_sh",
                role="synthesis, place and route, bitstream generation, and reports",
                required=True,
                note="Use a Tang Mega 138K capable Gowin EDA release.",
            ),
            FpgaToolRequirement(
                name="Gowin Programmer",
                executable="programmer_cli_or_gui",
                role="volatile SRAM programming or external flash programming",
                required=True,
                note="Sipeed recommends the standalone 1.9.12 SP1 Programmer for flash.",
            ),
            FpgaToolRequirement(
                name="openFPGALoader",
                executable="openFPGALoader",
                role="optional board programming path using the tangmega138k board flag",
                required=False,
                note="Use only after the physical device/package has been confirmed.",
            ),
        ),
        constraint_requirements=(
            FpgaConstraintRequirement(
                logical_signal="board_clk_i",
                constraint_kind="pin plus 40 ns clock period",
                source="Sipeed All PIN Constraints plus verified board oscillator",
                fail_if_missing=True,
                note="No synth/timing gate may pass with an unconstrained clock.",
            ),
            FpgaConstraintRequirement(
                logical_signal="board_reset_n_i",
                constraint_kind="pin, IO standard, and reset synchronizer treatment",
                source="Sipeed All PIN Constraints plus reset circuit check",
                fail_if_missing=True,
                note="The async input must be constrained and released through the wrapper synchronizer.",
            ),
            FpgaConstraintRequirement(
                logical_signal="pass_led_o",
                constraint_kind="PMOD LED pin, IO standard, and polarity",
                source="Sipeed PMOD LED x8 connector constraints",
                fail_if_missing=True,
                note="The first board smoke needs a visible pass indication.",
            ),
            FpgaConstraintRequirement(
                logical_signal="fail_led_o",
                constraint_kind="PMOD LED pin, IO standard, and polarity",
                source="Sipeed PMOD LED x8 connector constraints",
                fail_if_missing=True,
                note="The first board smoke needs a visible fail indication.",
            ),
            FpgaConstraintRequirement(
                logical_signal="heartbeat_led_o",
                constraint_kind="PMOD LED pin, IO standard, and polarity",
                source="Sipeed PMOD LED x8 connector constraints",
                fail_if_missing=True,
                note="Heartbeat distinguishes reset/clock failure from firmware failure.",
            ),
            FpgaConstraintRequirement(
                logical_signal="status_fault_code_o/status_retire_count_o",
                constraint_kind="optional GAO/UART/ILA probe plan",
                source="Gowin GAO or board UART probe mapping",
                fail_if_missing=False,
                note="Optional probes improve triage but are not required for the first LED pass/fail smoke.",
            ),
        ),
        steps=(
            FpgaGateStep(
                name="rtl_preflight",
                command=fpga_smoke.fpga_smoke_verilator_command(),
                purpose="Elaborate the first-test RTL before handing it to Gowin.",
                pass_criteria="Verilator exits 0 for cpu_v01_fpga_first_test_tb.",
                failure_conditions=(
                    "missing_cpu_v01_core_or_memory_black_box",
                    "first_test_rtl_does_not_elaborate",
                ),
            ),
            FpgaGateStep(
                name="gate_profile_check",
                command=FPGA_SYNTHESIS_TOOL,
                purpose="Validate the synthesis gate profile, sources, docs, and required constraints.",
                pass_criteria="The checker reports zero profile issues.",
                failure_conditions=(
                    "missing_source_file",
                    "missing_documentation",
                    "missing_constraint_requirement",
                ),
            ),
            FpgaGateStep(
                name="emit_gowin_tcl",
                command="python tools\\fpga_synthesis_gate.py --gowin-tcl",
                purpose="Emit the Gowin Tcl batch template for the verified board overlay.",
                pass_criteria="The template names every RTL source, the constraint file, and run all.",
                failure_conditions=(
                    "wrong_top_module",
                    "wrong_device_or_package",
                    "missing_constraint_file_reference",
                ),
            ),
            FpgaGateStep(
                name="gowin_synth_place_route",
                command="gw_sh build/fpga/tang_mega_138k/first_test/run_gowin.tcl",
                purpose="Run Gowin synthesis, place and route, and bitstream generation.",
                pass_criteria="Gowin completes run all and emits timing/utilization/ports reports.",
                failure_conditions=(
                    "unconstrained_clock_or_reset",
                    "negative_timing_slack_at_first_test_clock",
                    "missing_pass_fail_observation_pin",
                    "memory_or_core_black_box",
                ),
            ),
            FpgaGateStep(
                name="report_audit",
                command="python tools\\fpga_synthesis_gate.py --check-reports build\\fpga\\tang_mega_138k\\first_test",
                purpose="Audit generated reports for timing, utilization, ports, and bitstream outputs.",
                pass_criteria="Reports contain timing, utilization, port assignment, and bitstream evidence.",
                failure_conditions=(
                    "missing_timing_report",
                    "missing_utilization_report",
                    "missing_ports_report",
                    "missing_bitstream",
                ),
            ),
        ),
        reports=(
            FpgaReportRequirement(
                path="build/fpga/tang_mega_138k/first_test/impl/gwsynthesis/*.rpt",
                producer_step="gowin_synth_place_route",
                must_contain=("cpu_v01_fpga_top", "cpu_v01_core"),
            ),
            FpgaReportRequirement(
                path="build/fpga/tang_mega_138k/first_test/impl/pnr/*timing*.rpt",
                producer_step="gowin_synth_place_route",
                must_contain=("Slack", "board_clk_i"),
            ),
            FpgaReportRequirement(
                path="build/fpga/tang_mega_138k/first_test/impl/pnr/*ports*.rpt",
                producer_step="gowin_synth_place_route",
                must_contain=("pass_led_o", "fail_led_o", "heartbeat_led_o"),
            ),
            FpgaReportRequirement(
                path="build/fpga/tang_mega_138k/first_test/impl/pnr/*.fs",
                producer_step="gowin_synth_place_route",
                must_contain=(),
            ),
        ),
        blockers=(
            "confirm whether the physical board is the PG484 non-Pro SOM or the FPG676 Pro-style SOM",
            "extract board_clk_i, board_reset_n_i, pass_led_o, fail_led_o, and heartbeat_led_o pins from Sipeed constraints",
            "verify LED polarity and 3.3 V IO standard before programming",
        ),
    )


def fpga_synthesis_gate_json(*, indent: int = 2) -> str:
    return json.dumps(fpga_synthesis_gate().as_dict(), indent=indent, sort_keys=True)


def fpga_synthesis_command_plan(gate: FpgaSynthesisGate | None = None) -> tuple[str, ...]:
    if gate is None:
        gate = fpga_synthesis_gate()
    return tuple(step.command for step in gate.steps)


def gowin_tcl_script(gate: FpgaSynthesisGate | None = None) -> str:
    if gate is None:
        gate = fpga_synthesis_gate()
    lines = [
        "# CPU v0.1 I23-S05 Gowin first-test batch template.",
        "# Verify Tang Mega 138K device/package and replace <verified_B_or_C> before running.",
        f"set_device -device_version <verified_B_or_C> {gate.device}",
        f"set_option -top_module {gate.top_module}",
    ]
    lines.extend(f"add_file -type sv {path.as_posix()}" for path in gate.source_files)
    lines.append(f"add_file -type cst {gate.constraint_file.as_posix()}")
    lines.append(f"add_file -type sdc {gate.timing_file.as_posix()}")
    lines.append("run all")
    lines.append("run close")
    lines.append("")
    return "\n".join(lines)


def render_fpga_synthesis_gate(gate: FpgaSynthesisGate | None = None) -> str:
    if gate is None:
        gate = fpga_synthesis_gate()
    lines = [
        "# FPGA Synthesis Gate",
        "",
        f"Story: {gate.story}",
        "",
        f"Board: `{gate.board}`",
        f"Device: `{gate.device}`",
        f"IDE package: `{gate.ide_package}`",
        f"Top module: `{gate.top_module}`",
        f"Target clock: {gate.target_clock_hz} Hz",
        f"Build root: `{gate.build_root.as_posix()}`",
        "",
        "## Source Files",
        "",
    ]
    lines.extend(f"- `{path.as_posix()}`" for path in gate.source_files)
    lines.extend(
        [
            "",
            "## Tool Requirements",
            "",
            "| Tool | Executable | Required | Role | Note |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for tool in gate.tool_requirements:
        lines.append(
            f"| {tool.name} | `{tool.executable}` | "
            f"{'yes' if tool.required else 'no'} | {tool.role} | {tool.note} |"
        )
    lines.extend(
        [
            "",
            "## Constraint Requirements",
            "",
            "| Signal | Constraint | Fail if missing | Source | Note |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for constraint in gate.constraint_requirements:
        lines.append(
            f"| `{constraint.logical_signal}` | {constraint.constraint_kind} | "
            f"{'yes' if constraint.fail_if_missing else 'no'} | "
            f"{constraint.source} | {constraint.note} |"
        )
    lines.extend(
        [
            "",
            "## Gate Steps",
            "",
            "| Step | Command | Pass criteria | Failure conditions |",
            "| --- | --- | --- | --- |",
        ]
    )
    for step in gate.steps:
        failures = ", ".join(f"`{failure}`" for failure in step.failure_conditions)
        lines.append(
            f"| `{step.name}` | `{step.command}` | {step.pass_criteria} | {failures} |"
        )
    lines.extend(
        [
            "",
            "## Report Requirements",
            "",
            "| Report | Producer | Required contents |",
            "| --- | --- | --- |",
        ]
    )
    for report in gate.reports:
        contents = ", ".join(f"`{token}`" for token in report.must_contain) or "file exists"
        lines.append(f"| `{report.path}` | `{report.producer_step}` | {contents} |")
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {blocker}." for blocker in gate.blockers)
    lines.append("")
    return "\n".join(lines)


def validate_fpga_synthesis_gate(root: Path | None = None) -> tuple[str, ...]:
    if root is None:
        root = Path(__file__).resolve().parents[2]
    gate = fpga_synthesis_gate()
    issues: list[str] = []

    if gate.story != FPGA_SYNTHESIS_STORY:
        issues.append(f"synthesis gate story must be {FPGA_SYNTHESIS_STORY}")
    if gate.board != fpga_first_test.TARGET_BOARD_NAME:
        issues.append("synthesis gate board must match the first-test profile")
    if gate.device != fpga_first_test.TARGET_FPGA_DEVICE:
        issues.append("synthesis gate device must match the first-test profile")
    if gate.top_module != fpga_first_test.FPGA_TOP_MODULE:
        issues.append("synthesis gate top module must match the FPGA top profile")
    if gate.target_clock_hz > fpga_first_test.FPGA_FIRST_TEST_PROFILE.clock_reset.maximum_core_clock_hz:
        issues.append("synthesis gate target clock exceeds first-test profile limit")

    for path in gate.source_files:
        if not (root / path).exists():
            issues.append(f"missing synthesis source {path.as_posix()}")
    for path in fpga_smoke.FPGA_SMOKE_SOURCE_FILES:
        if not (root / path).exists():
            issues.append(f"missing Verilator preflight source {path.as_posix()}")

    tool_names = {tool.name for tool in gate.tool_requirements}
    for required in ("Verilator", "Gowin EDA command shell", "Gowin Programmer"):
        if required not in tool_names:
            issues.append(f"missing tool requirement {required}")

    constraints = {constraint.logical_signal: constraint for constraint in gate.constraint_requirements}
    for required in ("board_clk_i", "board_reset_n_i", "pass_led_o", "fail_led_o", "heartbeat_led_o"):
        constraint = constraints.get(required)
        if constraint is None:
            issues.append(f"missing constraint requirement {required}")
        elif not constraint.fail_if_missing:
            issues.append(f"{required} must fail the gate if unconstrained")

    steps = {step.name: step for step in gate.steps}
    for required in (
        "rtl_preflight",
        "gate_profile_check",
        "emit_gowin_tcl",
        "gowin_synth_place_route",
        "report_audit",
    ):
        if required not in steps:
            issues.append(f"missing gate step {required}")
    if "run all" not in gowin_tcl_script(gate):
        issues.append("Gowin Tcl script must run all")
    if gate.constraint_file.as_posix() not in gowin_tcl_script(gate):
        issues.append("Gowin Tcl script must include the board constraint file")
    if not any("timing" in report.path.lower() for report in gate.reports):
        issues.append("synthesis gate must require a timing report")
    if not any(report.path.endswith("*.fs") for report in gate.reports):
        issues.append("synthesis gate must require a bitstream file")
    if not gate.blockers:
        issues.append("synthesis gate must record board verification blockers")

    doc = _read_if_exists(root / FPGA_SYNTHESIS_DOC)
    for token in (
        "Story: I23-S05",
        FPGA_SYNTHESIS_TOOL,
        FPGA_SYNTHESIS_BOARD,
        FPGA_SYNTHESIS_DEVICE,
        FPGA_SYNTHESIS_IDE_PACKAGE,
        FPGA_SYNTHESIS_TOP_MODULE,
        "gw_sh",
        "run all",
        "board_clk_i",
        "board_reset_n_i",
        "pass_led_o",
        "fail_led_o",
        "heartbeat_led_o",
        "unconstrained_clock_or_reset",
        "negative_timing_slack_at_first_test_clock",
        "I23-S06",
    ):
        if token not in doc:
            issues.append(f"{FPGA_SYNTHESIS_DOC.as_posix()} missing {token}")

    return tuple(issues)


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")
