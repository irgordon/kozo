from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness import first_governed_runtime_capability as contract_module
from harness.abi_manifest import ROOT
from harness.codes import FIRST_GOVERNED_RUNTIME_CAPABILITY_EVIDENCE_INVALID, OK
from harness.runtime_evidence_taxonomy import get_expected_smoke_marker, get_smoke_marker_order
from harness.validator import BaseValidator, ValidationResult

_CONTRACT_PATH = contract_module.CONTRACT_PATH
_CAPABILITY_SOURCE_PATH = ROOT / "kernel" / "runtime_capability.odin"
_PROGRESSION_SOURCE_PATH = ROOT / "kernel" / "runtime_progression.odin"
_BOOT_SOURCE_PATH = ROOT / "kernel" / "arch" / "x86_64" / "boot.asm"
_ELF_REPORT_PATH = ROOT / "artifacts" / "runtime" / "kernel_elf_report.json"
_STAGES_PATH = ROOT / "contracts" / "runtime_progression_stages.v0.json"
_METADATA_PATH = ROOT / "artifacts" / "runtime" / "qemu_smoke.metadata.json"
_SERIAL_LOG_PATH = ROOT / "artifacts" / "runtime" / "qemu_smoke.log"
_TOOLING_BLOCKERS = {
    "missing_iso_generation_tooling",
    "missing_qemu_tooling",
    "missing_boot_image",
    "qemu_launch_failed",
}
_REQUIRED_SYMBOLS = (
    "execute_first_governed_capability",
    "dispatch_runtime_capability",
    "query_runtime_status",
    "runtime_serial_write_capability_dispatch_marker",
    "runtime_serial_write_status_query_marker",
    "runtime_serial_write_first_capability_marker",
)


@dataclass(frozen=True)
class FirstCapabilityEvidenceIssue:
    reason: str
    contract_field: str
    detail: str


@dataclass(frozen=True)
class FirstCapabilityContext:
    capability_lines: tuple[str, ...]
    progression_lines: tuple[str, ...]
    boot_lines: tuple[str, ...]


class FirstGovernedRuntimeCapabilityEvidenceValidator(BaseValidator):
    name = "first_governed_runtime_capability_evidence"
    subsystem = "first_governed_runtime_capability_evidence"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _evidence_issue()
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="First governed runtime capability aligns request validation, dispatch, response proof, markers, ELF symbols, stages, and halt",
        )


def _evidence_issue() -> FirstCapabilityEvidenceIssue | None:
    context = _load_context()
    if isinstance(context, FirstCapabilityEvidenceIssue):
        return context
    checks = (
        lambda: _progression_issue(context),
        lambda: _layout_issue(context),
        lambda: _request_issue(context),
        lambda: _dispatcher_issue(context),
        lambda: _handler_issue(context),
        lambda: _response_issue(context),
        lambda: _response_validation_issue(context),
        lambda: _success_marker_issue(context),
        lambda: _marker_bridge_issue(context),
        _binary_issue,
        _stage_issue,
        _qemu_issue,
    )
    for check in checks:
        issue = check()
        if issue is not None:
            return issue
    return None


def _load_context() -> FirstCapabilityContext | FirstCapabilityEvidenceIssue:
    contract_issue = _contract_issue()
    if contract_issue is not None:
        return contract_issue
    sources = (
        (_CAPABILITY_SOURCE_PATH, "capability.source_file"),
        (_PROGRESSION_SOURCE_PATH, "runtime_progression.source_file"),
        (_BOOT_SOURCE_PATH, "terminal_behavior.halt_contract"),
    )
    loaded = [_load_source(path, field) for path, field in sources]
    issue = next((value for value in loaded if isinstance(value, FirstCapabilityEvidenceIssue)), None)
    if issue is not None:
        return issue
    return FirstCapabilityContext(*(tuple(_normalized_lines(value)) for value in loaded))


def _contract_issue() -> FirstCapabilityEvidenceIssue | None:
    try:
        contract_module.load_first_governed_runtime_capability(_CONTRACT_PATH)
    except json.JSONDecodeError as exc:
        return _issue("invalid_contract_json", "contract", f"First capability contract is invalid JSON: {exc}")
    except (OSError, KeyError, TypeError, ValueError) as exc:
        return _issue("contract_schema_violation", "contract", f"First capability contract is unavailable or malformed: {exc}")
    return None


def _load_source(path: Path, field: str) -> str | FirstCapabilityEvidenceIssue:
    if path.is_file():
        return path.read_text()
    return _issue("missing_source", field, f"First capability source is missing: {path}")


def _progression_issue(context: FirstCapabilityContext) -> FirstCapabilityEvidenceIssue | None:
    expected = (
        "loop_status := controlled_runtime_loop()",
        "if loop_status != RUNTIME_PROGRESSION_OK {",
        "return loop_status",
        "return execute_first_governed_capability()",
    )
    return _ordered_issue(context.progression_lines, expected, "capability_path_missing", "execution_order")


def _layout_issue(context: FirstCapabilityContext) -> FirstCapabilityEvidenceIssue | None:
    expected = (
        "Runtime_Status_Request :: struct {",
        "version: u32,",
        "capability_id: u32,",
        "flags: u32,",
        "reserved: u32,",
        "Runtime_Status_Response :: struct {",
        "current_progression_stage: u32,",
        "proven_stage_mask: u64,",
        "controlled_loop_accumulator: u64,",
        "reserved: u64,",
        "#assert(size_of(Runtime_Status_Request) == RUNTIME_STATUS_REQUEST_SIZE)",
        "#assert(align_of(Runtime_Status_Request) == RUNTIME_STATUS_REQUEST_ALIGNMENT)",
        "#assert(size_of(Runtime_Status_Response) == RUNTIME_STATUS_RESPONSE_SIZE)",
        "#assert(align_of(Runtime_Status_Response) == RUNTIME_STATUS_RESPONSE_ALIGNMENT)",
    )
    return _ordered_issue(
        context.capability_lines,
        expected,
        "source_layout_mismatch",
        "request_response_layout",
    )


def _request_issue(context: FirstCapabilityContext) -> FirstCapabilityEvidenceIssue | None:
    required = (
        "if request == nil || uintptr(request) % RUNTIME_STATUS_REQUEST_ALIGNMENT != 0 {",
        "return RUNTIME_CAPABILITY_INVALID_REQUEST_POINTER",
        "if !runtime_status_response_pointer_is_valid(request, response) {",
        "return RUNTIME_CAPABILITY_INVALID_RESPONSE_POINTER",
        "if request.version != RUNTIME_STATUS_REQUEST_VERSION {",
        "return RUNTIME_CAPABILITY_UNSUPPORTED_REQUEST_VERSION",
        "if request.capability_id != RUNTIME_STATUS_QUERY_CAPABILITY_ID {",
        "return RUNTIME_CAPABILITY_UNSUPPORTED_CAPABILITY",
        "if request.flags != RUNTIME_STATUS_SUPPORTED_FLAGS {",
        "return RUNTIME_CAPABILITY_UNSUPPORTED_FLAGS",
        "if request.reserved != 0 {",
        "return RUNTIME_CAPABILITY_INVALID_RESERVED_FIELD",
    )
    return _required_lines_issue(context.capability_lines, required, "request_validation_missing", "request")


def _dispatcher_issue(context: FirstCapabilityContext) -> FirstCapabilityEvidenceIssue | None:
    expected = (
        "validation_status := validate_runtime_status_request(request, response)",
        "if validation_status != RUNTIME_PROGRESSION_OK {",
        "return validation_status",
        "clear_runtime_status_response(response)",
        "runtime_serial_write_capability_dispatch_marker()",
        "switch request.capability_id {",
        "case RUNTIME_STATUS_QUERY_CAPABILITY_ID:",
        "return query_runtime_status(response)",
        "case:",
        "return RUNTIME_CAPABILITY_UNSUPPORTED_CAPABILITY",
    )
    return _ordered_issue(context.capability_lines, expected, "dispatcher_sequence_mismatch", "execution_order")


def _handler_issue(context: FirstCapabilityContext) -> FirstCapabilityEvidenceIssue | None:
    expected = (
        "if !controlled_runtime_loop_state_is_complete() {",
        "return RUNTIME_CAPABILITY_EXECUTION_FAILURE",
        "populate_runtime_status_response(response)",
        "if !validate_runtime_status_response(response) {",
        "return RUNTIME_CAPABILITY_RESPONSE_VALIDATION_FAILURE",
        "runtime_serial_write_status_query_marker()",
        "return RUNTIME_PROGRESSION_OK",
    )
    return _ordered_issue(context.capability_lines, expected, "handler_sequence_mismatch", "execution_order")


def _response_issue(context: FirstCapabilityContext) -> FirstCapabilityEvidenceIssue | None:
    required = (
        "response.version = RUNTIME_STATUS_RESPONSE_VERSION",
        "response.capability_id = RUNTIME_STATUS_QUERY_CAPABILITY_ID",
        "response.status = RUNTIME_PROGRESSION_OK",
        "response.current_progression_stage = RUNTIME_STAGE_CONTROLLED_RUNTIME_LOOP",
        "response.proven_stage_mask = RUNTIME_PROVEN_STAGE_MASK",
        "response.boot_memory_region_size = RUNTIME_BOOT_MEMORY_SIZE",
        "response.controlled_loop_iteration_limit = runtime_loop_limit()",
        "response.controlled_loop_final_count = runtime_loop_iteration_count()",
        "response.controlled_loop_accumulator = runtime_loop_accumulator()",
        "response.reserved = 0",
    )
    return _required_lines_issue(context.capability_lines, required, "response_population_missing", "response.fields")


def _response_validation_issue(context: FirstCapabilityContext) -> FirstCapabilityEvidenceIssue | None:
    required = (
        "return response.version == RUNTIME_STATUS_RESPONSE_VERSION &&",
        "response.capability_id == RUNTIME_STATUS_QUERY_CAPABILITY_ID &&",
        "response.status == RUNTIME_PROGRESSION_OK &&",
        "response.current_progression_stage == RUNTIME_STAGE_CONTROLLED_RUNTIME_LOOP &&",
        "response.proven_stage_mask == RUNTIME_PROVEN_STAGE_MASK &&",
        "response.boot_memory_region_size == RUNTIME_BOOT_MEMORY_SIZE &&",
        "response.controlled_loop_iteration_limit == RUNTIME_LOOP_ITERATION_LIMIT &&",
        "response.controlled_loop_final_count == RUNTIME_LOOP_ITERATION_LIMIT &&",
        "response.controlled_loop_accumulator == RUNTIME_LOOP_EXPECTED_ACCUMULATOR &&",
        "response.reserved == 0",
    )
    return _required_lines_issue(
        context.capability_lines,
        required,
        "response_validation_missing",
        "response.validation",
    )


def _success_marker_issue(context: FirstCapabilityContext) -> FirstCapabilityEvidenceIssue | None:
    expected = (
        "status := dispatch_runtime_capability(&request, &response)",
        "if status != RUNTIME_PROGRESSION_OK {",
        "return status",
        "if !validate_runtime_status_response(&response) {",
        "return RUNTIME_CAPABILITY_RESPONSE_VALIDATION_FAILURE",
        "runtime_serial_write_first_capability_marker()",
        "return RUNTIME_PROGRESSION_OK",
    )
    issue = _ordered_issue(context.capability_lines, expected, "success_marker_before_validation", "markers")
    if issue is not None:
        return issue
    return _unique_markers_issue(context.capability_lines)


def _unique_markers_issue(lines: tuple[str, ...]) -> FirstCapabilityEvidenceIssue | None:
    markers = (
        "runtime_serial_write_capability_dispatch_marker()",
        "runtime_serial_write_status_query_marker()",
        "runtime_serial_write_first_capability_marker()",
    )
    if any(lines.count(marker) != 1 for marker in markers):
        return _issue("success_marker_duplicated", "markers.emission_owner", "Each capability success marker must have one Odin call site")
    return None


def _marker_bridge_issue(context: FirstCapabilityContext) -> FirstCapabilityEvidenceIssue | None:
    pairs = (
        ("runtime_serial_write_capability_dispatch_marker", "capability_dispatch_marker"),
        ("runtime_serial_write_status_query_marker", "runtime_status_query_marker"),
        ("runtime_serial_write_first_capability_marker", "first_capability_marker"),
    )
    for bridge, marker in pairs:
        expected = (f"{bridge}:", f"WRITE_COM1_MARKER {marker}, {marker}_end", "ret")
        issue = _ordered_issue(context.boot_lines, expected, "marker_bridge_missing", f"markers.{bridge}")
        if issue is not None:
            return issue
    return None


def _binary_issue() -> FirstCapabilityEvidenceIssue | None:
    report = _load_json(_ELF_REPORT_PATH, "kernel_elf_report")
    if isinstance(report, FirstCapabilityEvidenceIssue):
        return report
    record = report.get("first_governed_runtime_capability")
    if not isinstance(record, dict):
        return _issue("binary_capability_missing", "kernel_elf_report.first_governed_runtime_capability", "Kernel ELF report must record first capability evidence")
    symbols = record.get("symbols")
    if not isinstance(symbols, dict):
        return _issue("binary_symbol_missing", "kernel_elf_report.first_governed_runtime_capability.symbols", "Kernel ELF report must record first capability symbols")
    for symbol in _REQUIRED_SYMBOLS:
        value = symbols.get(symbol)
        if not isinstance(value, dict) or value.get("present") is not True or not value.get("address"):
            return _issue("binary_symbol_missing", f"kernel_elf_report.first_governed_runtime_capability.symbols.{symbol}", f"Kernel ELF is missing first capability symbol: {symbol}")
    if record.get("progression_call_present") is not True:
        return _issue("binary_call_missing", "kernel_elf_report.first_governed_runtime_capability.progression_call_present", "Runtime progression must call the first capability path")
    return None


def _stage_issue() -> FirstCapabilityEvidenceIssue | None:
    document = _load_json(_STAGES_PATH, "runtime_progression_stages")
    if isinstance(document, FirstCapabilityEvidenceIssue):
        return document
    statuses = {
        stage.get("stage_name"): stage.get("status")
        for stage in document.get("stages", [])
        if isinstance(stage, dict)
    }
    expected = {
        "CONTROLLED_RUNTIME_LOOP": "proven",
        "FIRST_GOVERNED_RUNTIME_CAPABILITY": "implemented_pending_ci",
        "USERSPACE_PLANNING": "planned",
    }
    for stage, status in expected.items():
        if statuses.get(stage) != status:
            return _issue("stage_status_mismatch", f"runtime_progression_stages.{stage}.status", f"Expected {stage} status {status}")
    return None


def _qemu_issue() -> FirstCapabilityEvidenceIssue | None:
    metadata = _load_json(_METADATA_PATH, "qemu_smoke.metadata")
    if isinstance(metadata, FirstCapabilityEvidenceIssue):
        return metadata
    if metadata.get("outcome") == "blocked" and metadata.get("blocker_category") in _TOOLING_BLOCKERS:
        return None
    if metadata.get("outcome") != "pass":
        return _issue("capability_evidence_missing", "qemu_smoke.outcome", "First capability requires passing QEMU evidence or an allowed local tooling blocker")
    return _passing_qemu_issue(metadata)


def _passing_qemu_issue(metadata: dict[str, object]) -> FirstCapabilityEvidenceIssue | None:
    markers = get_smoke_marker_order()
    if metadata.get("expected_marker") != get_expected_smoke_marker():
        return _issue("metadata_log_mismatch", "qemu_smoke.expected_marker", "QEMU expected marker must match runtime taxonomy")
    if metadata.get("observed_markers") != list(markers):
        return _issue("metadata_log_mismatch", "qemu_smoke.observed_markers", "QEMU metadata must contain the complete first capability sequence")
    if not _SERIAL_LOG_PATH.is_file() or not _ordered_markers_present(_SERIAL_LOG_PATH.read_text(errors="replace"), markers):
        return _issue("metadata_log_mismatch", "qemu_smoke.serial_log", "QEMU serial log must contain the ordered first capability sequence")
    return None


def _load_json(path: Path, field: str):
    if not path.is_file():
        return _issue("missing_evidence", field, f"Required first capability evidence is missing: {path}")
    try:
        value = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return _issue("invalid_evidence", field, f"First capability evidence is invalid JSON: {exc}")
    if not isinstance(value, dict):
        return _issue("invalid_evidence", field, "First capability evidence must be a JSON object")
    return value


def _normalized_lines(source: str) -> list[str]:
    lines = []
    for raw_line in source.splitlines():
        line = raw_line.split(";", 1)[0].strip()
        if line:
            lines.append(" ".join(line.split()))
    return lines


def _required_lines_issue(lines, required, reason: str, field: str):
    missing = next((item for item in required if item not in lines), None)
    if missing is not None:
        return _issue(reason, field, f"First capability source must contain: {missing}")
    return None


def _ordered_issue(lines, expected, reason: str, field: str):
    position = -1
    for item in expected:
        position = _line_index(lines, item, position + 1)
        if position is None:
            return _issue(reason, field, f"First capability path is missing ordered operation: {item}")
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


def _issue(reason: str, field: str, detail: str) -> FirstCapabilityEvidenceIssue:
    return FirstCapabilityEvidenceIssue(reason, field, detail)


def _failure(issue: FirstCapabilityEvidenceIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=FIRST_GOVERNED_RUNTIME_CAPABILITY_EVIDENCE_INVALID,
        detail=issue.detail,
        action="Keep first capability contract, source, ELF, QEMU evidence, stages, and halt continuation aligned",
        meta={"reason": issue.reason, "contract_field": issue.contract_field},
    )
