from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness.abi_manifest import ROOT
from harness.codes import FIXED_USER_EXECUTION_CONTEXT_CONTRACT_INVALID, OK
from harness.runtime_evidence_taxonomy import get_smoke_marker_order
from harness.validator import BaseValidator, ValidationResult
from harness.validators_impl.fixed_user_execution_context_contract import _contract_issue

_CONTRACT_PATH = ROOT / "contracts" / "fixed_user_execution_context_contract.v0.json"
_PRIVILEGE_PATH = ROOT / "kernel" / "arch" / "x86_64" / "privilege_transition.asm"
_LAYOUT_PATH = ROOT / "kernel" / "arch" / "x86_64" / "runtime_layout.inc"
_LINKER_PATH = ROOT / "linker" / "kernel.ld"
_RUNTIME_PATH = ROOT / "kernel" / "runtime_progression.odin"
_ELF_REPORT_PATH = ROOT / "artifacts" / "runtime" / "kernel_elf_report.json"
_METADATA_PATH = ROOT / "artifacts" / "runtime" / "qemu_smoke.metadata.json"
_SERIAL_PATH = ROOT / "artifacts" / "runtime" / "qemu_smoke.log"

_CONTEXT_SYMBOLS = (
    "initialize_fixed_user_execution_context",
    "validate_fixed_user_execution_context_ready",
    "activate_fixed_user_execution_context",
    "record_fixed_user_context_transition",
    "validate_fixed_user_context_return",
    "commit_fixed_user_context_result",
    "clear_fixed_user_execution_context",
    "validate_fixed_user_execution_context_cleared",
    "fixed_user_context",
    "fixed_user_context_end",
    "fixed_user_context_result",
    "fixed_user_context_result_end",
)
_REQUIRED_PROTECTED_RANGES = {
    "boot_stack",
    "boot_memory_region",
    "runtime_capability_state",
    "governed_page_tables",
    "governed_gdt",
    "governed_tss",
    "governed_idt",
    "privilege_return_stack",
    "double_fault_stack",
    "fixed_user_code",
    "fixed_user_data",
    "fixed_user_stack",
    "post_context_runtime_state",
}


@dataclass(frozen=True)
class FixedUserContextEvidenceIssue:
    reason: str
    contract_field: str
    detail: str


@dataclass(frozen=True)
class FixedUserContextEvidence:
    privilege: str
    layout: str
    linker: str
    runtime: str
    report: dict[str, object]
    metadata: dict[str, object]
    serial: str


class FixedUserExecutionContextEvidenceValidator(BaseValidator):
    name = "fixed_user_execution_context_evidence"
    subsystem = "fixed_user_execution_context_evidence"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _evidence_issue()
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Fixed user execution context source, ELF, cleanup, and QEMU evidence agree",
        )


def _evidence_issue() -> FixedUserContextEvidenceIssue | None:
    contract_issue = _contract_issue(_CONTRACT_PATH)
    if contract_issue is not None:
        return _issue(contract_issue.reason, contract_issue.contract_field, contract_issue.detail)
    evidence = _load_evidence()
    if isinstance(evidence, FixedUserContextEvidenceIssue):
        return evidence
    checks = (
        _geometry_issue,
        _lifecycle_issue,
        _identity_and_binding_issue,
        _transition_issue,
        _result_and_cleanup_issue,
        _failure_issue,
        _elf_issue,
        _runtime_issue,
    )
    return next((issue for check in checks if (issue := check(evidence)) is not None), None)


def _load_evidence():
    sources = {}
    for name, path in _source_paths().items():
        if not path.is_file():
            return _issue("missing_source", f"source.{name}", f"Missing context source: {path}")
        sources[name] = path.read_text()
    report = _load_json(_ELF_REPORT_PATH, "kernel_elf_report")
    if isinstance(report, FixedUserContextEvidenceIssue):
        return report
    metadata = _load_json(_METADATA_PATH, "qemu_smoke")
    if isinstance(metadata, FixedUserContextEvidenceIssue):
        return metadata
    if not _SERIAL_PATH.is_file():
        return _issue("missing_runtime_evidence", "qemu_smoke.serial", "QEMU serial evidence is missing")
    return FixedUserContextEvidence(
        sources["privilege"], sources["layout"], sources["linker"], sources["runtime"],
        report, metadata, _SERIAL_PATH.read_text(errors="replace"),
    )


def _source_paths() -> dict[str, Path]:
    return {
        "privilege": _PRIVILEGE_PATH,
        "layout": _LAYOUT_PATH,
        "linker": _LINKER_PATH,
        "runtime": _RUNTIME_PATH,
    }


def _geometry_issue(evidence) -> FixedUserContextEvidenceIssue | None:
    return next(
        (
            issue
            for check in (_context_geometry_issue, _result_geometry_issue, _linker_geometry_issue)
            if (issue := check(evidence)) is not None
        ),
        None,
    )


def _context_geometry_issue(evidence):
    context_tokens = (
        "%define FIXED_USER_CONTEXT_SIZE 128",
        "%define FIXED_USER_CONTEXT_ALIGNMENT 16",
        "alignb FIXED_USER_CONTEXT_ALIGNMENT\nfixed_user_context:\n    resb FIXED_USER_CONTEXT_SIZE",
    )
    return _tokens_issue(
        evidence.layout + evidence.privilege,
        context_tokens,
        "context_geometry_invalid",
        "context",
    )


def _result_geometry_issue(evidence):
    result_tokens = (
        "%define FIXED_USER_CONTEXT_RESULT_SIZE 32",
        "%define FIXED_USER_CONTEXT_RESULT_ALIGNMENT 8",
        "alignb FIXED_USER_CONTEXT_RESULT_ALIGNMENT\nfixed_user_context_result:\n    resb FIXED_USER_CONTEXT_RESULT_SIZE",
    )
    return _tokens_issue(
        evidence.layout + evidence.privilege,
        result_tokens,
        "result_geometry_invalid",
        "result",
    )


def _linker_geometry_issue(evidence):
    linker_tokens = (
        "(fixed_user_context_end - fixed_user_context) == 128",
        "(fixed_user_context % 16) == 0",
        "(fixed_user_context_result_end - fixed_user_context_result) == 32",
        "(fixed_user_context_result % 8) == 0",
    )
    return _tokens_issue(evidence.linker, linker_tokens, "linker_geometry_invalid", "elf_geometry")


def _lifecycle_issue(evidence) -> FixedUserContextEvidenceIssue | None:
    checks = (
        _lifecycle_entry_issue,
        _context_format_issue,
        _lifecycle_state_issue,
        _lifecycle_completion_issue,
    )
    return next((issue for check in checks if (issue := check(evidence)) is not None), None)


def _lifecycle_entry_issue(evidence):
    bridge = _source_range(
        evidence.privilege,
        "execute_fixed_user_runtime_status_transaction:",
        "enter_bounded_ring3_probe:",
    )
    required = (
        "call initialize_fixed_user_execution_context",
        "call validate_fixed_user_execution_context_ready",
        "call activate_fixed_user_execution_context",
        "call enter_bounded_ring3_probe",
    )
    return _ordered_issue(bridge, required, "lifecycle_invalid", "lifecycle.successful_transitions")


def _context_format_issue(evidence):
    format_validation = _source_range(
        evidence.privilege,
        "validate_fixed_user_context_format_and_identity:",
        "validate_fixed_user_context_bindings:",
    )
    format_tokens = (
        "FIXED_USER_CONTEXT_FORMAT_VERSION_OFFSET",
        "FIXED_USER_CONTEXT_STRUCTURE_SIZE_OFFSET",
        "FIXED_USER_CONTEXT_FAILURE_INVALID_CONTEXT_FORMAT",
    )
    return _tokens_issue(format_validation, format_tokens, "context_format_invalid", "context.format")


def _lifecycle_state_issue(evidence):
    lifecycle_tokens = (
        "FIXED_USER_CONTEXT_READY",
        "FIXED_USER_CONTEXT_ACTIVE",
        "FIXED_USER_CONTEXT_RETURNED",
        "FIXED_USER_CONTEXT_CLEARED",
    )
    return _tokens_issue(evidence.privilege, lifecycle_tokens, "lifecycle_invalid", "lifecycle")


def _lifecycle_completion_issue(evidence):
    completion = _source_range(evidence.privilege, "complete_fixed_user_execution_context:", "fail_and_clear_fixed_user_execution_context:")
    required = (
        "call validate_fixed_user_context_return",
        "call commit_fixed_user_context_result",
        "call clear_fixed_user_execution_context",
        "call validate_fixed_user_execution_context_cleared",
    )
    return _ordered_issue(completion, required, "lifecycle_invalid", "lifecycle.successful_transitions")


def _identity_and_binding_issue(evidence) -> FixedUserContextEvidenceIssue | None:
    checks = (_identity_issue, _binding_issue, _reserved_state_issue)
    return next((issue for check in checks if (issue := check(evidence)) is not None), None)


def _identity_issue(evidence):
    identity_tokens = (
        "%define FIXED_USER_CONTEXT_OPAQUE_IDENTITY 0x4b4f5a4f43545831",
        "mov rax, FIXED_USER_CONTEXT_OPAQUE_IDENTITY",
        "FIXED_USER_CONTEXT_OPAQUE_IDENTITY_OFFSET], rax",
    )
    issue = _tokens_issue(evidence.layout + evidence.privilege, identity_tokens, "identity_invalid", "context.opaque_identity")
    if issue is not None:
        return issue
    population = _source_range(evidence.privilege, "populate_fixed_user_execution_context:", "reset_fixed_user_context_result:")
    if "lea rax, [rel" in population:
        return _issue("identity_pointer_derived", "context.opaque_identity", "Context identity must not be derived from an address")
    return None


def _binding_issue(evidence):
    binding = _source_range(evidence.privilege, "validate_fixed_user_context_bindings:", "validate_fixed_user_context_reserved_state:")
    binding_tokens = tuple(
        f"FIXED_USER_CONTEXT_{name}_OFFSET"
        for name in (
            "USER_CODE_START", "USER_CODE_SIZE", "USER_DATA_START", "USER_DATA_SIZE",
            "USER_STACK_START", "USER_STACK_SIZE", "USER_STACK_TOP", "ENTRY_RIP",
            "INITIAL_RSP", "USER_CODE_SELECTOR", "USER_DATA_SELECTOR", "RETURN_VECTOR",
            "TRANSITION_BUDGET", "REQUEST_IDENTIFIER",
        )
    )
    return _tokens_issue(binding, binding_tokens, "binding_invalid", "fixed_bindings")


def _reserved_state_issue(evidence):
    reserved = _source_range(evidence.privilege, "validate_fixed_user_context_reserved_state:", "validate_fixed_user_context_phase_and_count:")
    return _tokens_issue(reserved, ("FIXED_USER_CONTEXT_RESERVED_0_OFFSET", "FIXED_USER_CONTEXT_RESERVED_1_OFFSET"), "reserved_state_invalid", "context.reserved")


def _transition_issue(evidence) -> FixedUserContextEvidenceIssue | None:
    checks = (_transition_handler_issue, _transition_accounting_issue, _phase_count_issue)
    return next((issue for check in checks if (issue := check(evidence)) is not None), None)


def _transition_handler_issue(evidence):
    handler = _source_range(evidence.privilege, "privilege_return_handler:", "handle_fixed_user_request:")
    return _ordered_issue(
        handler,
        ("call record_fixed_user_context_transition", "FIXED_USER_PHASE_REQUEST_PENDING", "FIXED_USER_PHASE_RESPONSE_READY"),
        "transition_accounting_invalid",
        "transition_budget.derivation",
    )


def _transition_accounting_issue(evidence):
    transition = _source_range(evidence.privilege, "record_fixed_user_context_transition:", "validate_fixed_user_context_return:")
    required = (
        "call validate_fixed_user_execution_context_active",
        "FIXED_USER_CONTEXT_TRANSITION_BUDGET_OFFSET",
        "jae .budget_exceeded",
        "FIXED_USER_PHASE_REQUEST_PENDING",
        "FIXED_USER_PHASE_RESPONSE_READY",
        "inc dword [rel fixed_user_context + FIXED_USER_CONTEXT_TRANSITION_COUNT_OFFSET]",
    )
    return _tokens_issue(transition, required, "third_transition_allowed", "transition_budget.third_transition")


def _phase_count_issue(evidence):
    phase = _source_range(evidence.privilege, "validate_fixed_user_context_phase_and_count:", "populate_fixed_user_execution_context:")
    required = (
        "FIXED_USER_PHASE_REQUEST_PENDING",
        "FIXED_USER_PHASE_RESPONSE_READY",
        "FIXED_USER_PHASE_CONSUMED",
        "fixed_user_context_count_invalid:",
        "fixed_user_context_association_invalid:",
    )
    return _tokens_issue(phase, required, "phase_count_mismatch_allowed", "transition_budget.phase_and_count_both_required")


def _result_and_cleanup_issue(evidence) -> FixedUserContextEvidenceIssue | None:
    completion = _source_range(evidence.privilege, "complete_fixed_user_execution_context:", "fail_and_clear_fixed_user_execution_context:")
    if completion.count("call commit_fixed_user_context_result") != 1:
        return _issue("result_commit_invalid", "result_lifetime.commit_count", "Success must commit exactly one lifecycle result")
    issue = _ordered_issue(
        completion,
        ("call commit_fixed_user_context_result", "call clear_fixed_user_execution_context", "call validate_fixed_user_execution_context_cleared", "call validate_fixed_user_context_success_result"),
        "result_survival_invalid",
        "result_lifetime.survives_context_clear",
    )
    if issue is not None:
        return issue
    commit = _source_range(evidence.privilege, "commit_fixed_user_context_result:", "clear_fixed_user_execution_context:")
    forbidden = ("OPAQUE_IDENTITY_OFFSET", "USER_CODE_START_OFFSET", "USER_DATA_START_OFFSET", "USER_STACK_START_OFFSET", "USER_CODE_SELECTOR_OFFSET", "RETURN_VECTOR_OFFSET")
    if any(token in commit for token in forbidden):
        return _issue("result_retains_authority", "result.authority_fields_forbidden", "Result must contain no reusable execution authority")
    clear = _source_range(evidence.privilege, "clear_fixed_user_execution_context:", "complete_fixed_user_execution_context:")
    required = ("rep stosq", "FIXED_USER_CONTEXT_FORMAT_VERSION_OFFSET", "FIXED_USER_CONTEXT_STRUCTURE_SIZE_OFFSET", "FIXED_USER_CONTEXT_CLEARED", "call fixed_qword_span_is_zero")
    return _tokens_issue(clear, required, "cleanup_invalid", "clear_state")


def _failure_issue(evidence) -> FixedUserContextEvidenceIssue | None:
    issue = _failure_cleanup_issue(evidence)
    if issue is not None:
        return issue
    issue = _continuation_clear_issue(evidence)
    if issue is not None:
        return issue
    failure = _failure_cleanup_source(evidence)
    if "runtime_serial_write_ring0_return_marker" in failure:
        return _issue("failure_emits_success", "failure_behavior", "Failure cleanup must not emit context completion evidence")
    return None


def _failure_cleanup_source(evidence):
    return _source_range(evidence.privilege, "fail_and_clear_fixed_user_execution_context:", "commit_fixed_user_context_failure_result:")


def _failure_cleanup_issue(evidence):
    return _ordered_issue(
        _failure_cleanup_source(evidence),
        (
            "call commit_fixed_user_context_failure_result",
            "call clear_fixed_user_execution_context",
            "call validate_fixed_user_execution_context_cleared",
            "call validate_fixed_user_context_failure_result_survives",
        ),
        "failure_cleanup_invalid",
        "lifecycle.failure_cleanup_transitions",
    )


def _continuation_clear_issue(evidence):
    continuation = _source_range(evidence.privilege, "privilege_ring0_continuation:", "privilege_fault_sink:")
    return _ordered_issue(
        continuation,
        ("call complete_fixed_user_execution_context", "call runtime_serial_write_ring0_return_marker"),
        "continuation_before_clear",
        "clear_state.normal_continuation_requires_valid_clear_state",
    )


def _elf_issue(evidence) -> FixedUserContextEvidenceIssue | None:
    record = evidence.report.get("fixed_user_execution_context")
    if not isinstance(record, dict):
        return _issue("missing_elf_evidence", "kernel_elf_report.fixed_user_execution_context", "Context ELF evidence is missing")
    issue = _elf_symbol_issue(record)
    if issue is not None:
        return issue
    issue = _elf_storage_issue(record)
    if issue is not None:
        return issue
    return _elf_overlap_issue(record)


def _elf_symbol_issue(record):
    symbols = record.get("symbols", {})
    if not isinstance(symbols, dict) or any(not symbols.get(name, {}).get("present") for name in _CONTEXT_SYMBOLS):
        return _issue("missing_elf_symbol", "kernel_elf_report.symbols", "A context ELF symbol is missing")
    return None


def _elf_storage_issue(record):
    for name, size, alignment in (("context", 128, 16), ("result", 32, 8)):
        storage = record.get(name, {})
        if storage.get("size_bytes") != size or storage.get("start_aligned") is not True or storage.get("required_alignment_bytes") != alignment:
            return _issue("elf_geometry_invalid", f"kernel_elf_report.{name}", f"ELF {name} geometry is invalid")
        if storage.get("section") != ".bss" or storage.get("writable") is not True or storage.get("non_executable") is not True or storage.get("higher_half_address") is not True:
            return _issue("elf_storage_policy_invalid", f"kernel_elf_report.{name}", f"ELF {name} must be higher-half RW-NX .bss storage")
    return None


def _elf_overlap_issue(record):
    protected = record.get("protected_ranges", {})
    if not isinstance(protected, dict) or not _REQUIRED_PROTECTED_RANGES <= protected.keys():
        return _issue("elf_overlap_invalid", "kernel_elf_report.protected_ranges", "ELF protected-range evidence is incomplete")
    if record.get("ordering_valid") is not True or record.get("no_overlap") is not True or record.get("overlaps") != []:
        return _issue("elf_overlap_invalid", "kernel_elf_report.overlaps", "Context and result must not overlap governed storage")
    return None


def _runtime_issue(evidence) -> FixedUserContextEvidenceIssue | None:
    expected = get_smoke_marker_order()
    observed = tuple(evidence.metadata.get("observed_markers", ()))
    if evidence.metadata.get("outcome") != "pass" or evidence.metadata.get("blocker_category") not in (None, "", "none"):
        return _issue("runtime_outcome_invalid", "qemu_smoke.outcome", "QEMU context evidence must pass without a blocker")
    if len(expected) != 41 or observed != expected:
        return _issue("marker_sequence_changed", "qemu_smoke.observed_markers", "The exact 41-marker sequence must remain unchanged")
    if any(evidence.serial.count(marker) != 1 for marker in expected):
        return _issue("runtime_marker_invalid", "qemu_smoke.serial", "Every governed marker must appear exactly once")
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


def _tokens_issue(text: str, tokens, reason: str, field: str):
    missing = next((token for token in tokens if token not in text), None)
    if missing is None:
        return None
    return _issue(reason, field, f"Required context token is missing: {missing}")


def _ordered_issue(text: str, tokens, reason: str, field: str):
    position = -1
    for token in tokens:
        position = text.find(token, position + 1)
        if position < 0:
            return _issue(reason, field, f"Required ordered context token is missing: {token}")
    return None


def _issue(reason: str, field: str, detail: str) -> FixedUserContextEvidenceIssue:
    return FixedUserContextEvidenceIssue(reason, field, detail)


def _failure(issue: FixedUserContextEvidenceIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=FIXED_USER_EXECUTION_CONTEXT_CONTRACT_INVALID,
        detail=issue.detail,
        action="Restore the fixed user execution context source, ELF, cleanup, and runtime evidence",
        meta={"reason": issue.reason, "contract_field": issue.contract_field},
    )
