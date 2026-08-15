from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness.abi_manifest import ROOT
from harness.codes import BOUNDED_REPEATED_USER_SESSION_EVIDENCE_INVALID, OK
from harness.runtime_evidence_taxonomy import get_smoke_marker_order
from harness.runtime_marker_occurrences import (
    extract_marker_occurrences,
    marker_occurrence_counts,
)
from harness.validator import BaseValidator, ValidationResult
from harness.validators_impl.bounded_repeated_user_session_contract import _contract_issue

_CONTRACT_PATH = ROOT / "contracts" / "bounded_repeated_user_session_contract.v0.json"
_RUNTIME_PATH = ROOT / "kernel" / "runtime_progression.odin"
_PRIVILEGE_PATH = ROOT / "kernel" / "arch" / "x86_64" / "privilege_transition.asm"
_LAYOUT_PATH = ROOT / "kernel" / "arch" / "x86_64" / "runtime_layout.inc"
_LINKER_PATH = ROOT / "linker" / "kernel.ld"
_ELF_REPORT_PATH = ROOT / "artifacts" / "runtime" / "kernel_elf_report.json"
_METADATA_PATH = ROOT / "artifacts" / "runtime" / "qemu_smoke.metadata.json"
_SERIAL_PATH = ROOT / "artifacts" / "runtime" / "qemu_smoke.log"

_REQUIRED_SYMBOLS = (
    "execute_bounded_repeated_user_sessions",
    "execute_first_bounded_user_session",
    "execute_second_bounded_user_session",
    "initialize_repeated_session_coordinator",
    "execute_fixed_user_session",
    "begin_fixed_user_session",
    "fixed_user_session_succeeds",
    "complete_fixed_user_session",
    "prepare_next_fixed_user_session",
    "finalize_repeated_session_coordinator",
    "reset_completed_fixed_user_session",
    "reset_fixed_user_context_for_reuse",
    "validate_fixed_user_session_cleanup",
    "reset_fixed_user_context_result",
    "reset_fixed_user_execution_context_for_reuse",
    "validate_fixed_user_session_reset_state",
    "validate_fixed_user_session_identity_sequence",
    "repeated_user_session_coordinator",
)


@dataclass(frozen=True)
class RepeatedSessionEvidenceIssue:
    reason: str
    contract_field: str
    detail: str


@dataclass(frozen=True)
class RepeatedSessionEvidence:
    runtime: str
    privilege: str
    layout: str
    linker: str
    report: dict[str, object]
    metadata: dict[str, object]
    serial: str


class BoundedRepeatedUserSessionEvidenceValidator(BaseValidator):
    name = "bounded_repeated_user_session_evidence"
    subsystem = "bounded_repeated_user_session_evidence"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _evidence_issue()
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Two fixed user sessions, reset boundary, ELF state, and QEMU occurrences agree",
        )


def _evidence_issue() -> RepeatedSessionEvidenceIssue | None:
    contract_issue = _contract_issue(_CONTRACT_PATH)
    if contract_issue is not None:
        return _issue(contract_issue.reason, contract_issue.contract_field, contract_issue.detail)
    evidence = _load_evidence()
    if isinstance(evidence, RepeatedSessionEvidenceIssue):
        return evidence
    checks = (
        _coordinator_issue,
        _two_session_flow_issue,
        _single_session_issue,
        _reset_boundary_issue,
        _identity_issue,
        _failure_issue,
        _elf_issue,
        _runtime_issue,
    )
    return next((issue for check in checks if (issue := check(evidence)) is not None), None)


def _load_evidence():
    sources = {}
    for name, path in _source_paths().items():
        if not path.is_file():
            return _issue("missing_source", f"source.{name}", f"Missing repeated-session source: {path}")
        sources[name] = path.read_text()
    report = _load_json(_ELF_REPORT_PATH, "kernel_elf_report")
    if isinstance(report, RepeatedSessionEvidenceIssue):
        return report
    metadata = _load_json(_METADATA_PATH, "qemu_smoke")
    if isinstance(metadata, RepeatedSessionEvidenceIssue):
        return metadata
    if not _SERIAL_PATH.is_file():
        return _issue("missing_runtime_evidence", "qemu_smoke.serial", "QEMU serial evidence is missing")
    return RepeatedSessionEvidence(
        sources["runtime"], sources["privilege"], sources["layout"], sources["linker"],
        report, metadata, _SERIAL_PATH.read_text(errors="replace"),
    )


def _source_paths() -> dict[str, Path]:
    return {
        "runtime": _RUNTIME_PATH,
        "privilege": _PRIVILEGE_PATH,
        "layout": _LAYOUT_PATH,
        "linker": _LINKER_PATH,
    }


def _coordinator_issue(evidence):
    required = (
        "REQUIRED_SESSION_COUNT :: u32(2)",
        "REQUIRED_TOTAL_TRANSITION_COUNT :: u32(4)",
        "Repeated_User_Session_Coordinator :: struct #align(8)",
        "#assert(size_of(Repeated_User_Session_Coordinator) == REPEATED_SESSION_COORDINATOR_SIZE)",
        "#assert(align_of(Repeated_User_Session_Coordinator) == 8)",
        "repeated_user_session_coordinator: Repeated_User_Session_Coordinator",
    )
    issue = _tokens_issue(evidence.runtime, required, "coordinator_invalid", "coordinator")
    if issue is not None:
        return issue
    linker_tokens = ("DEFINED(repeated_user_session_coordinator)", "(repeated_user_session_coordinator % 8) == 0")
    return _tokens_issue(evidence.linker, linker_tokens, "coordinator_linker_invalid", "coordinator.storage")


def _two_session_flow_issue(evidence):
    flow = _source_range(evidence.runtime, "execute_bounded_repeated_user_sessions ::", "execute_fixed_user_session ::")
    required = (
        "initialize_repeated_session_coordinator()",
        "repeated_session_initial_failure_code()",
        "execute_first_bounded_user_session()",
        "execute_second_bounded_user_session()",
        "execute_fixed_user_session(FIRST_SESSION_ORDINAL)",
        "prepare_next_fixed_user_session()",
        "execute_fixed_user_session(SECOND_SESSION_ORDINAL)",
        "finalize_repeated_session_coordinator()",
    )
    issue = _ordered_issue(flow, required, "session_flow_invalid", "sessions")
    if issue is not None:
        return issue
    if flow.count("execute_fixed_user_session(") != 2 or "while " in flow or "for " in flow:
        return _issue("session_count_unbounded", "sessions.required_count", "The coordinator must contain two explicit calls and no loop")
    return None


def _single_session_issue(evidence):
    session = _source_range(evidence.runtime, "execute_fixed_user_session ::", "prepare_next_fixed_user_session ::")
    required = (
        "next_fixed_user_session_failure_code(session_ordinal)",
        "set_active_repeated_session_ordinal(session_ordinal)",
        "execute_fixed_user_runtime_status_transaction()",
        "validate_fixed_user_context_success_result()",
        "record_completed_fixed_user_session()",
        "completed_session_failure_code(session_ordinal)",
    )
    return _ordered_issue(session, required, "session_lifecycle_invalid", "sessions.lifecycle")


def _reset_boundary_issue(evidence):
    reset = _source_range(evidence.runtime, "prepare_next_fixed_user_session ::", "initialize_repeated_session_coordinator ::")
    required = (
        "prepare_next_fixed_user_session ::",
        "reset_completed_fixed_user_session(",
        "finalize_repeated_session_coordinator ::",
        "reset_completed_fixed_user_session(",
        "reset_completed_fixed_user_session ::",
        "validate_fixed_user_session_cleanup()",
        "reset_fixed_user_context_result()",
        "reset_fixed_user_context_for_reuse(cleanup_failure_code)",
        "reset_fixed_user_context_for_reuse ::",
        "reset_fixed_user_execution_context_for_reuse()",
        "validate_fixed_user_session_reset_state()",
    )
    issue = _ordered_issue(reset, required, "reset_order_invalid", "reset_boundary")
    if issue is not None:
        return issue
    assembly_tokens = (
        "reset_fixed_user_context_result:",
        "jmp fixed_user_context_result_is_initial",
        "reset_fixed_user_execution_context_for_reuse:",
        "call validate_fixed_user_execution_context_cleared",
        "call fixed_user_context_is_uninitialized",
        "validate_fixed_user_session_reset_state:",
        "call fixed_user_context_result_is_initial",
        "call fixed_user_session_storage_is_zero",
        "FIXED_USER_PHASE_REQUEST_PENDING",
        "FIXED_USER_DATA_SCRATCH_VA",
        "user_probe_stack",
    )
    issue = _tokens_issue(evidence.privilege, assembly_tokens, "reset_readback_invalid", "reset_storage")
    if issue is not None:
        return issue
    reset_validation = _source_range(
        evidence.privilege,
        "validate_fixed_user_session_reset_state:",
        "invalidate_fixed_user_session_state:",
    )
    return _tokens_issue(
        reset_validation,
        ("call fixed_user_context_result_is_initial", "call fixed_user_session_storage_is_zero"),
        "reset_readback_invalid",
        "reset_storage",
    )


def _identity_issue(evidence):
    identity_tokens = (
        "%define FIXED_USER_CONTEXT_OPAQUE_IDENTITY 0x4b4f5a4f43545831",
        "%define FIXED_USER_CONTEXT_SECOND_OPAQUE_IDENTITY 0x4b4f5a4f43545832",
        "expected_fixed_user_context_identity:",
        "REPEATED_USER_SESSION_FIRST_ORDINAL",
        "REPEATED_USER_SESSION_SECOND_ORDINAL",
        "cmp rax, rdx",
        "call fixed_user_identity_is_non_pointer",
    )
    issue = _tokens_issue(evidence.layout + evidence.privilege, identity_tokens, "identity_sequence_invalid", "identities")
    if issue is not None:
        return issue
    if evidence.privilege.count("call fixed_user_identity_is_non_pointer") < 2:
        return _issue("identity_pointer_policy_invalid", "identities.pointer_policy", "Both identities must pass the non-pointer check")
    return None


def _failure_issue(evidence):
    failure = _source_range(evidence.runtime, "fail_repeated_user_sessions ::", "set_active_repeated_session_ordinal ::")
    required = (
        "active_session_ordinal, 0",
        "failure_code, failure_code",
        "invalidate_fixed_user_session_state()",
        "return RUNTIME_REPEATED_SESSION_FAILURE",
    )
    issue = _ordered_issue(failure, required, "failure_cleanup_invalid", "failure_behavior")
    if issue is not None:
        return issue
    required_codes = (
        "REPEATED_SESSION_FAILURE_INVALID_COORDINATOR_FORMAT",
        "REPEATED_SESSION_FAILURE_INVALID_COORDINATOR_SIZE",
        "REPEATED_SESSION_FAILURE_INVALID_SESSION_ORDINAL",
        "REPEATED_SESSION_FAILURE_INVALID_REQUIRED_SESSION_COUNT",
        "REPEATED_SESSION_FAILURE_STALE_CONTEXT_BEFORE_SESSION",
        "REPEATED_SESSION_FAILURE_STALE_CONTEXT_RESULT_BEFORE_SESSION",
        "REPEATED_SESSION_FAILURE_IDENTITY_REUSE",
        "REPEATED_SESSION_FAILURE_FIRST_SESSION",
        "REPEATED_SESSION_FAILURE_FIRST_SESSION_CLEANUP",
        "REPEATED_SESSION_FAILURE_FIRST_RESULT_RESET",
        "REPEATED_SESSION_FAILURE_SECOND_SESSION",
        "REPEATED_SESSION_FAILURE_SECOND_SESSION_CLEANUP",
        "REPEATED_SESSION_FAILURE_SECOND_RESULT_RESET",
        "REPEATED_SESSION_FAILURE_COMPLETED_COUNT",
        "REPEATED_SESSION_FAILURE_TOTAL_TRANSITION_COUNT",
        "REPEATED_SESSION_FAILURE_UNEXPECTED_THIRD_SESSION",
        "REPEATED_SESSION_FAILURE_FINAL_VALIDATION",
    )
    return _tokens_issue(evidence.runtime, required_codes, "failure_codes_missing", "failure_behavior.codes")


def _elf_issue(evidence):
    record = evidence.report.get("bounded_repeated_user_session")
    if not isinstance(record, dict):
        return _issue("missing_elf_evidence", "kernel_elf_report.bounded_repeated_user_session", "Repeated-session ELF evidence is missing")
    symbols = record.get("symbols", {})
    if not isinstance(symbols, dict) or any(not symbols.get(name, {}).get("present") for name in _REQUIRED_SYMBOLS):
        return _issue("missing_elf_symbol", "kernel_elf_report.bounded_repeated_user_session.symbols", "A repeated-session ELF symbol is missing")
    coordinator = record.get("coordinator", {})
    geometry = (
        coordinator.get("size_bytes") == 32,
        coordinator.get("required_alignment_bytes") == 8,
        coordinator.get("start_aligned") is True,
        coordinator.get("section") == ".bss",
        coordinator.get("writable") is True,
        coordinator.get("non_executable") is True,
        coordinator.get("higher_half_address") is True,
    )
    if not all(geometry) or record.get("coordinator_overlap_count") != 0:
        return _issue("elf_coordinator_invalid", "kernel_elf_report.bounded_repeated_user_session.coordinator", "Coordinator must be non-overlapping higher-half RW-NX .bss storage")
    required = {
        "session_call_count": 2,
        "total_session_call_count": 2,
        "session_helper_call_order_valid": True,
        "between_session_reset_order_valid": True,
        "terminal_reset_order_valid": True,
        "later_capability_gate_valid": True,
    }
    if any(record.get(field) != value for field, value in required.items()):
        return _issue("elf_flow_invalid", "kernel_elf_report.bounded_repeated_user_session", "ELF must retain exactly two session calls, both reset paths, and the later-capability gate")
    return None


def _runtime_issue(evidence):
    expected = get_smoke_marker_order()
    observed = evidence.metadata.get("observed_markers")
    if evidence.metadata.get("outcome") != "pass" or evidence.metadata.get("blocker_category") not in (None, "", "none"):
        return _issue("runtime_outcome_invalid", "qemu_smoke.outcome", "Repeated-session QEMU evidence must pass without a blocker")
    if observed != list(expected) or len(expected) != 52:
        return _issue("marker_sequence_invalid", "qemu_smoke.observed_markers", "QEMU metadata must preserve the exact 52 marker occurrences")
    expected_counts = marker_occurrence_counts(expected)
    metadata_fields = {
        "expected_marker_count": 52,
        "observed_marker_count": 52,
        "marker_occurrence_counts": expected_counts,
        "completed_session_count": 2,
        "active_or_failed_session_ordinal": 0,
    }
    if any(evidence.metadata.get(field) != value for field, value in metadata_fields.items()):
        return _issue("runtime_count_invalid", "qemu_smoke.marker_occurrences", "QEMU occurrence and session counts must match the two-session contract")
    serial_markers = extract_marker_occurrences(evidence.serial, expected_counts)
    if serial_markers != list(expected):
        return _issue("serial_sequence_invalid", "qemu_smoke.serial", "Serial evidence must preserve every ordered marker occurrence")
    return None


def _load_json(path: Path, field: str):
    if not path.is_file():
        return _issue("missing_evidence", field, f"Missing repeated-session evidence: {path}")
    try:
        value = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        return _issue("invalid_evidence_json", field, f"Invalid repeated-session JSON evidence: {exc}")
    if not isinstance(value, dict):
        return _issue("invalid_evidence_json", field, "Repeated-session JSON evidence must be an object")
    return value


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
    return _issue(reason, field, f"Missing required evidence token: {missing}")


def _ordered_issue(text: str, tokens, reason: str, field: str):
    position = -1
    for token in tokens:
        position = text.find(token, position + 1)
        if position < 0:
            return _issue(reason, field, f"Missing or out-of-order evidence token: {token}")
    return None


def _issue(reason: str, contract_field: str, detail: str) -> RepeatedSessionEvidenceIssue:
    return RepeatedSessionEvidenceIssue(reason, contract_field, detail)


def _failure(issue: RepeatedSessionEvidenceIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=BOUNDED_REPEATED_USER_SESSION_EVIDENCE_INVALID,
        detail=issue.detail,
        meta={"reason": issue.reason, "contract_field": issue.contract_field},
    )
