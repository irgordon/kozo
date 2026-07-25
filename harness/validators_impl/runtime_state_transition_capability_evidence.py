from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness import runtime_state_transition_capability as contract_module
from harness.abi_manifest import ROOT
from harness.codes import OK, RUNTIME_STATE_TRANSITION_CAPABILITY_EVIDENCE_INVALID
from harness.runtime_evidence_taxonomy import get_expected_smoke_marker, get_smoke_marker_order
from harness.validator import BaseValidator, ValidationResult

_CONTRACT_PATH = contract_module.CONTRACT_PATH
_CAPABILITY_SOURCE_PATH = ROOT / "kernel" / "runtime_capability.odin"
_PROGRESSION_SOURCE_PATH = ROOT / "kernel" / "runtime_progression.odin"
_BOOT_SOURCE_PATH = ROOT / "kernel" / "arch" / "x86_64" / "boot.asm"
_ELF_REPORT_PATH = ROOT / "artifacts" / "runtime" / "kernel_elf_report.json"
_METADATA_PATH = ROOT / "artifacts" / "runtime" / "qemu_smoke.metadata.json"
_SERIAL_LOG_PATH = ROOT / "artifacts" / "runtime" / "qemu_smoke.log"
_TOOLING_BLOCKERS = {
    "missing_iso_generation_tooling",
    "missing_qemu_tooling",
    "missing_boot_image",
    "qemu_launch_failed",
}
_REQUIRED_SYMBOLS = (
    "runtime_state_transition_cell",
    "initialize_runtime_state_transition_cell",
    "execute_second_governed_capability",
    "dispatch_runtime_capability",
    "dispatch_runtime_state_transition",
    "transition_runtime_state",
    "runtime_state_cell_store",
    "runtime_state_cell_state",
    "runtime_state_cell_reserved",
    "runtime_state_cell_generation",
    "runtime_serial_write_state_update_enter_marker",
    "runtime_serial_write_state_update_ok_marker",
    "runtime_serial_write_second_capability_marker",
)
_MARKER_CALLS = (
    "runtime_serial_write_state_update_enter_marker()",
    "runtime_serial_write_state_update_ok_marker()",
    "runtime_serial_write_second_capability_marker()",
)


@dataclass(frozen=True)
class StateTransitionEvidenceIssue:
    reason: str
    contract_field: str
    detail: str


@dataclass(frozen=True)
class StateTransitionContext:
    capability_lines: tuple[str, ...]
    progression_lines: tuple[str, ...]
    boot_lines: tuple[str, ...]


class RuntimeStateTransitionCapabilityEvidenceValidator(BaseValidator):
    name = "runtime_state_transition_capability_evidence"
    subsystem = "runtime_state_transition_capability_evidence"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _evidence_issue()
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Runtime state transition evidence aligns bounded volatile mutation, response proof, markers, ELF, first capability, and halt",
        )


def _evidence_issue() -> StateTransitionEvidenceIssue | None:
    context = _load_context()
    if isinstance(context, StateTransitionEvidenceIssue):
        return context
    checks = (
        lambda: _progression_issue(context),
        lambda: _layout_issue(context),
        lambda: _state_initialization_issue(context),
        lambda: _request_issue(context),
        lambda: _dispatcher_issue(context),
        lambda: _mutation_issue(context),
        lambda: _volatile_access_issue(context),
        lambda: _response_issue(context),
        lambda: _coordinator_issue(context),
        lambda: _marker_bridge_issue(context),
        lambda: _halt_issue(context),
        _binary_issue,
        _qemu_issue,
    )
    for check in checks:
        issue = check()
        if issue is not None:
            return issue
    return None


def _load_context() -> StateTransitionContext | StateTransitionEvidenceIssue:
    contract_issue = _contract_issue()
    if contract_issue is not None:
        return contract_issue
    loaded = (
        _load_source(_CAPABILITY_SOURCE_PATH, "capability.source_file"),
        _load_source(_PROGRESSION_SOURCE_PATH, "execution_order"),
        _load_source(_BOOT_SOURCE_PATH, "failure_behavior.halt_contract"),
    )
    issue = next((item for item in loaded if isinstance(item, StateTransitionEvidenceIssue)), None)
    if issue is not None:
        return issue
    return StateTransitionContext(
        *(
            tuple(_normalized_lines(item))
            for item in loaded
        )
    )


def _contract_issue() -> StateTransitionEvidenceIssue | None:
    try:
        contract_module.load_runtime_state_transition_capability(_CONTRACT_PATH)
    except json.JSONDecodeError as exc:
        return _issue("invalid_contract_json", "contract", f"State transition contract is invalid JSON: {exc}")
    except (OSError, KeyError, TypeError, ValueError) as exc:
        return _issue("contract_schema_violation", "contract", f"State transition contract is unavailable or malformed: {exc}")
    return None


def _load_source(path: Path, field: str) -> str | StateTransitionEvidenceIssue:
    if path.is_file():
        return path.read_text()
    return _issue("missing_source", field, f"State transition source is missing: {path}")


def _progression_issue(context: StateTransitionContext) -> StateTransitionEvidenceIssue | None:
    expected = (
        "if !initialize_runtime_state_transition_cell() {",
        "return RUNTIME_PROGRESSION_STATE_FAILURE",
        "runtime_emit_init_marker()",
        "loop_status := controlled_runtime_loop()",
        "if loop_status != RUNTIME_PROGRESSION_OK {",
        "return loop_status",
        "first_capability_status := execute_first_governed_capability()",
        "if first_capability_status != RUNTIME_PROGRESSION_OK {",
        "return first_capability_status",
        "return execute_second_governed_capability()",
    )
    return _ordered_issue(context.progression_lines, expected, "capability_path_missing", "execution_order")


def _layout_issue(context: StateTransitionContext) -> StateTransitionEvidenceIssue | None:
    required = (
        "Runtime_State_Cell :: struct {",
        "state: u32,",
        "reserved: u32,",
        "generation: u64,",
        "Runtime_State_Transition_Request :: struct {",
        "expected_state: u32,",
        "requested_state: u32,",
        "expected_generation: u64,",
        "Runtime_State_Transition_Response :: struct {",
        "previous_state: u32,",
        "current_state: u32,",
        "previous_generation: u64,",
        "current_generation: u64,",
        "#assert(size_of(Runtime_State_Cell) == RUNTIME_STATE_CELL_SIZE)",
        "#assert(align_of(Runtime_State_Cell) == RUNTIME_STATE_CELL_ALIGNMENT)",
        "#assert(size_of(Runtime_State_Transition_Request) == RUNTIME_STATE_TRANSITION_REQUEST_SIZE)",
        "#assert(size_of(Runtime_State_Transition_Response) == RUNTIME_STATE_TRANSITION_RESPONSE_SIZE)",
    )
    return _required_lines_issue(context.capability_lines, required, "source_layout_mismatch", "state_request_response_layout")


def _state_initialization_issue(context: StateTransitionContext) -> StateTransitionEvidenceIssue | None:
    expected = (
        "initialize_runtime_state_transition_cell :: proc \"contextless\" () -> bool {",
        "runtime_state_cell_store(RUNTIME_STATE_READY, RUNTIME_STATE_INITIAL_GENERATION)",
        "intrinsics.volatile_store(&runtime_state_transition_cell.reserved, 0)",
        "return runtime_state_cell_is_ready()",
    )
    return _ordered_issue(context.capability_lines, expected, "state_initialization_missing", "state.initial_values")


def _request_issue(context: StateTransitionContext) -> StateTransitionEvidenceIssue | None:
    required = (
        "if request == nil || uintptr(request) % RUNTIME_STATE_TRANSITION_REQUEST_ALIGNMENT != 0 {",
        "return RUNTIME_CAPABILITY_INVALID_REQUEST_POINTER",
        "if !runtime_state_transition_response_pointer_is_valid(request, response) {",
        "return RUNTIME_CAPABILITY_INVALID_RESPONSE_POINTER",
        "if request.version != RUNTIME_STATE_TRANSITION_REQUEST_VERSION {",
        "return RUNTIME_CAPABILITY_UNSUPPORTED_REQUEST_VERSION",
        "if request.capability_id != RUNTIME_STATE_TRANSITION_CAPABILITY_ID {",
        "return RUNTIME_CAPABILITY_UNSUPPORTED_CAPABILITY",
        "if request.flags != RUNTIME_STATE_TRANSITION_SUPPORTED_FLAGS {",
        "return RUNTIME_CAPABILITY_UNSUPPORTED_FLAGS",
        "if request.reserved != 0 {",
        "return RUNTIME_CAPABILITY_INVALID_RESERVED_FIELD",
        "if request.expected_generation != RUNTIME_STATE_INITIAL_GENERATION {",
        "return RUNTIME_STATE_STALE_GENERATION",
        "if request.expected_state != RUNTIME_STATE_READY ||",
        "request.requested_state != RUNTIME_STATE_ACTIVE {",
        "return RUNTIME_STATE_INVALID_TRANSITION",
    )
    return _required_lines_issue(context.capability_lines, required, "request_validation_missing", "request")


def _dispatcher_issue(context: StateTransitionContext) -> StateTransitionEvidenceIssue | None:
    expected = (
        "header_status := validate_runtime_capability_header(request)",
        "if header_status != RUNTIME_PROGRESSION_OK {",
        "return header_status",
        "header := cast(^Runtime_Capability_Header)(request)",
        "switch header.capability_id {",
        "case RUNTIME_STATUS_QUERY_CAPABILITY_ID:",
        "return dispatch_runtime_status_query(",
        "case RUNTIME_STATE_TRANSITION_CAPABILITY_ID:",
        "return dispatch_runtime_state_transition(",
        "case:",
        "return RUNTIME_CAPABILITY_UNSUPPORTED_CAPABILITY",
    )
    issue = _ordered_issue(context.capability_lines, expected, "dispatcher_sequence_mismatch", "execution_order")
    if issue is not None:
        return issue
    if context.capability_lines.count("runtime_serial_write_capability_dispatch_marker()") != 1:
        return _issue("generic_marker_duplicated", "markers.generic_dispatch_marker_repeated", "Generic dispatch marker must remain owned by capability ID 1")
    return None


def _mutation_issue(context: StateTransitionContext) -> StateTransitionEvidenceIssue | None:
    expected = (
        "previous_state := runtime_state_cell_state()",
        "previous_generation := runtime_state_cell_generation()",
        "transition_status := validate_current_runtime_state(",
        "if transition_status != RUNTIME_PROGRESSION_OK {",
        "return transition_status",
        "runtime_serial_write_state_update_enter_marker()",
        "runtime_state_cell_store(RUNTIME_STATE_ACTIVE, RUNTIME_STATE_TERMINAL_GENERATION)",
        "if !runtime_state_cell_is_active() {",
        "runtime_state_cell_store(previous_state, previous_generation)",
        "return RUNTIME_STATE_READBACK_FAILED",
        "populate_runtime_state_transition_response(response, previous_state, previous_generation)",
        "if !validate_runtime_state_transition_response(response) {",
        "return RUNTIME_CAPABILITY_RESPONSE_VALIDATION_FAILURE",
        "runtime_serial_write_state_update_ok_marker()",
        "return RUNTIME_PROGRESSION_OK",
    )
    issue = _ordered_issue(context.capability_lines, expected, "mutation_sequence_mismatch", "transition")
    if issue is not None:
        return issue
    if any(context.capability_lines.count(marker) != 1 for marker in _MARKER_CALLS):
        return _issue("success_marker_on_failure_path", "failure_behavior.success_markers_forbidden_on_failure", "Each state transition success marker must have exactly one call site")
    return None


def _volatile_access_issue(context: StateTransitionContext) -> StateTransitionEvidenceIssue | None:
    required = (
        'import "base:intrinsics"',
        "intrinsics.volatile_store(&runtime_state_transition_cell.state, state)",
        "intrinsics.volatile_store(&runtime_state_transition_cell.generation, generation)",
        "return intrinsics.volatile_load(&runtime_state_transition_cell.state)",
        "return intrinsics.volatile_load(&runtime_state_transition_cell.reserved)",
        "return intrinsics.volatile_load(&runtime_state_transition_cell.generation)",
    )
    return _required_lines_issue(context.capability_lines, required, "volatile_access_missing", "state.volatile_access_required")


def _response_issue(context: StateTransitionContext) -> StateTransitionEvidenceIssue | None:
    required = (
        "response.version = RUNTIME_STATE_TRANSITION_RESPONSE_VERSION",
        "response.capability_id = RUNTIME_STATE_TRANSITION_CAPABILITY_ID",
        "response.status = RUNTIME_PROGRESSION_OK",
        "response.previous_state = previous_state",
        "response.current_state = runtime_state_cell_state()",
        "response.reserved_0 = 0",
        "response.previous_generation = previous_generation",
        "response.current_generation = runtime_state_cell_generation()",
        "response.reserved_1 = 0",
        "return response.version == RUNTIME_STATE_TRANSITION_RESPONSE_VERSION &&",
        "response.previous_state == RUNTIME_STATE_READY &&",
        "response.current_state == RUNTIME_STATE_ACTIVE &&",
        "response.previous_generation == RUNTIME_STATE_INITIAL_GENERATION &&",
        "response.current_generation == RUNTIME_STATE_TERMINAL_GENERATION &&",
        "response.reserved_1 == 0",
    )
    return _required_lines_issue(context.capability_lines, required, "response_validation_missing", "response")


def _coordinator_issue(context: StateTransitionContext) -> StateTransitionEvidenceIssue | None:
    expected = (
        "request := governed_runtime_state_transition_request()",
        "response: Runtime_State_Transition_Response = ---",
        "status := dispatch_runtime_capability(cast(rawptr)(&request), cast(rawptr)(&response))",
        "if status != RUNTIME_PROGRESSION_OK {",
        "return status",
        "if !validate_runtime_state_transition_response(&response) {",
        "return RUNTIME_CAPABILITY_RESPONSE_VALIDATION_FAILURE",
        "runtime_serial_write_second_capability_marker()",
        "return RUNTIME_PROGRESSION_OK",
    )
    return _ordered_issue(context.capability_lines, expected, "coordinator_sequence_mismatch", "execution_order")


def _marker_bridge_issue(context: StateTransitionContext) -> StateTransitionEvidenceIssue | None:
    pairs = (
        ("runtime_serial_write_state_update_enter_marker", "runtime_state_update_enter_marker"),
        ("runtime_serial_write_state_update_ok_marker", "runtime_state_update_ok_marker"),
        ("runtime_serial_write_second_capability_marker", "second_capability_marker"),
    )
    for bridge, marker in pairs:
        expected = (f"{bridge}:", f"WRITE_COM1_MARKER {marker}, {marker}_end", "ret")
        issue = _ordered_issue(context.boot_lines, expected, "marker_bridge_missing", f"markers.{bridge}")
        if issue is not None:
            return issue
    return None


def _halt_issue(context: StateTransitionContext) -> StateTransitionEvidenceIssue | None:
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
    return _ordered_issue(context.boot_lines, expected, "halt_path_missing", "failure_behavior.halt_contract")


def _binary_issue() -> StateTransitionEvidenceIssue | None:
    report = _load_json(_ELF_REPORT_PATH, "kernel_elf_report")
    if isinstance(report, StateTransitionEvidenceIssue):
        return report
    record = report.get("runtime_state_transition_capability")
    if not isinstance(record, dict):
        return _issue("binary_capability_missing", "kernel_elf_report.runtime_state_transition_capability", "Kernel ELF report must record state transition evidence")
    symbols = record.get("symbols")
    if not isinstance(symbols, dict):
        return _issue("binary_symbol_missing", "kernel_elf_report.runtime_state_transition_capability.symbols", "Kernel ELF report must record state transition symbols")
    for symbol in _REQUIRED_SYMBOLS:
        value = symbols.get(symbol)
        if not isinstance(value, dict) or value.get("present") is not True or not value.get("address"):
            return _issue("binary_symbol_missing", f"kernel_elf_report.runtime_state_transition_capability.symbols.{symbol}", f"Kernel ELF is missing state transition symbol: {symbol}")
    return _binary_behavior_issue(record)


def _binary_behavior_issue(record: dict[str, object]) -> StateTransitionEvidenceIssue | None:
    if record.get("progression_call_present") is not True:
        return _issue("binary_call_missing", "kernel_elf_report.runtime_state_transition_capability.progression_call_present", "Runtime progression must call the second capability")
    if record.get("dispatcher_route_present") is not True:
        return _issue("binary_call_missing", "kernel_elf_report.runtime_state_transition_capability.dispatcher_route_present", "Dispatcher must retain the state transition route")
    if int(record.get("volatile_memory_access_count", 0)) < 4:
        return _issue("binary_volatile_access_missing", "kernel_elf_report.runtime_state_transition_capability.volatile_memory_access_count", "Kernel ELF must retain bounded state loads and stores")
    if int(record.get("handler_comparison_count", 0)) < 1:
        return _issue("binary_comparison_missing", "kernel_elf_report.runtime_state_transition_capability.handler_comparison_count", "Kernel ELF must retain state transition comparisons")
    if (
        record.get("state_cell_size_bytes") != 16
        or record.get("state_cell_aligned") is not True
    ):
        return _issue(
            "binary_state_geometry_invalid",
            "kernel_elf_report.runtime_state_transition_capability.state_cell_geometry",
            "Runtime state cell must retain its 16-byte size and 8-byte alignment",
        )
    return None


def _qemu_issue() -> StateTransitionEvidenceIssue | None:
    metadata = _load_json(_METADATA_PATH, "qemu_smoke.metadata")
    if isinstance(metadata, StateTransitionEvidenceIssue):
        return metadata
    if metadata.get("outcome") == "blocked" and metadata.get("blocker_category") in _TOOLING_BLOCKERS:
        return None
    if metadata.get("outcome") != "pass":
        return _issue("capability_evidence_missing", "qemu_smoke.outcome", "State transition requires passing QEMU evidence or an allowed local tooling blocker")
    markers = get_smoke_marker_order()
    if metadata.get("expected_marker") != get_expected_smoke_marker():
        return _issue("metadata_log_mismatch", "qemu_smoke.expected_marker", "QEMU expected marker must match runtime taxonomy")
    if metadata.get("observed_markers") != list(markers):
        return _issue("metadata_log_mismatch", "qemu_smoke.observed_markers", "QEMU metadata must contain the complete state transition sequence")
    if not _SERIAL_LOG_PATH.is_file() or not _ordered_markers_present(_SERIAL_LOG_PATH.read_text(errors="replace"), markers):
        return _issue("metadata_log_mismatch", "qemu_smoke.serial_log", "QEMU serial log must contain the ordered state transition sequence")
    return None


def _load_json(path: Path, field: str):
    if not path.is_file():
        return _issue("missing_evidence", field, f"Required state transition evidence is missing: {path}")
    try:
        value = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return _issue("invalid_evidence", field, f"State transition evidence is invalid JSON: {exc}")
    if not isinstance(value, dict):
        return _issue("invalid_evidence", field, "State transition evidence must be a JSON object")
    return value


def _normalized_lines(source: str) -> list[str]:
    lines = []
    for raw_line in source.splitlines():
        line = raw_line.split("//", 1)[0].strip()
        if line:
            lines.append(" ".join(line.split()))
    return lines


def _required_lines_issue(lines, required, reason: str, field: str):
    missing = next((item for item in required if item not in lines), None)
    if missing is not None:
        return _issue(reason, field, f"State transition source must contain: {missing}")
    return None


def _ordered_issue(lines, expected, reason: str, field: str):
    position = -1
    for item in expected:
        position = _line_index(lines, item, position + 1)
        if position is None:
            return _issue(reason, field, f"State transition path is missing ordered operation: {item}")
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


def _issue(reason: str, field: str, detail: str) -> StateTransitionEvidenceIssue:
    return StateTransitionEvidenceIssue(reason, field, detail)


def _failure(issue: StateTransitionEvidenceIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=RUNTIME_STATE_TRANSITION_CAPABILITY_EVIDENCE_INVALID,
        detail=issue.detail,
        action="Keep state transition contract, source, ELF, QEMU, first capability, runtime return, and halt evidence aligned",
        meta={"reason": issue.reason, "contract_field": issue.contract_field},
    )
