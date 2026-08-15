from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness import bounded_repeated_user_session_contract as contract_module
from harness.codes import BOUNDED_REPEATED_USER_SESSION_CONTRACT_INVALID, OK
from harness.validator import BaseValidator, ValidationResult

_COORDINATOR_FIELDS = (
    ("format_version", 0),
    ("structure_size", 4),
    ("required_session_count", 8),
    ("active_session_ordinal", 12),
    ("completed_session_count", 16),
    ("observed_total_transition_count", 20),
    ("failure_code", 24),
    ("reserved", 28),
)
_LIFECYCLE = ("UNINITIALIZED", "READY", "ACTIVE", "RETURNED", "CLEARED")
_RESET_STEPS = (
    "validate_context_cleared",
    "validate_session_result",
    "record_bounded_outcome",
    "reset_context_result",
    "validate_context_result_reset",
    "validate_transaction_storage_reset",
    "reset_context_to_uninitialized",
    "validate_context_uninitialized",
    "assign_fresh_identity",
)
_FORBIDDEN_COORDINATOR_FIELDS = {
    "context_identity",
    "pointer",
    "selector",
    "physical_address",
    "mapping_authority",
    "executable_address",
    "capability_handle",
    "user_controlled_value",
}
_FAILURE_CODES = {
    "INVALID_COORDINATOR_FORMAT": 1,
    "INVALID_COORDINATOR_SIZE": 2,
    "INVALID_SESSION_ORDINAL": 3,
    "INVALID_REQUIRED_SESSION_COUNT": 4,
    "STALE_CONTEXT_BEFORE_SESSION": 5,
    "STALE_CONTEXT_RESULT_BEFORE_SESSION": 6,
    "IDENTITY_REUSE": 7,
    "FIRST_SESSION_FAILURE": 8,
    "FIRST_SESSION_CLEANUP_FAILURE": 9,
    "FIRST_RESULT_RESET_FAILURE": 10,
    "SECOND_SESSION_FAILURE": 11,
    "SECOND_SESSION_CLEANUP_FAILURE": 12,
    "SECOND_RESULT_RESET_FAILURE": 13,
    "COMPLETED_SESSION_COUNT_MISMATCH": 14,
    "TOTAL_TRANSITION_COUNT_MISMATCH": 15,
    "UNEXPECTED_THIRD_SESSION_ATTEMPT": 16,
    "COORDINATOR_FINAL_VALIDATION_FAILURE": 17,
}


@dataclass(frozen=True)
class BoundedRepeatedUserSessionIssue:
    reason: str
    contract_field: str
    detail: str


class BoundedRepeatedUserSessionContractValidator(BaseValidator):
    name = "bounded_repeated_user_session_contract"
    subsystem = "bounded_repeated_user_session_contract"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _contract_issue(contract_module.CONTRACT_PATH)
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(code=OK, detail="Repeated user session contract requires two clean bounded lifecycles")


def _contract_issue(path: Path) -> BoundedRepeatedUserSessionIssue | None:
    contract = _load_contract(path)
    if isinstance(contract, BoundedRepeatedUserSessionIssue):
        return contract
    checks = (
        _authority_issue,
        _session_issue,
        _identity_issue,
        _coordinator_issue,
        _reset_issue,
        _failure_code_issue,
        _marker_issue,
        _continuation_issue,
        _claim_issue,
    )
    return next((issue for check in checks if (issue := check(contract)) is not None), None)


def _load_contract(path: Path):
    if not path.is_file():
        return _issue("missing_contract", "contract", f"Missing repeated-session contract: {path}")
    try:
        return contract_module.load_bounded_repeated_user_session_contract(path)
    except json.JSONDecodeError as exc:
        return _issue("invalid_json", "contract", f"Invalid repeated-session JSON: {exc}")
    except (KeyError, TypeError, ValueError) as exc:
        return _issue("contract_schema_violation", "contract", f"Repeated-session schema violation: {exc}")


def _authority_issue(contract) -> BoundedRepeatedUserSessionIssue | None:
    expected = {
        "owner": "ring0",
        "context_count": 1,
        "allocation": "fixed_static",
        "required_session_count": 2,
        "user_selectable_session_count": False,
        "public_abi": False,
    }
    return None if contract.authority == expected else _issue("invalid_authority", "authority", "Authority must remain one fixed Ring0-owned context and exactly two sessions")


def _session_issue(contract) -> BoundedRepeatedUserSessionIssue | None:
    session = contract.session
    valid = tuple(session.get("ordinals", ())) == (1, 2)
    valid &= tuple(session.get("lifecycle", ())) == _LIFECYCLE
    valid &= session.get("transition_budget") == 2 and session.get("total_transition_count") == 4
    valid &= session.get("third_session") == session.get("fifth_transition") == "fail_closed"
    return None if valid else _issue("invalid_session_contract", "session", "Two explicit two-transition lifecycles and no third session are required")


def _identity_issue(contract) -> BoundedRepeatedUserSessionIssue | None:
    first, second = contract_module.session_identities(contract)
    identity = contract.identity
    valid = first != 0 and second != 0 and first != second
    valid &= identity.get("nonzero") is True and identity.get("distinct") is True
    valid &= all(identity.get(field) is False for field in ("pointer_derived", "pid", "user_visible", "user_writable"))
    valid &= identity.get("invalid_after_clear") is True
    return None if valid else _issue("invalid_identity_policy", "identity", "Session identities must be distinct nonzero kernel-only non-pointer values")


def _coordinator_issue(contract) -> BoundedRepeatedUserSessionIssue | None:
    coordinator = contract.coordinator
    geometry = (coordinator.get("format_version"), coordinator.get("size_bytes"), coordinator.get("alignment_bytes"))
    fields = tuple((field.get("name"), field.get("offset")) for field in coordinator.get("fields", ()))
    field_names = {name for name, _ in fields}
    valid = geometry == (1, 32, 8) and fields == _COORDINATOR_FIELDS
    valid &= coordinator.get("active_session_ordinal_values") == [0, 1, 2]
    valid &= coordinator.get("completed_session_count_maximum") == 2
    valid &= coordinator.get("observed_total_transition_count_maximum") == 4
    valid &= not field_names & _FORBIDDEN_COORDINATOR_FIELDS
    valid &= _FORBIDDEN_COORDINATOR_FIELDS <= set(coordinator.get("authority_fields_forbidden", ()))
    return None if valid else _issue("invalid_coordinator", "coordinator", "Coordinator geometry, bounds, and authority exclusions must be exact")


def _reset_issue(contract) -> BoundedRepeatedUserSessionIssue | None:
    reset = contract.reset_boundary
    valid = tuple(reset.get("ordered_steps", ())) == _RESET_STEPS
    valid &= reset.get("silent_repair") is False and reset.get("readback_required") is True
    required = {"request_buffer", "response_buffer", "consumption_record", "user_stack", "transaction_phase", "context_result"}
    valid &= required <= set(reset.get("transaction_storage", ()))
    return None if valid else _issue("invalid_reset_boundary", "reset_boundary", "Reset must validate cleanup, result readback, storage, zero context, then fresh identity")


def _failure_code_issue(contract) -> BoundedRepeatedUserSessionIssue | None:
    if contract.failure_codes == _FAILURE_CODES:
        return None
    return _issue("invalid_failure_codes", "failure_codes", "Repeated-session failures must retain the exact internal diagnostic set")


def _marker_issue(contract) -> BoundedRepeatedUserSessionIssue | None:
    marker = contract.marker_policy
    valid = marker.get("starting_occurrence_count") == 41 and marker.get("transaction_block_length") == 11
    valid &= marker.get("transaction_block_occurrences") == 2 and marker.get("final_occurrence_count") == 52
    valid &= marker.get("catalog_names_changed") is False and marker.get("duplicate_occurrences_preserved") is True
    valid &= marker.get("final_marker") == "KOZO_RUNTIME_RETURN_OK"
    return None if valid else _issue("invalid_marker_policy", "marker_policy", "The unchanged 11-marker block must occur twice in the 52-occurrence sequence")


def _continuation_issue(contract) -> BoundedRepeatedUserSessionIssue | None:
    continuation = contract.runtime_continuation
    valid = continuation.get("later_capabilities_after_completed_sessions") == 2
    valid &= continuation.get("later_capabilities_after_total_transitions") == 4
    valid &= continuation.get("terminal_halt_unchanged") is True
    valid &= continuation.get("failure_converges_on_terminal_halt") is True
    return None if valid else _issue("invalid_continuation", "runtime_continuation", "Later capabilities require both sessions and all four transitions")


def _claim_issue(contract) -> BoundedRepeatedUserSessionIssue | None:
    prohibited = {"processes", "scheduling", "dynamic allocation", "public syscall ABI"}
    if prohibited <= set(contract.claim_boundary["does_not_prove"]):
        return None
    return _issue("claim_overreach", "claim_boundary.does_not_prove", "Repeated sessions must not claim processes, scheduling, allocation, or a public ABI")


def _issue(reason: str, field: str, detail: str) -> BoundedRepeatedUserSessionIssue:
    return BoundedRepeatedUserSessionIssue(reason, field, detail)


def _failure(issue: BoundedRepeatedUserSessionIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=BOUNDED_REPEATED_USER_SESSION_CONTRACT_INVALID,
        detail=f"{issue.reason}: {issue.detail}",
        action=f"Correct {issue.contract_field} in the bounded repeated user session contract",
    )
