from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness import first_governed_runtime_capability as contract_module
from harness.codes import FIRST_GOVERNED_RUNTIME_CAPABILITY_INVALID, OK
from harness.validator import BaseValidator, ValidationResult

_CONTRACT_PATH = contract_module.CONTRACT_PATH
_REQUEST_FIELDS = (
    ("version", 0, 4),
    ("capability_id", 4, 4),
    ("flags", 8, 4),
    ("reserved", 12, 4),
)
_RESPONSE_FIELDS = (
    ("version", 0, 4),
    ("capability_id", 4, 4),
    ("status", 8, 4),
    ("current_progression_stage", 12, 4),
    ("proven_stage_mask", 16, 8),
    ("boot_memory_region_size", 24, 8),
    ("controlled_loop_iteration_limit", 32, 8),
    ("controlled_loop_final_count", 40, 8),
    ("controlled_loop_accumulator", 48, 8),
    ("reserved", 56, 8),
)
_EXPECTED_VALUES = {
    "status": 0,
    "boot_memory_region_size": 4096,
    "controlled_loop_iteration_limit": 3,
    "controlled_loop_final_count": 3,
    "controlled_loop_accumulator": 6,
    "reserved": 0,
}
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
}
_MARKERS = (
    "KOZO_CAPABILITY_DISPATCH_ENTER",
    "KOZO_RUNTIME_STATUS_QUERY_OK",
    "KOZO_FIRST_CAPABILITY_OK",
)
_NON_GOALS = (
    "userspace execution",
    "public userspace ABI",
    "privilege separation",
    "hardware syscall entry",
    "scheduler behavior",
    "interrupt handling",
    "allocator behavior",
    "Linux compatibility",
    "POSIX compatibility",
    "production readiness",
)


@dataclass(frozen=True)
class FirstCapabilityIssue:
    reason: str
    contract_field: str
    detail: str


class FirstGovernedRuntimeCapabilityValidator(BaseValidator):
    name = "first_governed_runtime_capability"
    subsystem = "first_governed_runtime_capability"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _contract_issue(_CONTRACT_PATH)
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="First governed runtime capability contract defines one bounded runtime status query",
        )


def _contract_issue(path: Path) -> FirstCapabilityIssue | None:
    contract = _load_contract(path)
    if isinstance(contract, FirstCapabilityIssue):
        return contract
    checks = (
        _capability_issue,
        _request_issue,
        _response_issue,
        _status_issue,
        _marker_issue,
        _terminal_issue,
        _authority_issue,
        _claim_issue,
    )
    for check in checks:
        issue = check(contract)
        if issue is not None:
            return issue
    return None


def _load_contract(path: Path):
    if not path.is_file():
        return _issue("missing_contract_file", "contract", f"First capability contract is missing: {path}")
    try:
        return contract_module.load_first_governed_runtime_capability(path)
    except json.JSONDecodeError as exc:
        return _issue("invalid_contract_json", "contract", f"First capability contract is invalid JSON: {exc}")
    except (KeyError, TypeError, ValueError) as exc:
        return _issue("contract_schema_violation", "contract", f"First capability contract schema violation: {exc}")


def _capability_issue(contract) -> FirstCapabilityIssue | None:
    capability = contract.capability
    actual = (
        capability.canonical_name,
        capability.canonical_identifier,
        capability.numeric_identifier,
        capability.stage_id,
        capability.status,
    )
    expected = (
        "RUNTIME_STATUS_QUERY",
        "FIRST_GOVERNED_RUNTIME_CAPABILITY",
        1,
        6,
        "implemented_pending_ci",
    )
    if actual != expected:
        return _issue("invalid_capability_identity", "capability", "Capability identity or local stage status is invalid")
    return None


def _request_issue(contract) -> FirstCapabilityIssue | None:
    request = contract.request
    if (request.version, request.size_bytes, request.alignment_bytes) != (1, 16, 4):
        return _issue("invalid_request_geometry", "request", "Runtime status request must be version 1, 16 bytes, and 4-byte aligned")
    if _field_tuples(request.fields) != _REQUEST_FIELDS:
        return _issue("invalid_request_geometry", "request.fields", "Runtime status request field layout is invalid")
    if request.supported_flags != 0 or request.required_zero_fields != ("flags", "reserved"):
        return _issue("invalid_request_policy", "request.required_zero_fields", "Request flags and reserved fields must be governed as zero")
    return None


def _response_issue(contract) -> FirstCapabilityIssue | None:
    response = contract.response
    if (response.version, response.size_bytes, response.alignment_bytes) != (1, 64, 8):
        return _issue("invalid_response_geometry", "response", "Runtime status response must be version 1, 64 bytes, and 8-byte aligned")
    if _field_tuples(response.fields) != _RESPONSE_FIELDS:
        return _issue("invalid_response_geometry", "response.fields", "Runtime status response field layout is invalid")
    if response.reported_progression_stage != 5 or response.proven_stage_mask != 63:
        return _issue("invalid_proven_state", "response.proven_stage_mask", "Response must report only the accepted stage 0 through 5 baseline")
    if response.expected_values != _EXPECTED_VALUES:
        return _issue("invalid_response_values", "response.expected_values", "Runtime status response values are not the governed deterministic values")
    return None


def _status_issue(contract) -> FirstCapabilityIssue | None:
    if contract.statuses != _STATUSES:
        return _issue("invalid_status_map", "statuses", "Capability statuses must preserve the exact deterministic map")
    if len(set(contract.statuses.values())) != len(contract.statuses):
        return _issue("duplicate_status_value", "statuses", "Capability status values must be unique")
    return None


def _marker_issue(contract) -> FirstCapabilityIssue | None:
    markers = contract.markers
    if markers.ordered_sequence != _MARKERS:
        return _issue("invalid_marker_order", "markers.ordered_sequence", "Capability markers must use the governed order")
    if markers.required_after != "KOZO_RUNTIME_LOOP_EXIT_OK":
        return _issue("invalid_marker_boundary", "markers.required_after", "Capability dispatch must follow controlled loop success")
    if markers.required_before != "KOZO_RUNTIME_RETURN_OK":
        return _issue("invalid_marker_boundary", "markers.required_before", "Capability completion must precede runtime return")
    return None


def _terminal_issue(contract) -> FirstCapabilityIssue | None:
    terminal = contract.terminal_behavior
    if terminal.get("required_return_status") != 0:
        return _issue("invalid_terminal_status", "terminal_behavior.required_return_status", "Runtime return requires exact status zero")
    if terminal.get("fallthrough_forbidden") is not True:
        return _issue("fallthrough_allowed", "terminal_behavior.fallthrough_forbidden", "Capability continuation must preserve non-fallthrough halt behavior")
    return None


def _authority_issue(contract) -> FirstCapabilityIssue | None:
    owner = "first_governed_runtime_capability contract owns the CONTROLLED_RUNTIME_LOOP to FIRST_GOVERNED_RUNTIME_CAPABILITY proof boundary"
    if owner not in contract.transition_ownership:
        return _issue("missing_transition_owner", "transition_ownership", "First capability transition requires one explicit owner")
    if len(contract.required_evidence) < 7:
        return _issue("missing_evidence_requirement", "required_evidence", "First capability contract must declare all evidence categories")
    return None


def _claim_issue(contract) -> FirstCapabilityIssue | None:
    for non_goal in _NON_GOALS:
        if non_goal not in contract.non_goals:
            return _issue("missing_non_goal", f"non_goals.{non_goal}", f"First capability must preserve non-goal: {non_goal}")
    if "userspace capability access" not in contract.claim_boundary.get("does_not_prove", ()):
        return _issue("invalid_claim_boundary", "claim_boundary.does_not_prove", "Claim boundary must reject userspace capability access")
    return None


def _field_tuples(fields) -> tuple[tuple[str, int, int], ...]:
    return tuple((field.name, field.offset_bytes, field.width_bytes) for field in fields)


def _issue(reason: str, field: str, detail: str) -> FirstCapabilityIssue:
    return FirstCapabilityIssue(reason, field, detail)


def _failure(issue: FirstCapabilityIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=FIRST_GOVERNED_RUNTIME_CAPABILITY_INVALID,
        detail=issue.detail,
        action="Align the first governed runtime capability contract with its bounded request and response boundary",
        meta={"reason": issue.reason, "contract_field": issue.contract_field},
    )
