from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness.abi_manifest import ROOT
from harness.codes import FIXED_USER_REQUEST_BOUNDARY_EVIDENCE_INVALID, OK
from harness.runtime_evidence_taxonomy import get_smoke_marker_order
from harness.runtime_marker_occurrences import marker_occurs_as_governed
from harness.validator import BaseValidator, ValidationResult
from harness.validators_impl.fixed_user_request_boundary_contract import _contract_issue

_CONTRACT_PATH = ROOT / "contracts" / "fixed_user_request_boundary_contract.v0.json"
_BOOT_PATH = ROOT / "kernel" / "arch" / "x86_64" / "boot.asm"
_PRIVILEGE_PATH = ROOT / "kernel" / "arch" / "x86_64" / "privilege_transition.asm"
_LAYOUT_PATH = ROOT / "kernel" / "arch" / "x86_64" / "runtime_layout.inc"
_LINKER_PATH = ROOT / "linker" / "kernel.ld"
_ELF_REPORT_PATH = ROOT / "artifacts" / "runtime" / "kernel_elf_report.json"
_METADATA_PATH = ROOT / "artifacts" / "runtime" / "qemu_smoke.metadata.json"
_SERIAL_PATH = ROOT / "artifacts" / "runtime" / "qemu_smoke.log"

_BOUNDARY_MARKERS = (
    "KOZO_USER_REQUEST_COPY_IN_OK",
    "KOZO_USER_RUNTIME_STATUS_SERVICE_ENTER",
    "KOZO_USER_RUNTIME_STATUS_SERVICE_OK",
    "KOZO_USER_RESPONSE_COPY_OUT_OK",
    "KOZO_FIXED_USER_REQUEST_OK",
)
_ELF_RANGES = {
    "request_shadow": (40, 8),
    "response_shadow": (88, 8),
    "response_verify": (88, 8),
}
_ELF_SYMBOLS = (
    "user_privilege_probe_start",
    "privilege_return_handler",
    "handle_fixed_user_request",
    "handle_fixed_user_response_consumption",
    "validate_ring3_request_frame",
    "validate_fixed_user_buffer_ranges",
    "copy_fixed_user_request_in",
    "validate_fixed_user_request",
    "build_fixed_user_runtime_status_response",
    "validate_fixed_user_response",
    "copy_fixed_user_response_out",
    "validate_fixed_user_response_readback",
    "clear_fixed_user_request_buffers",
    "fixed_user_buffers_are_zero",
    "privilege_ring0_continuation",
    "fixed_user_request_shadow",
    "fixed_user_request_shadow_end",
    "fixed_user_response_shadow",
    "fixed_user_response_shadow_end",
    "fixed_user_response_verify",
    "fixed_user_response_verify_end",
    "fixed_user_request_success_state",
)


@dataclass(frozen=True)
class FixedUserRequestEvidenceIssue:
    reason: str
    contract_field: str
    detail: str


@dataclass(frozen=True)
class FixedUserRequestEvidenceContext:
    boot: str
    privilege: str
    layout: str
    linker: str
    report: dict[str, object]
    metadata: dict[str, object]
    serial: str


class FixedUserRequestBoundaryEvidenceValidator(BaseValidator):
    name = "fixed_user_request_boundary_evidence"
    subsystem = "fixed_user_request_boundary_evidence"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _evidence_issue()
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="One exact Ring3 request and Ring0 response transaction aligns across source, ELF, and QEMU evidence",
        )


def _evidence_issue() -> FixedUserRequestEvidenceIssue | None:
    contract_issue = _contract_issue(_CONTRACT_PATH)
    if contract_issue is not None:
        return _issue(contract_issue.reason, contract_issue.contract_field, contract_issue.detail)
    context = _load_context()
    if isinstance(context, FixedUserRequestEvidenceIssue):
        return context
    for check in _evidence_checks():
        issue = check(context)
        if issue is not None:
            return issue
    return None


def _evidence_checks():
    return (
        _layout_issue,
        _ring3_request_issue,
        _handler_order_issue,
        _range_issue,
        _copy_issue,
        _service_issue,
        _clearing_issue,
        _failure_issue,
        _linker_issue,
        _elf_issue,
        _runtime_issue,
    )


def _load_context():
    sources = _load_sources()
    if isinstance(sources, FixedUserRequestEvidenceIssue):
        return sources
    report = _load_json(_ELF_REPORT_PATH, "kernel_elf_report")
    if isinstance(report, FixedUserRequestEvidenceIssue):
        return report
    metadata = _load_json(_METADATA_PATH, "qemu_smoke")
    if isinstance(metadata, FixedUserRequestEvidenceIssue):
        return metadata
    if not _SERIAL_PATH.is_file():
        return _issue("missing_runtime_evidence", "qemu_smoke.serial_log", "QEMU serial log is missing")
    return FixedUserRequestEvidenceContext(
        sources["boot"],
        sources["privilege"],
        sources["layout"],
        sources["linker"],
        report,
        metadata,
        _SERIAL_PATH.read_text(errors="replace"),
    )


def _load_sources():
    paths = {
        "boot": _BOOT_PATH,
        "privilege": _PRIVILEGE_PATH,
        "layout": _LAYOUT_PATH,
        "linker": _LINKER_PATH,
    }
    for name, path in paths.items():
        if not path.is_file():
            return _issue("missing_source", f"source_files.{name}", f"Missing boundary source: {path}")
    return {name: path.read_text() for name, path in paths.items()}


def _layout_issue(context):
    required = (
        "%define FIXED_USER_REQUEST_VA (USER_PROBE_DATA_VA + 0x000)",
        "%define FIXED_USER_RESPONSE_VA (USER_PROBE_DATA_VA + 0x080)",
        "%define FIXED_USER_REQUEST_SIZE 40",
        "%define FIXED_USER_RESPONSE_SIZE 88",
        "%define FIXED_USER_REQUEST_VERSION 1",
        "%define FIXED_USER_REQUEST_ID 2",
    )
    return _source_tokens_issue(context.layout, required, "layout_geometry_invalid", "request.response")


def _ring3_request_issue(context):
    expected = (
        "mov rdi, FIXED_USER_REQUEST_VA",
        "mov dword [rdi], FIXED_USER_REQUEST_VERSION",
        "mov dword [rdi + 4], FIXED_USER_REQUEST_ID",
        "mov dword [rdi + 8], FIXED_USER_REQUEST_SIZE",
        "mov dword [rdi + 12], FIXED_USER_RESPONSE_SIZE",
        "mov qword [rdi + 16], FIXED_USER_REQUEST_SEQUENCE",
        "mov qword [rdi + 24], 0",
        "mov dword [rdi + 32], FIXED_USER_REQUEST_FLAGS",
        "mov dword [rdi + 36], 0",
        "cmp qword [rdi + 24], 0",
        "int KOZO_PRIVILEGE_RETURN_VECTOR",
    )
    return _ordered_source_issue(context.privilege, expected, "ring3_request_invalid", "request.fields")


def _handler_order_issue(context):
    handler = _source_range(context.privilege, "handle_fixed_user_request:", "handle_fixed_user_response_consumption:")
    expected = (
        "call validate_ring3_request_frame",
        "call validate_fixed_user_buffer_ranges",
        "call copy_fixed_user_request_in",
        "call validate_fixed_user_request",
        "call runtime_serial_write_user_request_copy_in_marker",
        "call runtime_serial_write_user_runtime_status_service_enter_marker",
        "call build_fixed_user_runtime_status_response",
        "call validate_fixed_user_response",
        "call runtime_serial_write_user_runtime_status_service_ok_marker",
        "call copy_fixed_user_response_out",
        "call validate_fixed_user_response_readback",
        "call runtime_serial_write_user_response_copy_out_marker",
        "call prepare_user_response_resume",
        "call runtime_serial_write_ring3_response_resume_marker",
        "jmp resume_fixed_user_response_consumer",
    )
    return _ordered_source_issue(handler, expected, "handler_order_invalid", "copy_boundary")


def _range_issue(context):
    source = _source_range(
        context.privilege,
        "validate_fixed_user_buffer_ranges:",
        "copy_fixed_user_request_in:",
    )
    required = (
        "call validate_fixed_user_span",
        "add rax, FIXED_USER_REQUEST_SIZE",
        "cmp rax, rcx",
        "shl rax, 16",
        "sar rax, 16",
        "call walk_page_mapping",
        "call physical_for_kernel_virtual",
    )
    issue = _source_tokens_issue(source, required, "span_validation_invalid", "copy_boundary")
    if issue is not None:
        return issue
    if source.count("jc .invalid") < 3:
        return _issue("span_validation_invalid", "copy_boundary", "All span-end additions must fail on overflow")
    return None


def _copy_issue(context):
    copy_in = _source_range(context.privilege, "copy_fixed_user_request_in:", "validate_fixed_user_request:")
    copy_out = _source_range(context.privilege, "copy_fixed_user_response_out:", "validate_fixed_user_response_readback:")
    readback = _source_range(context.privilege, "validate_fixed_user_response_readback:", "prepare_user_response_resume:")
    if _fixed_move_count(copy_in, 5) is False:
        return _issue("copy_in_invalid", "copy_boundary.copy_in_size_bytes", "Copy-in must move exactly five fixed qwords")
    if _fixed_move_count(copy_out, 11) is False:
        return _issue("copy_out_invalid", "copy_boundary.copy_out_size_bytes", "Copy-out must move exactly eleven fixed qwords")
    if _fixed_move_count(readback, 11) is False or "call fixed_user_response_fields_are_valid" not in readback:
        return _issue("response_readback_invalid", "copy_boundary.copy_out_readback_required", "Response readback must copy and validate eleven qwords")
    return None


def _service_issue(context):
    request = _source_range(context.privilege, "validate_fixed_user_request:", "runtime_status_snapshot_fields_are_valid:")
    service = _source_range(context.privilege, "runtime_status_snapshot_fields_are_valid:", "validate_fixed_user_response:")
    if sum("fixed_user_request_shadow" in line and "cmp " in line for line in request.splitlines()) < 8:
        return _issue("request_validation_invalid", "request.fields", "Every fixed request field must be validated")
    required = (
        "cmp dword [rel runtime_status_snapshot], RUNTIME_STATUS_STAGE",
        "build_fixed_user_runtime_status_response:",
        "rep stosq",
        "mov [rel fixed_user_response_shadow + 72], rax",
        "mov [rel fixed_user_response_shadow + 80], rax",
    )
    return _source_tokens_issue(service, required, "service_invalid", "fixed_service")


def _clearing_issue(context):
    clearing = _source_range(
        context.privilege,
        "clear_fixed_user_request_buffers:",
        "clear_fixed_user_reused_storage:",
    )
    required = (
        "mov ecx, FIXED_USER_REQUEST_QWORDS",
        "mov ecx, FIXED_USER_RESPONSE_QWORDS",
        "rep stosq",
        "call clear_fixed_user_reused_storage",
        "call fixed_user_session_storage_is_zero",
        "call clear_fixed_user_reused_storage",
        "call fixed_user_session_storage_is_zero",
    )
    issue = _source_tokens_issue(clearing, required, "buffer_clear_invalid", "buffer_clearing")
    if issue is not None:
        return issue
    reused = _source_range(context.privilege, "clear_fixed_user_reused_storage:", "fixed_user_session_storage_is_zero:")
    readback = _source_range(context.privilege, "fixed_user_session_storage_is_zero:", "fixed_user_buffers_are_zero:")
    return _source_tokens_issue(
        reused + readback,
        ("FIXED_USER_DATA_SCRATCH_VA", "USER_PROBE_STACK_VA", "call fixed_user_buffers_are_zero"),
        "buffer_clear_invalid",
        "buffer_clearing",
    )


def _failure_issue(context):
    failure = _source_range(context.privilege, "privilege_return_failure:", "privilege_ring0_continuation:")
    if any(marker.lower() in failure.lower() for marker in _BOUNDARY_MARKERS):
        return _issue("failure_emits_success", "halt_behavior", "Failure path must not emit fixed-request success markers")
    if "jnz .halt" not in context.boot:
        return _issue("failure_halt_missing", "halt_behavior.failure_target", "Boot caller must halt after a nonzero privilege status")
    return None


def _linker_issue(context):
    required = (
        "fixed user request shadow must be exactly 40 bytes",
        "fixed user response shadow must be exactly 88 bytes",
        "fixed user response verify buffer must be exactly 88 bytes",
        "fixed user request shadow must be 8-byte aligned",
        "fixed user response shadow must be 8-byte aligned",
        "fixed user response verify buffer must be 8-byte aligned",
    )
    return _source_tokens_issue(context.linker, required, "linker_geometry_invalid", "kernel_shadows")


def _elf_issue(context):
    record = context.report.get("fixed_user_request_boundary")
    if not isinstance(record, dict):
        return _issue("missing_elf_evidence", "kernel_elf_report.fixed_user_request_boundary", "Kernel ELF report lacks fixed request evidence")
    issue = _elf_symbol_issue(record)
    if issue is not None:
        return issue
    issue = _elf_range_issue(record)
    if issue is not None:
        return issue
    return _elf_behavior_issue(record)


def _elf_symbol_issue(record):
    symbols = record.get("symbols")
    for symbol in _ELF_SYMBOLS:
        value = symbols.get(symbol) if isinstance(symbols, dict) else None
        if not isinstance(value, dict) or value.get("present") is not True:
            field = f"kernel_elf_report.fixed_user_request_boundary.symbols.{symbol}"
            return _issue("missing_elf_symbol", field, f"Kernel ELF lacks {symbol}")
    return None


def _elf_range_issue(record):
    for field, (size, alignment) in _ELF_RANGES.items():
        value = record.get(field)
        if not _valid_elf_range(value, size, alignment):
            path = f"kernel_elf_report.fixed_user_request_boundary.{field}"
            return _issue("elf_geometry_invalid", path, f"{field} must be {size} bytes and {alignment}-byte aligned")
    return None


def _elf_behavior_issue(record):
    required_true = (
        "ring3_return_interrupt_present",
        "handler_call_order_valid",
        "fixed_continuation_jump_present",
    )
    if any(record.get(field) is not True for field in required_true):
        return _issue("missing_elf_evidence", "kernel_elf_report.fixed_user_request_boundary", "ELF must retain the fixed interrupt, handler order, and continuation")
    minimum_counts = {
        "ring3_request_store_count": 8,
        "copy_in_memory_move_count": 10,
        "copy_out_memory_move_count": 22,
        "readback_memory_move_count": 22,
    }
    if any(record.get(field, -1) < count for field, count in minimum_counts.items()):
        return _issue("missing_elf_copy_evidence", "kernel_elf_report.fixed_user_request_boundary", "ELF must retain exact request, copy, and readback operations")
    if record.get("clear_stosq_count", 0) < 5 or record.get("post_clear_zero_validation_present") is not True:
        return _issue("missing_elf_clear_evidence", "kernel_elf_report.fixed_user_request_boundary", "ELF must retain five fixed clears and zero readback validation")
    if record.get("prohibited_boundary_instructions") != []:
        return _issue("prohibited_instruction_present", "kernel_elf_report.fixed_user_request_boundary.prohibited_boundary_instructions", "Boundary must not introduce syscall, sysret, swapgs, sti, or wrmsr")
    return None


def _runtime_issue(context):
    expected = list(get_smoke_marker_order())
    if context.metadata.get("outcome") != "pass":
        return _issue("runtime_outcome_invalid", "qemu_smoke.outcome", "QEMU must pass the complete governed marker sequence")
    if context.metadata.get("observed_markers") != expected:
        return _issue("metadata_log_mismatch", "qemu_smoke.observed_markers", "QEMU metadata must agree with the taxonomy")
    return _serial_marker_issue(context.serial, expected)


def _serial_marker_issue(serial: str, expected: list[str]):
    position = -1
    for marker in expected:
        position = serial.find(marker, position + 1)
        if position < 0:
            return _issue("runtime_marker_missing", f"qemu_smoke.{marker}", f"QEMU serial log is missing {marker}")
        if marker in _BOUNDARY_MARKERS and not marker_occurs_as_governed(serial, marker, expected):
            return _issue("runtime_marker_duplicate", f"qemu_smoke.{marker}", f"QEMU serial marker count must match the governed occurrence count for {marker}")
    return None


def _fixed_move_count(source: str, expected: int) -> bool:
    loads = sum("mov rax, [rsi" in line for line in source.splitlines())
    stores = sum("mov [rdi" in line and "rax" in line for line in source.splitlines())
    return loads == expected + 1 and stores == expected


def _valid_elf_range(value, size: int, alignment: int) -> bool:
    return (
        isinstance(value, dict)
        and value.get("size_bytes") == size
        and value.get("required_alignment_bytes") == alignment
        and value.get("start_aligned") is True
    )


def _load_json(path: Path, field: str):
    if not path.is_file():
        return _issue("missing_evidence", field, f"Missing evidence: {path}")
    try:
        value = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return _issue("invalid_evidence_json", field, f"Invalid evidence JSON: {exc}")
    if not isinstance(value, dict):
        return _issue("invalid_evidence_json", field, "Evidence must be a JSON object")
    return value


def _ordered_source_issue(source: str, tokens: tuple[str, ...], reason: str, field: str):
    lines = tuple(_normalized_lines(source))
    position = -1
    for token in tokens:
        try:
            position = lines.index(token, position + 1)
        except ValueError:
            return _issue(reason, field, f"Missing or misordered source operation: {token}")
    return None


def _source_tokens_issue(source: str, tokens: tuple[str, ...], reason: str, field: str):
    for token in tokens:
        if token not in source:
            return _issue(reason, field, f"Missing source operation: {token}")
    return None


def _source_range(source: str, start: str, end: str | None) -> str:
    start_index = source.find(start)
    if start_index < 0:
        return ""
    end_index = source.find(end, start_index + len(start)) if end is not None else len(source)
    return source[start_index:end_index if end_index >= 0 else len(source)]


def _normalized_lines(source: str):
    for line in source.splitlines():
        normalized = line.split(";", 1)[0].strip()
        if normalized:
            yield normalized


def _issue(reason: str, field: str, detail: str) -> FixedUserRequestEvidenceIssue:
    return FixedUserRequestEvidenceIssue(reason, field, detail)


def _failure(issue: FixedUserRequestEvidenceIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=FIXED_USER_REQUEST_BOUNDARY_EVIDENCE_INVALID,
        detail=issue.detail,
        action="Regenerate fixed request source, ELF, and QEMU evidence without broadening the boundary",
        meta={"reason": issue.reason, "contract_field": issue.contract_field},
    )
