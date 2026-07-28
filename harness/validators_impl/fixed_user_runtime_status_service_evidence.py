from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness.abi_manifest import ROOT
from harness.codes import FIXED_USER_RUNTIME_STATUS_SERVICE_EVIDENCE_INVALID, OK
from harness.runtime_evidence_taxonomy import get_smoke_marker_order
from harness.validator import BaseValidator, ValidationResult
from harness.validators_impl.fixed_user_runtime_status_service_contract import _contract_issue

_CONTRACT_PATH = ROOT / "contracts" / "fixed_user_runtime_status_service_contract.v0.json"
_BOOT_PATH = ROOT / "kernel" / "arch" / "x86_64" / "boot.asm"
_PRIVILEGE_PATH = ROOT / "kernel" / "arch" / "x86_64" / "privilege_transition.asm"
_LAYOUT_PATH = ROOT / "kernel" / "arch" / "x86_64" / "runtime_layout.inc"
_RUNTIME_PATH = ROOT / "kernel" / "runtime_progression.odin"
_CAPABILITY_PATH = ROOT / "kernel" / "runtime_capability.odin"
_ELF_REPORT_PATH = ROOT / "artifacts" / "runtime" / "kernel_elf_report.json"
_METADATA_PATH = ROOT / "artifacts" / "runtime" / "qemu_smoke.metadata.json"
_SERIAL_PATH = ROOT / "artifacts" / "runtime" / "qemu_smoke.log"
_RUNTIME_MARKERS = (
    "KOZO_RUNTIME_LOOP_EXIT_OK",
    "KOZO_RING3_ENTER",
    "KOZO_USER_REQUEST_COPY_IN_OK",
    "KOZO_USER_RUNTIME_STATUS_SERVICE_ENTER",
    "KOZO_USER_RUNTIME_STATUS_SERVICE_OK",
    "KOZO_USER_RESPONSE_COPY_OUT_OK",
    "KOZO_RING3_RESPONSE_RESUME",
    "KOZO_USER_RESPONSE_CONSUMED_OK",
    "KOZO_FIXED_USER_RESPONSE_OK",
    "KOZO_FIXED_USER_REQUEST_OK",
    "KOZO_RING3_PROBE_OK",
    "KOZO_RING0_RETURN_OK",
    "KOZO_CAPABILITY_DISPATCH_ENTER",
    "KOZO_RUNTIME_STATUS_QUERY_OK",
    "KOZO_FIRST_CAPABILITY_OK",
)
_ELF_SYMBOLS = (
    "runtime_progression_entry",
    "execute_runtime_status_boundaries",
    "collect_runtime_status",
    "validate_runtime_status_snapshot",
    "clear_runtime_status_snapshot",
    "build_internal_runtime_status_response",
    "execute_fixed_user_runtime_status_transaction",
    "enter_bounded_ring3_probe",
    "runtime_status_snapshot",
    "runtime_status_snapshot_fields_are_valid",
    "build_fixed_user_runtime_status_response",
    "fixed_user_response_fields_are_valid",
    "fixed_user_response_digest",
)


@dataclass(frozen=True)
class RuntimeStatusEvidenceIssue:
    reason: str
    contract_field: str
    detail: str


@dataclass(frozen=True)
class RuntimeStatusEvidenceContext:
    boot: str
    privilege: str
    layout: str
    runtime: str
    capability: str
    report: dict[str, object]
    metadata: dict[str, object]
    serial: str


class FixedUserRuntimeStatusServiceEvidenceValidator(BaseValidator):
    name = "fixed_user_runtime_status_service_evidence"
    subsystem = "fixed_user_runtime_status_service_evidence"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _evidence_issue()
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Post-loop user status transaction, shared snapshot, internal capability, and QEMU evidence agree",
        )


def _evidence_issue() -> RuntimeStatusEvidenceIssue | None:
    contract_issue = _contract_issue(_CONTRACT_PATH)
    if contract_issue is not None:
        return _issue(contract_issue.reason, contract_issue.contract_field, contract_issue.detail)
    context = _load_context()
    if isinstance(context, RuntimeStatusEvidenceIssue):
        return context
    for check in (
        _boot_boundary_issue,
        _runtime_order_issue,
        _shared_status_issue,
        _bridge_issue,
        _response_issue,
        _failure_issue,
        _elf_issue,
        _runtime_evidence_issue,
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
        "runtime": _RUNTIME_PATH,
        "capability": _CAPABILITY_PATH,
    }.items():
        if not path.is_file():
            return _issue("missing_source", f"source_files.{name}", f"Missing runtime status source: {path}")
        sources[name] = path.read_text()
    report = _load_json(_ELF_REPORT_PATH, "kernel_elf_report")
    if isinstance(report, RuntimeStatusEvidenceIssue):
        return report
    metadata = _load_json(_METADATA_PATH, "qemu_smoke")
    if isinstance(metadata, RuntimeStatusEvidenceIssue):
        return metadata
    if not _SERIAL_PATH.is_file():
        return _issue("missing_runtime_evidence", "qemu_smoke.serial_log", "QEMU serial log is missing")
    return RuntimeStatusEvidenceContext(
        sources["boot"],
        sources["privilege"],
        sources["layout"],
        sources["runtime"],
        sources["capability"],
        report,
        metadata,
        _SERIAL_PATH.read_text(errors="replace"),
    )


def _boot_boundary_issue(context):
    start = _source_range(context.boot, "_start:", "initialize_cpu_extended_state:")
    forbidden = (
        "call enter_bounded_ring3_probe",
        "call execute_fixed_user_runtime_status_transaction",
    )
    if any(token in start for token in forbidden):
        return _issue("boot_executes_transaction", "runtime_ordering.boot_executes_transaction", "Boot must prepare privilege state without entering Ring3")
    required = (
        "call initialize_privilege_transition",
        "call runtime_progression_entry",
    )
    return _ordered_issue(start, required, "boot_preparation_invalid", "runtime_ordering")


def _runtime_order_issue(context):
    entry = _source_range(context.runtime, "runtime_progression_entry ::", "execute_runtime_status_boundaries ::")
    issue = _ordered_issue(
        entry,
        (
            "controlled_runtime_loop()",
            "execute_runtime_status_boundaries()",
            "execute_second_governed_capability()",
        ),
        "runtime_order_invalid",
        "runtime_ordering",
    )
    if issue is not None:
        return issue
    boundaries = _source_range(
        context.runtime,
        "execute_runtime_status_boundaries ::",
        "controlled_runtime_loop ::",
    )
    return _ordered_issue(
        boundaries,
        (
            "collect_runtime_status()",
            "execute_fixed_user_runtime_status_transaction()",
            "execute_first_governed_capability()",
            "clear_runtime_status_snapshot()",
        ),
        "runtime_order_invalid",
        "runtime_ordering",
    )


def _shared_status_issue(context):
    required = (
        "Runtime_Status_Snapshot :: struct",
        "runtime_status_snapshot: Runtime_Status_Snapshot",
        "collect_runtime_status ::",
        "validate_runtime_status_snapshot ::",
        "clear_runtime_status_snapshot ::",
        "build_internal_runtime_status_response ::",
    )
    issue = _tokens_issue(context.capability, required, "shared_status_missing", "shared_status")
    if issue is not None:
        return issue
    collector = _source_range(
        context.capability,
        "collect_runtime_status ::",
        "populate_runtime_status_snapshot ::",
    )
    if "controlled_runtime_loop_state_is_complete()" not in collector:
        return _issue("pre_runtime_status_substitute", "shared_status.collector_symbol", "Status collection must validate real completed loop state")
    internal = _source_range(
        context.capability,
        "query_runtime_status ::",
        "collect_runtime_status ::",
    )
    if "validate_runtime_status_snapshot()" not in internal or "build_internal_runtime_status_response" not in internal:
        return _issue("internal_status_source_diverged", "shared_status.internal_response_builder", "Capability ID 1 must use the shared snapshot")
    return None


def _bridge_issue(context):
    bridge = _source_range(
        context.privilege,
        "execute_fixed_user_runtime_status_transaction:",
        "privilege_return_handler:",
    )
    issue = _ordered_issue(
        bridge,
        (
            "sub rsp, 8",
            "call enter_bounded_ring3_probe",
            "add rsp, 8",
            "ret",
            "mov [rel saved_odin_return_stack], rsp",
            "call runtime_status_snapshot_fields_are_valid",
            "call runtime_serial_write_ring3_enter_marker",
            "iretq",
        ),
        "bridge_order_invalid",
        "runtime_ordering.runtime_bridge_symbol",
    )
    if issue is not None:
        return issue
    continuation = _source_range(
        context.privilege,
        "privilege_ring0_continuation:",
        "privilege_fault_sink:",
    )
    required = (
        "cmp rsp, [rel saved_odin_return_stack]",
        "call fixed_user_buffers_are_zero",
        "mov qword [rel fixed_user_transaction_phase], FIXED_USER_PHASE_REQUEST_PENDING",
        "call runtime_serial_write_ring0_return_marker",
        "ret",
    )
    return _ordered_issue(continuation, required, "odin_return_invalid", "runtime_ordering.return_target")


def _response_issue(context):
    layout_tokens = (
        "%define FIXED_USER_REQUEST_ID 2",
        "%define FIXED_USER_RESPONSE_SIZE 88",
        "%define RUNTIME_STATUS_SNAPSHOT_SIZE 64",
        "%define RUNTIME_STATUS_FEATURE_MASK 0x7f",
    )
    issue = _tokens_issue(context.layout, layout_tokens, "response_geometry_invalid", "response")
    if issue is not None:
        return issue
    handler = _source_range(
        context.privilege,
        "handle_fixed_user_request:",
        "handle_fixed_user_response_consumption:",
    )
    issue = _ordered_issue(
        handler,
        (
            "call validate_fixed_user_request",
            "call runtime_serial_write_user_request_copy_in_marker",
            "call runtime_serial_write_user_runtime_status_service_enter_marker",
            "call build_fixed_user_runtime_status_response",
            "call validate_fixed_user_response",
            "call runtime_serial_write_user_runtime_status_service_ok_marker",
            "call copy_fixed_user_response_out",
        ),
        "service_order_invalid",
        "marker_order",
    )
    if issue is not None:
        return issue
    consumer = _source_range(
        context.privilege,
        "user_response_consumer_start:",
        "user_response_consumer_end:",
    )
    comparisons = sum("cmp " in line and "[rdi" in line for line in consumer.splitlines())
    if comparisons < 14:
        return _issue("partial_ring3_validation", "ring3_validation", "Ring3 must compare all fourteen fixed response fields")
    if "xor rax, [rdi + 80]" not in consumer:
        return _issue("response_digest_invalid", "ring3_validation.digest_operation", "Ring3 must digest all eleven response qwords")
    return None


def _failure_issue(context):
    boundaries = _source_range(
        context.runtime,
        "execute_runtime_status_boundaries ::",
        "controlled_runtime_loop ::",
    )
    failure_guard = boundaries.find("if transaction_status !=")
    capability_call = boundaries.find("execute_first_governed_capability()")
    if failure_guard < 0 or capability_call < 0 or failure_guard > capability_call:
        return _issue("capability_after_failed_transaction", "failure_behavior", "A failed user transaction must return before capability dispatch")
    failure = _source_range(
        context.privilege,
        "privilege_return_failure:",
        "privilege_ring0_continuation:",
    )
    if "runtime_serial_write_user_runtime_status_service_ok_marker" in failure:
        return _issue("failure_emits_success", "failure_behavior", "Failure paths must not emit service success")
    return None


def _elf_issue(context):
    evidence = context.report.get("fixed_user_runtime_status_service")
    if not isinstance(evidence, dict):
        return _issue("missing_elf_evidence", "kernel_elf_report.fixed_user_runtime_status_service", "ELF runtime status evidence is missing")
    symbols = evidence.get("symbols", {})
    if not isinstance(symbols, dict):
        return _issue("missing_elf_symbol", "kernel_elf_report.symbols", "ELF status symbols are missing")
    for symbol in _ELF_SYMBOLS:
        if not symbols.get(symbol, {}).get("present"):
            return _issue("missing_elf_symbol", f"kernel_elf_report.symbols.{symbol}", f"ELF symbol is missing: {symbol}")
    snapshot = evidence.get("snapshot", {})
    if snapshot.get("size_bytes") != 64 or snapshot.get("aligned") is not True:
        return _issue("snapshot_elf_geometry_invalid", "kernel_elf_report.snapshot", "ELF snapshot must be 64 bytes and 8-byte aligned")
    required_true = (
        "runtime_entry_calls_status_boundaries",
        "status_boundary_call_order_valid",
        "bridge_calls_fixed_ring3_entry",
        "request_handler_service_order_valid",
    )
    for field in required_true:
        if evidence.get(field) is not True:
            return _issue("elf_call_order_invalid", f"kernel_elf_report.{field}", f"ELF evidence must prove {field}")
    if evidence.get("boot_calls_transaction") is not False:
        return _issue("boot_executes_transaction", "kernel_elf_report.boot_calls_transaction", "ELF must prove boot does not enter the fixed transaction")
    if evidence.get("response_builder_store_count", 0) < 11:
        return _issue("elf_response_stores_missing", "kernel_elf_report.response_builder_store_count", "ELF must retain the complete response stores")
    consumer_issue = _ring3_consumer_elf_issue(evidence)
    if consumer_issue is not None:
        return consumer_issue
    if evidence.get("digest_xor_count", 0) < 10:
        return _issue("elf_digest_incomplete", "kernel_elf_report.digest_xor_count", "ELF must retain all ten digest XOR operations")
    return None


def _ring3_consumer_elf_issue(evidence):
    expected_offsets = _expected_response_offsets()
    if (
        evidence.get("ring3_response_consumer_symbol_found") is not True
        or evidence.get("ring3_response_consumer_instruction_count", 0) <= 0
    ):
        return _issue(
            "elf_consumer_missing",
            "kernel_elf_report.ring3_response_consumer_symbol_found",
            "ELF must contain the bounded Ring3 response consumer",
        )
    if evidence.get("ring3_response_compare_count", 0) < len(expected_offsets):
        return _issue(
            "elf_response_comparisons_missing",
            "kernel_elf_report.ring3_response_compare_count",
            "ELF must retain complete Ring3 comparisons",
        )
    if (
        evidence.get("ring3_response_expected_offsets") != expected_offsets
        or evidence.get("ring3_response_missing_offsets") != []
        or evidence.get("ring3_response_observed_offsets") != expected_offsets
    ):
        return _issue(
            "elf_response_offsets_missing",
            "kernel_elf_report.ring3_response_missing_offsets",
            "ELF must compare every contract-defined Ring3 response offset",
        )
    if evidence.get("ring3_response_success_store_count", 0) < 8:
        return _issue(
            "elf_success_stores_missing",
            "kernel_elf_report.ring3_response_success_store_count",
            "ELF must retain all fixed consumption-record stores",
        )
    if evidence.get("ring3_response_second_interrupt_present") is not True:
        return _issue(
            "elf_second_interrupt_missing",
            "kernel_elf_report.ring3_response_second_interrupt_present",
            "ELF must retain one fixed post-validation int 0x81",
        )
    required_order = (
        "ring3_response_comparisons_before_success_store",
        "ring3_response_success_store_before_interrupt",
        "ring3_response_fail_closed_guard_present",
        "ring3_response_order_valid",
    )
    if any(evidence.get(field) is not True for field in required_order):
        return _issue(
            "elf_consumer_order_invalid",
            "kernel_elf_report.ring3_response_order_valid",
            "Ring3 comparisons, record stores, int 0x81, and ud2 must remain ordered",
        )
    return None


def _expected_response_offsets():
    try:
        contract = json.loads(_CONTRACT_PATH.read_text())
        offsets = [field["offset"] for field in contract["response"]["fields"]]
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return []
    return [f"0x{offset:02x}" for offset in offsets]


def _runtime_evidence_issue(context):
    if (
        context.metadata.get("outcome") != "pass"
        or context.metadata.get("blocker_category") not in (None, "", "none")
    ):
        return _issue("runtime_outcome_invalid", "qemu_smoke.outcome", "QEMU status transaction evidence must pass without a blocker")
    observed = tuple(context.metadata.get("observed_markers", ()))
    expected = get_smoke_marker_order()
    if observed != expected:
        return _issue("metadata_log_mismatch", "qemu_smoke.observed_markers", "QEMU metadata must contain the complete taxonomy sequence")
    serial_markers = tuple(marker for marker in expected if marker in context.serial)
    if serial_markers != expected:
        return _issue("runtime_marker_missing", "qemu_smoke.serial_log", "Serial evidence is missing a required runtime status marker")
    if any(context.serial.count(marker) != 1 for marker in _RUNTIME_MARKERS):
        return _issue("runtime_marker_duplicate", "qemu_smoke.serial_log", "Each runtime status boundary marker must appear exactly once")
    return None


def _load_json(path: Path, field: str):
    if not path.is_file():
        return _issue("missing_evidence", field, f"Missing evidence file: {path}")
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        return _issue("invalid_evidence_json", field, f"Invalid evidence JSON: {exc}")


def _source_range(text: str, start: str, end: str) -> str:
    start_index = text.find(start)
    end_index = text.find(end, start_index + len(start))
    if start_index < 0 or end_index < 0:
        return ""
    return text[start_index:end_index]


def _ordered_issue(text: str, tokens, reason: str, field: str):
    position = -1
    for token in tokens:
        next_position = text.find(token, position + 1)
        if next_position < 0:
            return _issue(reason, field, f"Required ordered token is missing: {token}")
        position = next_position
    return None


def _tokens_issue(text: str, tokens, reason: str, field: str):
    for token in tokens:
        if token not in text:
            return _issue(reason, field, f"Required token is missing: {token}")
    return None


def _issue(reason: str, contract_field: str, detail: str) -> RuntimeStatusEvidenceIssue:
    return RuntimeStatusEvidenceIssue(reason, contract_field, detail)


def _failure(issue: RuntimeStatusEvidenceIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=FIXED_USER_RUNTIME_STATUS_SERVICE_EVIDENCE_INVALID,
        detail=issue.detail,
        action="Restore post-loop ordering, shared runtime status ownership, fixed response validation, and QEMU evidence",
        meta={"reason": issue.reason, "contract_field": issue.contract_field},
    )
