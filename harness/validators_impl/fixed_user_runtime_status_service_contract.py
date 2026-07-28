from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness import fixed_user_runtime_status_service_contract as contract_module
from harness.codes import FIXED_USER_RUNTIME_STATUS_SERVICE_CONTRACT_INVALID, OK
from harness.validator import BaseValidator, ValidationResult

_CONTRACT_PATH = contract_module.CONTRACT_PATH
_SNAPSHOT_FIELDS = (
    ("current_runtime_stage", 0, 4),
    ("reserved_0", 4, 4),
    ("proven_stage_mask", 8, 8),
    ("boot_memory_region_size", 16, 8),
    ("controlled_loop_iteration_limit", 24, 8),
    ("controlled_loop_final_count", 32, 8),
    ("controlled_loop_final_accumulator", 40, 8),
    ("feature_mask", 48, 8),
    ("reserved_1", 56, 8),
)
_RESPONSE_FIELDS = (
    ("version", 0, 4),
    ("request_id", 4, 4),
    ("status", 8, 4),
    ("response_size", 12, 4),
    ("sequence", 16, 8),
    ("current_runtime_stage", 24, 4),
    ("reserved_0", 28, 4),
    ("proven_stage_mask", 32, 8),
    ("boot_memory_region_size", 40, 8),
    ("controlled_loop_iteration_limit", 48, 8),
    ("controlled_loop_final_count", 56, 8),
    ("controlled_loop_final_accumulator", 64, 8),
    ("feature_mask", 72, 8),
    ("reserved_1", 80, 8),
)
_FEATURE_BITS = (
    (0, "fixed_user_mappings_proven"),
    (1, "cpu_extended_state_proven"),
    (2, "bounded_ring3_transition_proven"),
    (3, "fixed_user_request_boundary_proven"),
    (4, "bounded_response_consumption_proven"),
    (5, "first_internal_runtime_capability_proven"),
    (6, "second_internal_runtime_capability_proven"),
)
_MARKERS = (
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
_NON_GOALS = (
    "pre-runtime status service",
    "general user service dispatcher",
    "public syscall ABI",
    "user-provided pointers",
    "user-provided lengths",
    "persistent Ring3 execution",
    "process model behavior",
    "scheduler behavior",
    "Linux compatibility",
    "POSIX compatibility",
    "production readiness",
)


@dataclass(frozen=True)
class FixedUserRuntimeStatusContractIssue:
    reason: str
    contract_field: str
    detail: str


class FixedUserRuntimeStatusServiceContractValidator(BaseValidator):
    name = "fixed_user_runtime_status_service_contract"
    subsystem = "fixed_user_runtime_status_service_contract"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _contract_issue(_CONTRACT_PATH)
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Fixed user runtime status service contract preserves post-loop ordering and one shared status source",
        )


def _contract_issue(path: Path) -> FixedUserRuntimeStatusContractIssue | None:
    contract = _load_contract(path)
    if isinstance(contract, FixedUserRuntimeStatusContractIssue):
        return contract
    for check in (
        _ordering_issue,
        _shared_status_issue,
        _request_issue,
        _response_issue,
        _feature_issue,
        _validation_issue,
        _cleanup_issue,
        _marker_issue,
        _failure_issue,
        _claim_issue,
    ):
        issue = check(contract)
        if issue is not None:
            return issue
    return None


def _load_contract(path: Path):
    if not path.is_file():
        return _issue("missing_contract_file", "contract", f"Runtime status service contract is missing: {path}")
    try:
        return contract_module.load_fixed_user_runtime_status_service_contract(path)
    except json.JSONDecodeError as exc:
        return _issue("invalid_contract_json", "contract", f"Runtime status service contract is invalid JSON: {exc}")
    except (KeyError, TypeError, ValueError) as exc:
        return _issue("contract_schema_violation", "contract", f"Runtime status service schema violation: {exc}")


def _ordering_issue(contract) -> FixedUserRuntimeStatusContractIssue | None:
    expected = {
        "boot_prepares_privilege_state": True,
        "boot_executes_transaction": False,
        "runtime_entry_symbol": "runtime_progression_entry",
        "runtime_bridge_symbol": "execute_fixed_user_runtime_status_transaction",
        "required_after_marker": "KOZO_RUNTIME_LOOP_EXIT_OK",
        "required_before_marker": "KOZO_CAPABILITY_DISPATCH_ENTER",
        "return_target": "active_odin_call_frame",
        "internal_capabilities_follow_transaction": True,
    }
    if contract.runtime_ordering != expected:
        return _issue("runtime_order_invalid", "runtime_ordering", "The fixed transaction must run after loop completion and return to active Odin")
    return None


def _shared_status_issue(contract) -> FixedUserRuntimeStatusContractIssue | None:
    status = contract.shared_status
    expected = {
        "collector_symbol": "collect_runtime_status",
        "validator_symbol": "validate_runtime_status_snapshot",
        "internal_response_builder": "build_internal_runtime_status_response",
        "user_response_builder": "build_fixed_user_runtime_status_response",
        "snapshot_symbol": "runtime_status_snapshot",
        "snapshot_size_bytes": 64,
        "snapshot_alignment_bytes": 8,
        "ownership": "kernel_runtime",
        "user_accessible": False,
        "writable": True,
        "executable": False,
        "collected_after_loop": True,
        "used_by_user_transaction": True,
        "used_by_internal_capability_1": True,
        "cleared_after_internal_capability_1": True,
    }
    for field, value in expected.items():
        if status.get(field) != value:
            return _issue("shared_status_invalid", f"shared_status.{field}", f"Shared status {field} must be {value!r}")
    if _field_layout(status.get("fields")) != _SNAPSHOT_FIELDS:
        return _issue("snapshot_geometry_invalid", "shared_status.fields", "Runtime status snapshot must use the exact 64-byte layout")
    expected_values = {
        "current_runtime_stage": 5,
        "proven_stage_mask": 63,
        "boot_memory_region_size": 4096,
        "controlled_loop_iteration_limit": 3,
        "controlled_loop_final_count": 3,
        "controlled_loop_final_accumulator": 6,
        "feature_mask": 127,
        "reserved_0": 0,
        "reserved_1": 0,
    }
    if status.get("expected_values") != expected_values:
        return _issue("snapshot_values_invalid", "shared_status.expected_values", "Runtime status snapshot must report only the accepted post-loop values")
    return None


def _request_issue(contract) -> FixedUserRuntimeStatusContractIssue | None:
    expected = {
        "name": "FIXED_USER_RUNTIME_STATUS_REQUEST",
        "identifier": 2,
        "version": 1,
        "virtual_address": "0x0000400000001000",
        "size_bytes": 40,
        "response_size_bytes": 88,
        "sequence": 1,
        "payload": 0,
        "flags": 0,
        "reserved": 0,
    }
    if contract.request != expected:
        return _issue("request_identity_invalid", "request", "The user status service must use one fixed ID 2 request with zero payload")
    return None


def _response_issue(contract) -> FixedUserRuntimeStatusContractIssue | None:
    response = contract.response
    if (
        response.get("name") != "FIXED_USER_RUNTIME_STATUS_RESPONSE"
        or response.get("virtual_address") != "0x0000400000001080"
        or response.get("size_bytes") != 88
        or response.get("alignment_bytes") != 8
    ):
        return _issue("response_geometry_invalid", "response", "The user status response must remain fixed at 88 aligned bytes")
    if _field_layout(response.get("fields")) != _RESPONSE_FIELDS:
        return _issue("response_geometry_invalid", "response.fields", "The user response must use the exact 88-byte field layout")
    return None


def _feature_issue(contract) -> FixedUserRuntimeStatusContractIssue | None:
    actual = tuple((item.get("bit"), item.get("name")) for item in contract.feature_mask_bits)
    if actual != _FEATURE_BITS:
        return _issue("feature_mask_invalid", "feature_mask_bits", "Feature bits 0 through 6 must be unique and authoritative")
    return None


def _validation_issue(contract) -> FixedUserRuntimeStatusContractIssue | None:
    ring3 = contract.ring3_validation
    if (
        ring3.get("all_response_fields_required") is not True
        or ring3.get("expected_values_from_contract") is not True
        or ring3.get("expected_values_from_user_memory") is not False
        or ring3.get("consumption_record_size_bytes") != 48
        or ring3.get("selected_status_value") != "proven_stage_mask"
        or ring3.get("digest_operation") != "xor_all_eleven_response_qwords"
    ):
        return _issue("ring3_validation_invalid", "ring3_validation", "Ring3 must validate all fields and digest all eleven response qwords")
    ring0 = contract.ring0_revalidation
    if not all(ring0.get(field) is True for field in (
        "complete_response_shadow_comparison",
        "all_response_fields_required",
        "consumption_record_required",
        "digest_revalidation_required",
    )):
        return _issue("ring0_revalidation_invalid", "ring0_revalidation", "Ring0 must revalidate the full response and consumption record")
    return None


def _cleanup_issue(contract) -> FixedUserRuntimeStatusContractIssue | None:
    if not all(contract.cleanup.get(field) is True for field in (
        "transaction_buffers_cleared_before_return_to_odin",
        "transaction_phase_reset_before_return_to_odin",
        "snapshot_preserved_for_internal_capability_1",
        "snapshot_cleared_after_internal_capability_1",
        "zero_readback_required",
    )):
        return _issue("cleanup_invalid", "cleanup", "Transaction buffers and shared snapshot must follow the governed lifetime")
    return None


def _marker_issue(contract) -> FixedUserRuntimeStatusContractIssue | None:
    if contract.marker_order != _MARKERS:
        return _issue("marker_order_invalid", "marker_order", "Runtime status markers must follow loop exit and precede capability dispatch")
    return None


def _failure_issue(contract) -> FixedUserRuntimeStatusContractIssue | None:
    if not all(contract.failure_behavior.get(field) is True for field in (
        "unknown_status_forbidden",
        "later_success_markers_forbidden",
        "internal_capabilities_forbidden_after_transaction_failure",
        "runtime_return_forbidden_after_transaction_failure",
        "terminal_halt_remains_authoritative",
    )):
        return _issue("failure_behavior_invalid", "failure_behavior", "Transaction failures must prevent capabilities and runtime return")
    return None


def _claim_issue(contract) -> FixedUserRuntimeStatusContractIssue | None:
    if not contract.claim_boundary.get("proves") or not contract.claim_boundary.get("does_not_prove"):
        return _issue("missing_claim_boundary", "claim_boundary", "The contract must separate proven and unproven behavior")
    missing = tuple(goal for goal in _NON_GOALS if goal not in contract.non_goals)
    if missing:
        return _issue("missing_non_goal", f"non_goals.{missing[0]}", f"Missing non-goal: {missing[0]}")
    return None


def _field_layout(fields) -> tuple[tuple[str, int, int], ...]:
    if not isinstance(fields, list):
        return ()
    return tuple((field.get("name"), field.get("offset"), field.get("size")) for field in fields)


def _issue(reason: str, contract_field: str, detail: str) -> FixedUserRuntimeStatusContractIssue:
    return FixedUserRuntimeStatusContractIssue(reason, contract_field, detail)


def _failure(issue: FixedUserRuntimeStatusContractIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=FIXED_USER_RUNTIME_STATUS_SERVICE_CONTRACT_INVALID,
        detail=issue.detail,
        action="Restore the fixed post-loop status-service contract and its shared snapshot boundary",
        meta={"reason": issue.reason, "contract_field": issue.contract_field},
    )
