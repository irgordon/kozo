from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness import controlled_runtime_loop_contract as contract_module
from harness.abi_manifest import ROOT
from harness.codes import CONTROLLED_RUNTIME_LOOP_EVIDENCE_INVALID, OK
from harness.runtime_evidence_taxonomy import get_expected_smoke_marker, get_smoke_marker_order
from harness.validator import BaseValidator, ValidationResult

_CONTRACT_PATH = contract_module.CONTRACT_PATH
_RUNTIME_SOURCE_PATH = ROOT / "kernel" / "runtime_progression.odin"
_BOOT_SOURCE_PATH = ROOT / "kernel" / "arch" / "x86_64" / "boot.asm"
_ELF_REPORT_PATH = ROOT / "artifacts" / "runtime" / "kernel_elf_report.json"
_METADATA_PATH = ROOT / "artifacts" / "runtime" / "qemu_smoke.metadata.json"
_SERIAL_LOG_PATH = ROOT / "artifacts" / "runtime" / "qemu_smoke.log"
_STAGES_PATH = ROOT / "contracts" / "runtime_progression_stages.v0.json"
_TOOLING_BLOCKERS = {
    "missing_iso_generation_tooling",
    "missing_qemu_tooling",
    "missing_boot_image",
    "qemu_launch_failed",
}
_REQUIRED_SYMBOLS = (
    "controlled_runtime_loop",
    "runtime_loop_state",
    "runtime_serial_write_loop_enter_marker",
    "runtime_serial_write_loop_iter_1_marker",
    "runtime_serial_write_loop_iter_2_marker",
    "runtime_serial_write_loop_iter_3_marker",
    "runtime_serial_write_loop_exit_marker",
)


@dataclass(frozen=True)
class ControlledRuntimeLoopEvidenceIssue:
    reason: str
    contract_field: str
    detail: str


@dataclass(frozen=True)
class ControlledRuntimeLoopContext:
    contract: contract_module.ControlledRuntimeLoopContract
    runtime_lines: tuple[str, ...]
    boot_lines: tuple[str, ...]


class ControlledRuntimeLoopEvidenceValidator(BaseValidator):
    name = "controlled_runtime_loop_evidence"
    subsystem = "controlled_runtime_loop_evidence"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _evidence_issue()
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Controlled runtime loop evidence aligns bounded Odin state, ELF control flow, ordered markers, status, and terminal halt",
        )


def _evidence_issue() -> ControlledRuntimeLoopEvidenceIssue | None:
    context = _load_context()
    if isinstance(context, ControlledRuntimeLoopEvidenceIssue):
        return context
    return _first_issue(
        _runtime_structure_issue(context),
        _marker_bridge_issue(context),
        _binary_evidence_issue(),
        _stage_status_issue(),
        _qemu_evidence_issue(),
    )


def _load_context() -> ControlledRuntimeLoopContext | ControlledRuntimeLoopEvidenceIssue:
    contract = _load_contract()
    if isinstance(contract, ControlledRuntimeLoopEvidenceIssue):
        return contract
    runtime = _load_source(_RUNTIME_SOURCE_PATH, "current_state.source_file")
    if isinstance(runtime, ControlledRuntimeLoopEvidenceIssue):
        return runtime
    boot = _load_source(_BOOT_SOURCE_PATH, "terminal_behavior.halt_contract")
    if isinstance(boot, ControlledRuntimeLoopEvidenceIssue):
        return boot
    return ControlledRuntimeLoopContext(
        contract=contract,
        runtime_lines=tuple(_normalized_lines(runtime)),
        boot_lines=tuple(_normalized_lines(boot)),
    )


def _load_contract():
    try:
        return contract_module.load_controlled_runtime_loop_contract(_CONTRACT_PATH)
    except json.JSONDecodeError as exc:
        return _issue("invalid_contract_json", "contract", f"Controlled runtime loop contract is invalid JSON: {exc}")
    except (OSError, KeyError, TypeError, ValueError) as exc:
        return _issue("contract_schema_violation", "contract", f"Controlled runtime loop contract is unavailable or malformed: {exc}")


def _load_source(path: Path, field: str) -> str | ControlledRuntimeLoopEvidenceIssue:
    if path.is_file():
        return path.read_text()
    return _issue("missing_source", field, f"Controlled runtime loop source is missing: {path}")


def _runtime_structure_issue(context: ControlledRuntimeLoopContext) -> ControlledRuntimeLoopEvidenceIssue | None:
    return _first_issue(
        _entry_issue(context.runtime_lines),
        _state_issue(context.runtime_lines),
        _loop_issue(context.runtime_lines),
        _completion_issue(context.runtime_lines),
        _return_boundary_issue(context.boot_lines),
    )


def _entry_issue(lines: tuple[str, ...]) -> ControlledRuntimeLoopEvidenceIssue | None:
    expected = (
        "runtime_emit_init_marker()",
        "loop_status := controlled_runtime_loop()",
        "if loop_status != RUNTIME_PROGRESSION_OK {",
        "return loop_status",
        '@(export)',
        'controlled_runtime_loop :: proc "contextless" () -> u32 {',
        "runtime_loop_reset_state()",
        "if runtime_loop_limit() != RUNTIME_LOOP_ITERATION_LIMIT {",
        "return RUNTIME_LOOP_INVALID_LIMIT",
        "if !runtime_loop_initial_state_is_valid() {",
        "return RUNTIME_LOOP_INVALID_INITIAL_STATE",
        "runtime_serial_write_loop_enter_marker()",
    )
    return _ordered_issue(lines, expected, "loop_entry_mismatch", "loop.entry")


def _state_issue(lines: tuple[str, ...]) -> ControlledRuntimeLoopEvidenceIssue | None:
    required = (
        "runtime_loop_state: Runtime_Loop_State",
        "intrinsics.volatile_store(&runtime_loop_state.iteration_limit, RUNTIME_LOOP_ITERATION_LIMIT)",
        "intrinsics.volatile_store(&runtime_loop_state.iteration_count, 0)",
        "intrinsics.volatile_store(&runtime_loop_state.accumulator, 0)",
        "intrinsics.volatile_store(&runtime_loop_state.status, RUNTIME_LOOP_STATUS_IDLE)",
        "intrinsics.volatile_store(&runtime_loop_state.reserved, 0)",
        "return intrinsics.volatile_load(&runtime_loop_state.iteration_count)",
        "return intrinsics.volatile_load(&runtime_loop_state.accumulator)",
    )
    return _required_lines_issue(lines, required, "volatile_state_missing", "state")


def _loop_issue(lines: tuple[str, ...]) -> ControlledRuntimeLoopEvidenceIssue | None:
    expected = (
        "for runtime_loop_iteration_count() < runtime_loop_limit() {",
        "status := runtime_loop_execute_iteration()",
        "if status != RUNTIME_PROGRESSION_OK {",
        "return status",
        "next_count := runtime_loop_iteration_count() + 1",
        "next_accumulator := runtime_loop_accumulator() + next_count",
        "intrinsics.volatile_store(&runtime_loop_state.iteration_count, next_count)",
        "intrinsics.volatile_store(&runtime_loop_state.accumulator, next_accumulator)",
        "if !runtime_loop_iteration_state_is_valid(next_count) {",
        "return RUNTIME_LOOP_ITERATION_STATE_MISMATCH",
        "if next_accumulator != runtime_loop_expected_accumulator(next_count) {",
        "return RUNTIME_LOOP_ACCUMULATOR_MISMATCH",
        "if !runtime_emit_loop_iteration_marker(next_count) {",
    )
    return _ordered_issue(lines, expected, "loop_sequence_mismatch", "loop")


def _completion_issue(lines: tuple[str, ...]) -> ControlledRuntimeLoopEvidenceIssue | None:
    expected = (
        "if runtime_loop_iteration_count() != runtime_loop_limit() {",
        "return RUNTIME_LOOP_TERMINAL_COUNT_MISMATCH",
        "if runtime_loop_accumulator() != RUNTIME_LOOP_EXPECTED_ACCUMULATOR {",
        "return RUNTIME_LOOP_ACCUMULATOR_MISMATCH",
        "runtime_loop_set_status(RUNTIME_LOOP_STATUS_COMPLETED)",
        "if runtime_loop_status() != RUNTIME_LOOP_STATUS_COMPLETED || runtime_loop_reserved() != 0 {",
        "return RUNTIME_LOOP_TERMINAL_STATUS_MISMATCH",
        "runtime_serial_write_loop_exit_marker()",
        "return RUNTIME_PROGRESSION_OK",
    )
    return _ordered_issue(lines, expected, "loop_completion_mismatch", "terminal_behavior")


def _return_boundary_issue(lines: tuple[str, ...]) -> ControlledRuntimeLoopEvidenceIssue | None:
    expected = (
        "call runtime_progression_entry",
        "cmp eax, 0",
        "jne .halt",
        "WRITE_COM1_MARKER runtime_return_marker, runtime_return_marker_end",
        "cli",
        ".halt:",
        "hlt",
        "jmp .halt",
    )
    return _ordered_issue(lines, expected, "halt_path_mismatch", "terminal_behavior")


def _marker_bridge_issue(context: ControlledRuntimeLoopContext) -> ControlledRuntimeLoopEvidenceIssue | None:
    ownership_issue = _required_lines_issue(
        context.runtime_lines,
        (
            "runtime_serial_write_loop_enter_marker()",
            "runtime_serial_write_loop_iter_1_marker()",
            "runtime_serial_write_loop_iter_2_marker()",
            "runtime_serial_write_loop_iter_3_marker()",
            "runtime_serial_write_loop_exit_marker()",
        ),
        "marker_bridge_missing",
        "markers.emission_owner",
    )
    if ownership_issue is not None:
        return ownership_issue
    pairs = (
        ("runtime_serial_write_loop_enter_marker", "runtime_loop_enter_marker"),
        ("runtime_serial_write_loop_iter_1_marker", "runtime_loop_iter_1_marker"),
        ("runtime_serial_write_loop_iter_2_marker", "runtime_loop_iter_2_marker"),
        ("runtime_serial_write_loop_iter_3_marker", "runtime_loop_iter_3_marker"),
        ("runtime_serial_write_loop_exit_marker", "runtime_loop_exit_marker"),
    )
    for bridge, marker in pairs:
        expected = (f"{bridge}:", f"WRITE_COM1_MARKER {marker}, {marker}_end", "ret")
        issue = _ordered_issue(context.boot_lines, expected, "marker_bridge_missing", f"markers.{bridge}")
        if issue is not None:
            return issue
    return None


def _binary_evidence_issue() -> ControlledRuntimeLoopEvidenceIssue | None:
    report = _load_json(_ELF_REPORT_PATH, "kernel_elf_report")
    if isinstance(report, ControlledRuntimeLoopEvidenceIssue):
        return report
    record = report.get("controlled_runtime_loop")
    if not isinstance(record, dict):
        return _issue("binary_loop_missing", "kernel_elf_report.controlled_runtime_loop", "Kernel ELF report must record controlled loop evidence")
    issue = _binary_symbol_issue(record)
    if issue is not None:
        return issue
    if record.get("backward_branch_present") is not True:
        return _issue("binary_backward_edge_missing", "kernel_elf_report.controlled_runtime_loop.backward_branch_present", "Controlled runtime loop must retain a backward branch in the linked ELF")
    if record.get("terminal_comparison_present") is not True:
        return _issue("binary_terminal_comparison_missing", "kernel_elf_report.controlled_runtime_loop.terminal_comparison_present", "Controlled runtime loop must retain a terminal comparison in the linked ELF")
    return None


def _binary_symbol_issue(record: dict[str, object]) -> ControlledRuntimeLoopEvidenceIssue | None:
    symbols = record.get("symbols")
    if not isinstance(symbols, dict):
        return _issue("binary_symbol_missing", "kernel_elf_report.controlled_runtime_loop.symbols", "Kernel ELF report must record controlled loop symbols")
    for symbol in _REQUIRED_SYMBOLS:
        value = symbols.get(symbol)
        if not isinstance(value, dict) or value.get("present") is not True or not value.get("address"):
            return _issue("binary_symbol_missing", f"kernel_elf_report.controlled_runtime_loop.symbols.{symbol}", f"Kernel ELF is missing controlled loop symbol: {symbol}")
    return None


def _stage_status_issue() -> ControlledRuntimeLoopEvidenceIssue | None:
    document = _load_json(_STAGES_PATH, "runtime_progression_stages")
    if isinstance(document, ControlledRuntimeLoopEvidenceIssue):
        return document
    statuses = {
        stage.get("stage_name"): stage.get("status")
        for stage in document.get("stages", [])
        if isinstance(stage, dict)
    }
    if statuses.get("CONTROLLED_RUNTIME_LOOP") != "proven":
        return _issue("stage_status_mismatch", "runtime_progression_stages.CONTROLLED_RUNTIME_LOOP.status", "Controlled runtime loop must remain proven after hosted acceptance")
    return None


def _qemu_evidence_issue() -> ControlledRuntimeLoopEvidenceIssue | None:
    metadata = _load_json(_METADATA_PATH, "qemu_smoke.metadata")
    if isinstance(metadata, ControlledRuntimeLoopEvidenceIssue):
        return metadata
    if metadata.get("outcome") == "blocked" and metadata.get("blocker_category") in _TOOLING_BLOCKERS:
        return None
    if metadata.get("outcome") != "pass":
        return _issue("runtime_loop_evidence_missing", "qemu_smoke.outcome", "Controlled loop requires passing QEMU evidence or an allowed local tooling blocker")
    return _passing_qemu_issue(metadata)


def _passing_qemu_issue(metadata: dict[str, object]) -> ControlledRuntimeLoopEvidenceIssue | None:
    markers = get_smoke_marker_order()
    if metadata.get("expected_marker") != get_expected_smoke_marker():
        return _issue("metadata_log_mismatch", "qemu_smoke.expected_marker", "QEMU expected marker must match runtime taxonomy")
    if metadata.get("observed_markers") != list(markers):
        return _issue("metadata_log_mismatch", "qemu_smoke.observed_markers", "QEMU metadata must contain the complete controlled loop sequence")
    if not _SERIAL_LOG_PATH.is_file() or not _ordered_markers_present(_SERIAL_LOG_PATH.read_text(errors="replace"), markers):
        return _issue("metadata_log_mismatch", "qemu_smoke.serial_log", "QEMU serial log must contain the ordered controlled loop sequence")
    return None


def _load_json(path: Path, field: str):
    if not path.is_file():
        return _issue("missing_evidence", field, f"Required controlled loop evidence is missing: {path}")
    try:
        value = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return _issue("invalid_evidence", field, f"Controlled loop evidence is invalid JSON: {exc}")
    if not isinstance(value, dict):
        return _issue("invalid_evidence", field, "Controlled loop evidence must be a JSON object")
    return value


def _normalized_lines(source: str) -> list[str]:
    lines = []
    for raw_line in source.splitlines():
        line = raw_line.split(";", 1)[0].strip()
        if line:
            lines.append(" ".join(line.split()))
    return lines


def _required_lines_issue(lines, required, reason: str, field: str):
    for item in required:
        if item not in lines:
            return _issue(reason, field, f"Controlled loop source must contain: {item}")
    return None


def _ordered_issue(lines, expected, reason: str, field: str):
    position = -1
    for item in expected:
        position = _line_index(lines, item, position + 1)
        if position is None:
            return _issue(reason, field, f"Controlled loop path is missing ordered operation: {item}")
    return None


def _line_index(lines, expected: str, start: int = 0) -> int | None:
    return next((index for index in range(start, len(lines)) if lines[index] == expected), None)


def _ordered_markers_present(text: str, markers: tuple[str, ...]) -> bool:
    position = -1
    for marker in markers:
        position = text.find(marker, position + 1)
        if position < 0:
            return False
    return True


def _first_issue(*issues):
    return next((issue for issue in issues if issue is not None), None)


def _issue(reason: str, field: str, detail: str) -> ControlledRuntimeLoopEvidenceIssue:
    return ControlledRuntimeLoopEvidenceIssue(reason, field, detail)


def _failure(issue: ControlledRuntimeLoopEvidenceIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=CONTROLLED_RUNTIME_LOOP_EVIDENCE_INVALID,
        detail=issue.detail,
        action="Keep controlled loop contract, Odin state, ELF control flow, QEMU evidence, stage status, and terminal halt aligned",
        meta={"reason": issue.reason, "contract_field": issue.contract_field},
    )
