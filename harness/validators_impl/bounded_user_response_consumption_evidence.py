from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness.abi_manifest import ROOT
from harness.codes import BOUNDED_USER_RESPONSE_CONSUMPTION_EVIDENCE_INVALID, OK
from harness.runtime_evidence_taxonomy import get_smoke_marker_order
from harness.validator import BaseValidator, ValidationResult
from harness.validators_impl.bounded_user_response_consumption_contract import _contract_issue

_CONTRACT_PATH = ROOT / "contracts" / "bounded_user_response_consumption_contract.v0.json"
_BOOT_PATH = ROOT / "kernel" / "arch" / "x86_64" / "boot.asm"
_PRIVILEGE_PATH = ROOT / "kernel" / "arch" / "x86_64" / "privilege_transition.asm"
_LAYOUT_PATH = ROOT / "kernel" / "arch" / "x86_64" / "runtime_layout.inc"
_LINKER_PATH = ROOT / "linker" / "kernel.ld"
_ELF_REPORT_PATH = ROOT / "artifacts" / "runtime" / "kernel_elf_report.json"
_METADATA_PATH = ROOT / "artifacts" / "runtime" / "qemu_smoke.metadata.json"
_SERIAL_PATH = ROOT / "artifacts" / "runtime" / "qemu_smoke.log"
_NEW_MARKERS = (
    "KOZO_RING3_RESPONSE_RESUME",
    "KOZO_USER_RESPONSE_CONSUMED_OK",
    "KOZO_FIXED_USER_RESPONSE_OK",
)
_NEW_MARKER_BRIDGES = (
    "runtime_serial_write_ring3_response_resume_marker",
    "runtime_serial_write_user_response_consumed_marker",
    "runtime_serial_write_fixed_user_response_marker",
)
_ELF_SYMBOLS = (
    "user_response_consumer_start",
    "user_response_consumer_interrupt_return",
    "user_response_consumer_end",
    "handle_fixed_user_request",
    "handle_fixed_user_response_consumption",
    "validate_ring3_response_frame",
    "prepare_user_response_resume",
    "resume_fixed_user_response_consumer",
    "validate_user_visible_response",
    "copy_fixed_user_consumption_record",
    "validate_fixed_user_consumption_record",
    "clear_fixed_user_response_transaction",
    "fixed_user_transaction_phase",
    "fixed_user_transaction_phase_end",
    "fixed_user_consumption_shadow",
    "fixed_user_consumption_shadow_end",
    "privilege_ring0_continuation",
)


@dataclass(frozen=True)
class BoundedUserResponseEvidenceIssue:
    reason: str
    contract_field: str
    detail: str


@dataclass(frozen=True)
class BoundedUserResponseEvidenceContext:
    boot: str
    privilege: str
    layout: str
    linker: str
    report: dict[str, object]
    metadata: dict[str, object]
    serial: str


class BoundedUserResponseConsumptionEvidenceValidator(BaseValidator):
    name = "bounded_user_response_consumption_evidence"
    subsystem = "bounded_user_response_consumption_evidence"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _evidence_issue()
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="One fixed Ring3 response consumer and second int 0x81 transaction align across source, ELF, and QEMU",
        )


def _evidence_issue() -> BoundedUserResponseEvidenceIssue | None:
    contract_issue = _contract_issue(_CONTRACT_PATH)
    if contract_issue is not None:
        return _issue(contract_issue.reason, contract_issue.contract_field, contract_issue.detail)
    context = _load_context()
    if isinstance(context, BoundedUserResponseEvidenceIssue):
        return context
    for check in (
        _layout_issue,
        _phase_dispatch_issue,
        _first_handler_issue,
        _resume_issue,
        _ring3_consumer_issue,
        _second_handler_issue,
        _cleanup_continuation_issue,
        _failure_issue,
        _linker_issue,
        _elf_issue,
        _runtime_issue,
    ):
        issue = check(context)
        if issue is not None:
            return issue
    return None


def _load_context():
    sources = {}
    for name, path in {
        "boot": _BOOT_PATH,
        "privilege": _PRIVILEGE_PATH,
        "layout": _LAYOUT_PATH,
        "linker": _LINKER_PATH,
    }.items():
        if not path.is_file():
            return _issue("missing_source", f"source_files.{name}", f"Missing response source: {path}")
        sources[name] = path.read_text()
    report = _load_json(_ELF_REPORT_PATH, "kernel_elf_report")
    if isinstance(report, BoundedUserResponseEvidenceIssue):
        return report
    metadata = _load_json(_METADATA_PATH, "qemu_smoke")
    if isinstance(metadata, BoundedUserResponseEvidenceIssue):
        return metadata
    if not _SERIAL_PATH.is_file():
        return _issue("missing_runtime_evidence", "qemu_smoke.serial_log", "QEMU serial log is missing")
    return BoundedUserResponseEvidenceContext(
        sources["boot"],
        sources["privilege"],
        sources["layout"],
        sources["linker"],
        report,
        metadata,
        _SERIAL_PATH.read_text(errors="replace"),
    )


def _layout_issue(context):
    required = (
        "%define FIXED_USER_CONSUMPTION_RECORD_VA (USER_PROBE_DATA_VA + 0x100)",
        "%define FIXED_USER_CONSUMPTION_RECORD_SIZE 48",
        "%define FIXED_USER_CONSUMPTION_RECORD_VERSION 1",
        "%define FIXED_USER_CONSUMPTION_RECORD_ID 1",
        "%define FIXED_USER_PHASE_REQUEST_PENDING 0",
        "%define FIXED_USER_PHASE_RESPONSE_READY 1",
        "%define FIXED_USER_PHASE_CONSUMED 2",
    )
    return _tokens_issue(context.layout, required, "layout_geometry_invalid", "consumption_record")


def _phase_dispatch_issue(context):
    source = _source_range(context.privilege, "privilege_return_handler:", "handle_fixed_user_request:")
    expected = (
        "cmp dword [rel fixed_user_transaction_phase], FIXED_USER_PHASE_REQUEST_PENDING",
        "je handle_fixed_user_request",
        "cmp dword [rel fixed_user_transaction_phase], FIXED_USER_PHASE_RESPONSE_READY",
        "je handle_fixed_user_response_consumption",
        "mov eax, USER_RESPONSE_PHASE_INVALID",
        "jmp privilege_return_failure",
    )
    return _ordered_issue(source, expected, "phase_dispatch_invalid", "transaction_phases")


def _first_handler_issue(context):
    source = _source_range(
        context.privilege,
        "handle_fixed_user_request:",
        "handle_fixed_user_response_consumption:",
    )
    expected = (
        "call validate_ring3_request_frame",
        "call copy_fixed_user_request_in",
        "call runtime_serial_write_user_runtime_status_service_enter_marker",
        "call build_fixed_user_runtime_status_response",
        "call runtime_serial_write_user_runtime_status_service_ok_marker",
        "call copy_fixed_user_response_out",
        "call validate_fixed_user_response_readback",
        "call runtime_serial_write_user_response_copy_out_marker",
        "call prepare_user_response_resume",
        "call runtime_serial_write_ring3_response_resume_marker",
        "jmp resume_fixed_user_response_consumer",
    )
    return _ordered_issue(source, expected, "first_handler_order_invalid", "execution_point")


def _resume_issue(context):
    source = _source_range(
        context.privilege,
        "resume_fixed_user_response_consumer:",
        "validate_user_visible_response:",
    )
    required = (
        "lea rsp, [rel privilege_return_stack_top]",
        "push qword USER_DATA_SELECTOR",
        "mov rax, USER_INITIAL_RSP",
        "push qword USER_RFLAGS",
        "push qword USER_CODE_SELECTOR",
        "user_response_consumer_start - user_probe_code_start",
        "iretq",
        "ud2",
    )
    return _tokens_issue(source, required, "resume_frame_invalid", "response_consumer")


def _ring3_consumer_issue(context):
    source = _source_range(
        context.privilege,
        "user_response_consumer_start:",
        "user_response_consumer_end:",
    )
    required = (
        "mov ax, cs",
        "cmp eax, 3",
        "mov rax, USER_INITIAL_RSP",
        "push rax",
        "pop rcx",
        "mov rdi, FIXED_USER_RESPONSE_VA",
        "mov rsi, FIXED_USER_CONSUMPTION_RECORD_VA",
        "mov dword [rsi], FIXED_USER_CONSUMPTION_RECORD_VERSION",
        "mov [rsi + 12], r8d",
        "mov qword [rsi + 40], 0",
        "int KOZO_PRIVILEGE_RETURN_VECTOR",
        "user_response_consumer_interrupt_return:",
        "ud2",
    )
    issue = _tokens_issue(source, required, "ring3_consumer_invalid", "ring3_response_checks")
    if issue is not None:
        return issue
    response_comparisons = sum("[rdi" in line and "cmp " in line for line in source.splitlines())
    if response_comparisons < 14:
        return _issue("partial_ring3_response_validation", "ring3_response_checks", "Ring3 must compare every fixed response field")
    status_write = source.find("mov [rsi + 12], r8d")
    final_comparison = source.rfind("cmp qword [rdi + 80], 0")
    if status_write < final_comparison:
        return _issue("success_record_before_validation", "consumption_record", "Record construction must follow every response comparison")
    return None


def _second_handler_issue(context):
    source = _source_range(
        context.privilege,
        "handle_fixed_user_response_consumption:",
        "privilege_response_phase_failure:",
    )
    expected = (
        "call validate_ring3_response_frame",
        "call validate_fixed_user_buffer_ranges",
        "call validate_user_visible_response",
        "call copy_fixed_user_consumption_record",
        "call validate_fixed_user_consumption_record",
        "call runtime_serial_write_user_response_consumed_marker",
        "call clear_fixed_user_response_transaction",
        "mov dword [rel fixed_user_transaction_phase], FIXED_USER_PHASE_CONSUMED",
        "call runtime_serial_write_fixed_user_response_marker",
        "call runtime_serial_write_fixed_user_request_marker",
        "call runtime_serial_write_ring3_probe_marker",
        "jmp privilege_ring0_continuation",
    )
    issue = _ordered_issue(source, expected, "second_handler_order_invalid", "response_revalidation")
    if issue is not None:
        return issue
    copy = _source_range(
        context.privilege,
        "copy_fixed_user_consumption_record:",
        "validate_fixed_user_consumption_record:",
    )
    if _fixed_move_count(copy, 6) is False:
        return _issue("record_copy_invalid", "record_copy.copy_size_bytes", "Consumption copy must move exactly six fixed qwords")
    validation = _source_range(
        context.privilege,
        "validate_fixed_user_consumption_record:",
        "clear_fixed_user_response_transaction:",
    )
    if sum("fixed_user_consumption_shadow" in line and "cmp " in line for line in validation.splitlines()) < 8:
        return _issue("record_validation_invalid", "consumption_record.fields", "Every consumption-record field must be validated")
    return None


def _cleanup_continuation_issue(context):
    clearing = _source_range(
        context.privilege,
        "clear_fixed_user_response_transaction:",
        "clear_fixed_user_request_buffers:",
    )
    required = (
        "FIXED_USER_RESPONSE_VA",
        "FIXED_USER_CONSUMPTION_RECORD_VA",
        "fixed_user_response_shadow",
        "fixed_user_consumption_shadow",
        "fixed_user_response_verify",
        "call fixed_user_buffers_are_zero",
    )
    issue = _tokens_issue(clearing, required, "final_clearing_invalid", "clearing")
    if issue is not None:
        return issue
    continuation = _source_range(
        context.privilege,
        "privilege_ring0_continuation:",
        "privilege_fault_sink:",
    )
    expected = (
        "cmp dword [rel fixed_user_transaction_phase], FIXED_USER_PHASE_CONSUMED",
        "call fixed_user_buffers_are_zero",
        "mov qword [rel fixed_user_transaction_phase], FIXED_USER_PHASE_REQUEST_PENDING",
        "cmp qword [rel fixed_user_transaction_phase], FIXED_USER_PHASE_REQUEST_PENDING",
        "call runtime_serial_write_ring0_return_marker",
        "ret",
    )
    return _ordered_issue(continuation, expected, "phase_reset_invalid", "phase_reset")


def _failure_issue(context):
    failure = _source_range(
        context.privilege,
        "privilege_return_failure:",
        "privilege_ring0_continuation:",
    )
    if any(bridge in failure for bridge in _NEW_MARKER_BRIDGES):
        return _issue("failure_emits_success", "halt_behavior", "Failure path must not emit response success markers")
    if "jnz .halt" not in context.boot:
        return _issue("failure_halt_missing", "halt_behavior.failure_target", "Boot caller must halt after nonzero privilege status")
    prohibited = ("syscall", "sysret", "swapgs", "sti")
    consumer = _source_range(context.privilege, "user_response_consumer_start:", "user_response_consumer_end:")
    if any(token in consumer for token in prohibited):
        return _issue("prohibited_instruction_present", "response_consumer", "Response consumer must not introduce syscall, sysret, swapgs, or sti")
    return None


def _linker_issue(context):
    required = (
        "fixed user consumption shadow must be exactly 48 bytes",
        "fixed user transaction phase must be exactly 8 bytes",
        "fixed user consumption shadow must be 8-byte aligned",
        "fixed user transaction phase must be 8-byte aligned",
        "user response consumer must remain inside the user code page",
    )
    return _tokens_issue(context.linker, required, "linker_geometry_invalid", "kernel_shadow")


def _elf_issue(context):
    record = context.report.get("bounded_user_response_consumption")
    if not isinstance(record, dict):
        return _issue("missing_elf_evidence", "kernel_elf_report.bounded_user_response_consumption", "Kernel ELF report lacks response-consumption evidence")
    symbols = record.get("symbols")
    for symbol in _ELF_SYMBOLS:
        value = symbols.get(symbol) if isinstance(symbols, dict) else None
        if not isinstance(value, dict) or value.get("present") is not True:
            return _issue("missing_elf_symbol", f"kernel_elf_report.bounded_user_response_consumption.symbols.{symbol}", f"Kernel ELF lacks {symbol}")
    if not _valid_range(record.get("transaction_phase"), 8, 8):
        return _issue("elf_geometry_invalid", "kernel_elf_report.bounded_user_response_consumption.transaction_phase", "Phase storage must be 8 aligned bytes")
    if not _valid_range(record.get("consumption_shadow"), 48, 8):
        return _issue("elf_geometry_invalid", "kernel_elf_report.bounded_user_response_consumption.consumption_shadow", "Consumption shadow must be 48 aligned bytes")
    required_true = (
        "consumer_inside_user_page",
        "consumer_second_interrupt_present",
        "resume_iretq_present",
        "initial_interrupt_present",
        "first_handler_resume_call_order_valid",
        "second_handler_call_order_valid",
        "response_clear_zero_validation_present",
        "fixed_continuation_jump_present",
    )
    if any(record.get(field) is not True for field in required_true):
        return _issue("missing_elf_evidence", "kernel_elf_report.bounded_user_response_consumption", "ELF must retain both transitions, handler order, clearing, and continuation")
    minimums = {
        "consumer_response_compare_count": 18,
        "consumer_record_store_count": 8,
        "record_copy_memory_move_count": 12,
        "response_revalidation_compare_count": 1,
        "response_clear_stosq_count": 5,
        "total_iretq_count": 2,
    }
    if any(record.get(field, -1) < value for field, value in minimums.items()):
        return _issue("missing_elf_operation", "kernel_elf_report.bounded_user_response_consumption", "ELF must retain exact comparisons, stores, copies, clears, and two iretq sites")
    if record.get("prohibited_instructions") != []:
        return _issue("prohibited_instruction_present", "kernel_elf_report.bounded_user_response_consumption.prohibited_instructions", "Response boundary must not contain syscall, sysret, swapgs, sti, or wrmsr")
    return None


def _runtime_issue(context):
    expected = list(get_smoke_marker_order())
    if context.metadata.get("outcome") != "pass":
        return _issue("runtime_outcome_invalid", "qemu_smoke.outcome", "QEMU must pass the complete governed marker sequence")
    if context.metadata.get("observed_markers") != expected:
        return _issue("metadata_log_mismatch", "qemu_smoke.observed_markers", "QEMU metadata must agree with the taxonomy")
    position = -1
    for marker in expected:
        position = context.serial.find(marker, position + 1)
        if position < 0:
            return _issue("runtime_marker_missing", f"qemu_smoke.{marker}", f"QEMU serial log is missing {marker}")
        if marker in _NEW_MARKERS and context.serial.count(marker) != 1:
            return _issue("runtime_marker_duplicate", f"qemu_smoke.{marker}", f"QEMU serial log must contain exactly one {marker}")
    return None


def _fixed_move_count(source: str, expected: int) -> bool:
    loads = sum("mov rax, [rsi" in line for line in source.splitlines())
    stores = sum("mov [rdi" in line and "rax" in line for line in source.splitlines())
    return loads == expected + 1 and stores == expected


def _valid_range(value, size: int, alignment: int) -> bool:
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


def _ordered_issue(source: str, tokens: tuple[str, ...], reason: str, field: str):
    lines = tuple(_normalized_lines(source))
    position = -1
    for token in tokens:
        try:
            position = lines.index(token, position + 1)
        except ValueError:
            return _issue(reason, field, f"Missing or misordered source operation: {token}")
    return None


def _tokens_issue(source: str, tokens: tuple[str, ...], reason: str, field: str):
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


def _issue(reason: str, field: str, detail: str) -> BoundedUserResponseEvidenceIssue:
    return BoundedUserResponseEvidenceIssue(reason, field, detail)


def _failure(issue: BoundedUserResponseEvidenceIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=BOUNDED_USER_RESPONSE_CONSUMPTION_EVIDENCE_INVALID,
        detail=issue.detail,
        action="Regenerate bounded response-consumption source, ELF, and QEMU evidence without broadening the transaction",
        meta={"reason": issue.reason, "contract_field": issue.contract_field},
    )
