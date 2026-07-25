from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness import runtime_state_transition_capability as contract_module
from harness.codes import OK, RUNTIME_STATE_TRANSITION_CAPABILITY_INVALID
from harness.validator import BaseValidator, ValidationResult

_CONTRACT_PATH = contract_module.CONTRACT_PATH
_STATE_FIELDS = (
    ("state", 0, 4),
    ("reserved", 4, 4),
    ("generation", 8, 8),
)
_REQUEST_FIELDS = (
    ("version", 0, 4),
    ("capability_id", 4, 4),
    ("expected_state", 8, 4),
    ("requested_state", 12, 4),
    ("expected_generation", 16, 8),
    ("flags", 24, 4),
    ("reserved", 28, 4),
)
_RESPONSE_FIELDS = (
    ("version", 0, 4),
    ("capability_id", 4, 4),
    ("status", 8, 4),
    ("previous_state", 12, 4),
    ("current_state", 16, 4),
    ("reserved_0", 20, 4),
    ("previous_generation", 24, 8),
    ("current_generation", 32, 8),
    ("reserved_1", 40, 8),
)
_MARKERS = (
    "KOZO_RUNTIME_STATE_UPDATE_ENTER",
    "KOZO_RUNTIME_STATE_UPDATE_OK",
    "KOZO_SECOND_CAPABILITY_OK",
)
_STATUSES = {
    "success": 0,
    "invalid_request_pointer": 9,
    "invalid_response_pointer": 10,
    "unsupported_request_version": 11,
    "unsupported_capability": 12,
    "unsupported_flags": 13,
    "invalid_reserved_field": 14,
    "response_validation_failure": 15,
    "capability_execution_failure": 16,
    "stale_generation": 17,
    "invalid_transition": 18,
    "readback_failure": 19,
}
_NON_GOALS = (
    "arbitrary kernel memory writes",
    "general state-machine framework",
    "dynamic capability registration",
    "concurrent execution",
    "userspace execution",
    "authentication",
    "authorization",
    "privilege separation",
    "persistent state",
    "Linux compatibility",
    "POSIX compatibility",
    "production readiness",
)


@dataclass(frozen=True)
class StateTransitionIssue:
    reason: str
    contract_field: str
    detail: str


class RuntimeStateTransitionCapabilityValidator(BaseValidator):
    name = "runtime_state_transition_capability"
    subsystem = "runtime_state_transition_capability"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _contract_issue(_CONTRACT_PATH)
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Runtime state transition contract governs one bounded READY/0 to ACTIVE/1 capability",
        )


def _contract_issue(path: Path) -> StateTransitionIssue | None:
    contract = _load_contract(path)
    if isinstance(contract, StateTransitionIssue):
        return contract
    checks = (
        _capability_issue,
        _state_issue,
        _request_issue,
        _response_issue,
        _transition_issue,
        _status_issue,
        _marker_issue,
        _failure_issue,
        _claim_issue,
    )
    for check in checks:
        issue = check(contract)
        if issue is not None:
            return issue
    return None


def _load_contract(path: Path):
    if not path.is_file():
        return _issue("missing_contract_file", "contract", f"State transition contract is missing: {path}")
    try:
        return contract_module.load_runtime_state_transition_capability(path)
    except json.JSONDecodeError as exc:
        return _issue("invalid_contract_json", "contract", f"State transition contract is invalid JSON: {exc}")
    except (KeyError, TypeError, ValueError) as exc:
        return _issue("contract_schema_violation", "contract", f"State transition contract schema violation: {exc}")


def _capability_issue(contract) -> StateTransitionIssue | None:
    actual = tuple(vars(contract.capability).values())
    expected = (
        "RUNTIME_STATE_TRANSITION",
        "SECOND_GOVERNED_RUNTIME_CAPABILITY",
        2,
        6,
        "implemented_pending_ci",
        "kernel/runtime_capability.odin",
        "execute_second_governed_capability",
        "dispatch_runtime_capability",
        "transition_runtime_state",
    )
    if actual != expected:
        return _issue("invalid_capability_identity", "capability", "State transition capability identity is invalid")
    return None


def _state_issue(contract) -> StateTransitionIssue | None:
    state = contract.state
    if (state.symbol, state.size_bytes, state.alignment_bytes) != (
        "runtime_state_transition_cell",
        16,
        8,
    ):
        return _issue("invalid_state_geometry", "state", "Runtime state cell must be 16 bytes and 8-byte aligned")
    if _field_tuples(state.fields) != _STATE_FIELDS:
        return _issue("invalid_state_geometry", "state.fields", "Runtime state cell field layout is invalid")
    if state.initial_values != {"state": 1, "reserved": 0, "generation": 0}:
        return _issue("invalid_initial_state", "state.initial_values", "Initial state must be READY generation 0")
    if state.terminal_values != {"state": 2, "reserved": 0, "generation": 1}:
        return _issue("invalid_terminal_state", "state.terminal_values", "Terminal state must be ACTIVE generation 1")
    if not state.volatile_access_required or state.concurrency_safe or state.persistent:
        return _issue("invalid_state_policy", "state.volatile_access_required", "State must require volatile access without concurrency or persistence claims")
    return None


def _request_issue(contract) -> StateTransitionIssue | None:
    request = contract.request
    if (request.version, request.size_bytes, request.alignment_bytes) != (1, 32, 8):
        return _issue("invalid_request_geometry", "request", "State transition request must be version 1, 32 bytes, and 8-byte aligned")
    if _field_tuples(request.fields) != _REQUEST_FIELDS:
        return _issue("invalid_request_geometry", "request.fields", "State transition request field layout is invalid")
    expected = {
        "capability_id": 2,
        "expected_state": 1,
        "requested_state": 2,
        "expected_generation": 0,
        "flags": 0,
        "reserved": 0,
    }
    if request.values != expected or request.supported_flags != 0:
        return _issue("invalid_request_values", "request.required_values", "Governed request values must describe READY/0 to ACTIVE/1")
    return None


def _response_issue(contract) -> StateTransitionIssue | None:
    response = contract.response
    if (response.version, response.size_bytes, response.alignment_bytes) != (1, 48, 8):
        return _issue("invalid_response_geometry", "response", "State transition response must be version 1, 48 bytes, and 8-byte aligned")
    if _field_tuples(response.fields) != _RESPONSE_FIELDS:
        return _issue("invalid_response_geometry", "response.fields", "State transition response field layout is invalid")
    expected = {
        "capability_id": 2,
        "status": 0,
        "previous_state": 1,
        "current_state": 2,
        "reserved_0": 0,
        "previous_generation": 0,
        "current_generation": 1,
        "reserved_1": 0,
    }
    if response.values != expected:
        return _issue("invalid_response_values", "response.expected_values", "State transition response values are invalid")
    return None


def _transition_issue(contract) -> StateTransitionIssue | None:
    expected = {
        "allowed_from_state": 1,
        "allowed_to_state": 2,
        "required_initial_generation": 0,
        "required_terminal_generation": 1,
        "generation_increment": 1,
        "generation_overflow_forbidden": True,
        "readback_required": True,
        "rollback_on_readback_failure": True,
        "arbitrary_target_forbidden": True,
    }
    if contract.transition != expected:
        return _issue("invalid_transition_policy", "transition", "Only READY/0 to ACTIVE/1 with readback and rollback is allowed")
    return None


def _status_issue(contract) -> StateTransitionIssue | None:
    if contract.statuses != _STATUSES:
        return _issue("invalid_status_map", "statuses", "State transition statuses must preserve existing values and add 17 through 19")
    if len(set(contract.statuses.values())) != len(contract.statuses):
        return _issue("duplicate_status_value", "statuses", "State transition status values must be unique")
    return None


def _marker_issue(contract) -> StateTransitionIssue | None:
    markers = contract.markers
    if markers.ordered_sequence != _MARKERS:
        return _issue("invalid_marker_order", "markers.ordered_sequence", "State transition markers must use the governed order")
    if markers.required_after != "KOZO_FIRST_CAPABILITY_OK":
        return _issue("invalid_marker_boundary", "markers.required_after", "Second capability must follow first capability success")
    if markers.required_before != "KOZO_RUNTIME_RETURN_OK" or markers.generic_dispatch_marker_repeated:
        return _issue("invalid_marker_boundary", "markers.required_before", "Second capability must precede runtime return without repeating generic dispatch")
    return None


def _failure_issue(contract) -> StateTransitionIssue | None:
    behavior = contract.failure_behavior
    required_true = (
        "success_markers_forbidden_on_failure",
        "unknown_capability_rejected",
        "readback_failure_restores_previous_state",
        "runtime_return_requires_success",
    )
    if any(behavior.get(field) is not True for field in required_true):
        return _issue("invalid_failure_behavior", "failure_behavior", "Failure behavior must exclude success, restore readback failure, and preserve halt convergence")
    if behavior.get("halt_contract") != "contracts/runtime_halt_contract.v0.json":
        return _issue("missing_halt_authority", "failure_behavior.halt_contract", "Runtime halt contract must remain authoritative")
    return None


def _claim_issue(contract) -> StateTransitionIssue | None:
    for non_goal in _NON_GOALS:
        if non_goal not in contract.non_goals:
            return _issue("missing_non_goal", f"non_goals.{non_goal}", f"State transition must preserve non-goal: {non_goal}")
    if "userspace capability access" not in contract.claim_boundary.get("does_not_prove", ()):
        return _issue("invalid_claim_boundary", "claim_boundary.does_not_prove", "Claim boundary must reject userspace capability access")
    if len(contract.required_evidence) < 8:
        return _issue("missing_evidence_requirement", "required_evidence", "State transition contract must declare all evidence categories")
    return None


def _field_tuples(fields) -> tuple[tuple[str, int, int], ...]:
    return tuple((field.name, field.offset_bytes, field.width_bytes) for field in fields)


def _issue(reason: str, field: str, detail: str) -> StateTransitionIssue:
    return StateTransitionIssue(reason, field, detail)


def _failure(issue: StateTransitionIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=RUNTIME_STATE_TRANSITION_CAPABILITY_INVALID,
        detail=issue.detail,
        action="Align the state transition capability contract with its one bounded READY/0 to ACTIVE/1 boundary",
        meta={"reason": issue.reason, "contract_field": issue.contract_field},
    )
