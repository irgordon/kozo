from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness import fixed_user_request_boundary_contract as contract_module
from harness.codes import FIXED_USER_REQUEST_BOUNDARY_CONTRACT_INVALID, OK
from harness.validator import BaseValidator, ValidationResult

_CONTRACT_PATH = contract_module.CONTRACT_PATH
_REQUEST_FIELDS = (
    ("version", 0, 4),
    ("request_id", 4, 4),
    ("request_size", 8, 4),
    ("response_size", 12, 4),
    ("sequence", 16, 8),
    ("payload", 24, 8),
    ("flags", 32, 4),
    ("reserved", 36, 4),
)
_RESPONSE_FIELDS = (
    ("version", 0, 4),
    ("request_id", 4, 4),
    ("status", 8, 4),
    ("response_size", 12, 4),
    ("sequence", 16, 8),
    ("echoed_payload", 24, 8),
    ("observed_user_cpl", 32, 4),
    ("observed_kernel_cpl", 36, 4),
    ("response_token", 40, 8),
)
_MARKERS = (
    "KOZO_RING3_ENTER",
    "KOZO_USER_REQUEST_COPY_IN_OK",
    "KOZO_USER_REQUEST_SERVICE_OK",
    "KOZO_USER_RESPONSE_COPY_OUT_OK",
    "KOZO_FIXED_USER_REQUEST_OK",
    "KOZO_RING3_PROBE_OK",
    "KOZO_RING0_RETURN_OK",
    "KOZO_RUNTIME_PROGRESS_ENTRY",
)
_STATUSES = {
    "success": 0,
    "range_invalid": 9,
    "copy_in_failed": 10,
    "request_invalid": 11,
    "service_failed": 12,
    "response_invalid": 13,
    "copy_out_failed": 14,
    "response_readback_failed": 15,
    "buffer_clear_failed": 16,
    "continuation_invalid": 17,
}
_NON_GOALS = (
    "general syscall ABI",
    "user-provided pointers",
    "user-provided lengths",
    "general copy_from_user",
    "general copy_to_user",
    "return to Ring 3",
    "persistent userspace execution",
    "process model behavior",
    "scheduler behavior",
    "Linux compatibility",
    "POSIX compatibility",
    "production readiness",
)


@dataclass(frozen=True)
class FixedUserRequestContractIssue:
    reason: str
    contract_field: str
    detail: str


class FixedUserRequestBoundaryContractValidator(BaseValidator):
    name = "fixed_user_request_boundary_contract"
    subsystem = "fixed_user_request_boundary_contract"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _contract_issue(_CONTRACT_PATH)
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Fixed user request contract governs one exact Ring3-to-Ring0 transaction",
        )


def _contract_issue(path: Path) -> FixedUserRequestContractIssue | None:
    contract = _load_contract(path)
    if isinstance(contract, FixedUserRequestContractIssue):
        return contract
    checks = (
        _execution_issue,
        _request_issue,
        _response_issue,
        _span_issue,
        _shadow_issue,
        _service_issue,
        _copy_issue,
        _permission_issue,
        _clearing_issue,
        _marker_status_issue,
        _halt_claim_issue,
    )
    for check in checks:
        issue = check(contract)
        if issue is not None:
            return issue
    return None


def _load_contract(path: Path):
    if not path.is_file():
        return _issue("missing_contract_file", "contract", f"Fixed user request contract is missing: {path}")
    try:
        return contract_module.load_fixed_user_request_boundary_contract(path)
    except json.JSONDecodeError as exc:
        return _issue("invalid_contract_json", "contract", f"Fixed user request contract is invalid JSON: {exc}")
    except (KeyError, TypeError, ValueError) as exc:
        return _issue("contract_schema_violation", "contract", f"Fixed user request schema violation: {exc}")


def _execution_issue(contract) -> FixedUserRequestContractIssue | None:
    point = contract.execution_point
    expected = {
        "after_marker": "KOZO_RING3_ENTER",
        "before_marker": "KOZO_RING3_PROBE_OK",
        "ring3_symbol": "user_privilege_probe_start",
        "return_handler_symbol": "privilege_return_handler",
        "fixed_continuation_symbol": "privilege_ring0_continuation",
        "return_vector": "0x81",
        "returns_to_ring3": False,
    }
    if point != expected:
        return _issue("invalid_execution_point", "execution_point", "Boundary must use the fixed Ring3 stub, int 0x81 handler, and Ring0 continuation")
    return None


def _request_issue(contract) -> FixedUserRequestContractIssue | None:
    request = contract.request
    expected = {
        "name": "FIXED_USER_BOUNDARY_PROBE",
        "identifier": 1,
        "version": 1,
        "virtual_address": "0x0000400000001000",
        "page_offset": 0,
        "size_bytes": 40,
        "alignment_bytes": 8,
        "physical_backing_symbol": "user_probe_data_start",
        "sequence": 1,
        "payload": "0x4b4f5a4f50524956",
        "flags": 0,
        "reserved": 0,
    }
    for field, value in expected.items():
        if request.get(field) != value:
            return _issue("invalid_request_geometry", f"request.{field}", f"Fixed request {field} must be {value!r}")
    if _field_layout(request.get("fields")) != _REQUEST_FIELDS:
        return _issue("invalid_request_geometry", "request.fields", "Fixed request fields must occupy the exact 40-byte layout")
    return None


def _response_issue(contract) -> FixedUserRequestContractIssue | None:
    response = contract.response
    expected = {
        "version": 1,
        "request_identifier": 1,
        "success_status": 0,
        "virtual_address": "0x0000400000001080",
        "page_offset": 128,
        "size_bytes": 48,
        "alignment_bytes": 8,
        "physical_backing_symbol": "user_probe_data_start",
        "observed_user_cpl": 3,
        "observed_kernel_cpl": 0,
    }
    for field, value in expected.items():
        if response.get(field) != value:
            return _issue("invalid_response_geometry", f"response.{field}", f"Fixed response {field} must be {value!r}")
    if _field_layout(response.get("fields")) != _RESPONSE_FIELDS:
        return _issue("invalid_response_geometry", "response.fields", "Fixed response fields must occupy the exact 48-byte layout")
    return None


def _span_issue(contract) -> FixedUserRequestContractIssue | None:
    try:
        valid = contract_module.fixed_spans_are_valid(contract)
    except (TypeError, ValueError):
        valid = False
    if not valid:
        return _issue("invalid_user_span", "request.response", "Request and response spans must be aligned, non-overlapping, and inside the fixed user-data page")
    return None


def _shadow_issue(contract) -> FixedUserRequestContractIssue | None:
    expected = {
        "request": ("fixed_user_request_shadow", "fixed_user_request_shadow_end", 40),
        "response": ("fixed_user_response_shadow", "fixed_user_response_shadow_end", 48),
        "verify": ("fixed_user_response_verify", "fixed_user_response_verify_end", 48),
    }
    for name, (start, end, size) in expected.items():
        shadow = contract.kernel_shadows.get(name, {})
        values = (shadow.get("start_symbol"), shadow.get("end_symbol"), shadow.get("size_bytes"))
        if values != (start, end, size) or shadow.get("alignment_bytes") != 8:
            return _issue("invalid_shadow_geometry", f"kernel_shadows.{name}", f"{name} shadow geometry must remain fixed")
    policy = contract.kernel_shadows
    if policy.get("user_accessible") is not False or policy.get("writable") is not True or policy.get("executable") is not False:
        return _issue("invalid_shadow_policy", "kernel_shadows", "Kernel shadows must remain supervisor RW-NX")
    return None


def _service_issue(contract) -> FixedUserRequestContractIssue | None:
    service = contract.fixed_service
    if service.get("name") != "FIXED_USER_BOUNDARY_PROBE" or service.get("request_identifier") != 1:
        return _issue("invalid_service_identity", "fixed_service", "Only fixed request service 1 is governed")
    if service.get("response_token_operation") != "request_payload_xor_fixed_mask":
        return _issue("invalid_response_token_rule", "fixed_service.response_token_operation", "Response token must XOR the request payload with the fixed mask")
    if service.get("response_token_mask") != "0xa5a55a5ac3c33c3c":
        return _issue("invalid_response_token_rule", "fixed_service.response_token_mask", "Response token mask must remain fixed")
    if service.get("reads_user_memory") is not False or service.get("writes_user_memory") is not False:
        return _issue("service_crosses_copy_boundary", "fixed_service", "The fixed service must consume and produce only kernel-owned shadows")
    return None


def _copy_issue(contract) -> FixedUserRequestContractIssue | None:
    boundary = contract.copy_boundary
    required_true = (
        "saved_frame_validation_before_copy_in",
        "complete_span_validation_before_access",
        "request_source_fixed",
        "request_destination_fixed",
        "response_source_fixed",
        "response_destination_fixed",
        "copy_out_readback_required",
        "request_response_non_overlap_required",
        "overflow_safe_range_validation_required",
    )
    if any(boundary.get(field) is not True for field in required_true):
        return _issue("missing_copy_requirement", "copy_boundary", "Frame, span, fixed-copy, readback, overlap, and overflow checks are mandatory")
    if boundary.get("user_supplied_pointer") is not False or boundary.get("user_supplied_length") is not False:
        return _issue("caller_controlled_copy", "copy_boundary", "No user-provided pointer or length is accepted")
    if boundary.get("copy_in_size_bytes") != 40 or boundary.get("copy_out_size_bytes") != 48:
        return _issue("invalid_copy_size", "copy_boundary", "Copy-in and copy-out sizes must be exactly 40 and 48 bytes")
    return None


def _permission_issue(contract) -> FixedUserRequestContractIssue | None:
    policy = contract.page_permissions
    expected = {
        "page_start": "0x0000400000001000",
        "page_end": "0x0000400000002000",
        "present": True,
        "user": True,
        "writable": True,
        "executable": False,
        "physical_backing_symbol": "user_probe_data_start",
        "software_walk_required": True,
    }
    if policy != expected:
        return _issue("invalid_page_policy", "page_permissions", "The complete boundary must remain in the fixed user RW-NX data page")
    return None


def _clearing_issue(contract) -> FixedUserRequestContractIssue | None:
    clearing = contract.buffer_clearing
    expected_sizes = {
        "user_request_clear_size_bytes": 40,
        "user_response_clear_size_bytes": 48,
        "kernel_request_shadow_clear_size_bytes": 40,
        "kernel_response_shadow_clear_size_bytes": 48,
        "kernel_verify_clear_size_bytes": 48,
    }
    if clearing.get("before_ring3_entry") is not True or clearing.get("after_copy_out_validation") is not True:
        return _issue("missing_buffer_clear", "buffer_clearing", "Boundary buffers must be cleared before entry and after validated copy-out")
    if clearing.get("zero_readback_required") is not True:
        return _issue("missing_buffer_clear_readback", "buffer_clearing.zero_readback_required", "Buffer clearing requires zero readback")
    for field, size in expected_sizes.items():
        if clearing.get(field) != size:
            return _issue("invalid_clear_size", f"buffer_clearing.{field}", f"{field} must be exactly {size} bytes")
    return None


def _marker_status_issue(contract) -> FixedUserRequestContractIssue | None:
    if contract.marker_order != _MARKERS:
        return _issue("invalid_marker_order", "marker_order", "Fixed request markers must match the governed boundary order")
    if set(contract.marker_ownership) != set(_MARKERS[1:5]):
        return _issue("invalid_marker_ownership", "marker_ownership", "Each fixed-request success marker must have one Ring0 owner")
    if contract.failure_statuses != _STATUSES:
        return _issue("invalid_failure_status", "failure_statuses", "Fixed request failure statuses must remain exact")
    return None


def _halt_claim_issue(contract) -> FixedUserRequestContractIssue | None:
    halt = contract.halt_behavior
    if halt.get("failure_target") != "boot_terminal_halt" or halt.get("terminal_halt_remains_authoritative") is not True:
        return _issue("invalid_halt_behavior", "halt_behavior", "All failures must converge on the existing terminal halt")
    for value in _NON_GOALS:
        if value not in contract.non_goals:
            return _issue("missing_non_goal", f"non_goals.{value}", f"Fixed request contract must retain non-goal: {value}")
    does_not_prove = contract.claim_boundary.get("does_not_prove", ())
    if "safe execution of arbitrary hostile user code" not in does_not_prove:
        return _issue("claim_boundary_too_broad", "claim_boundary.does_not_prove", "The contract must exclude arbitrary hostile user-code safety")
    return None


def _field_layout(value) -> tuple[tuple[str, int, int], ...]:
    if not isinstance(value, list):
        return ()
    return tuple(
        (field.get("name"), field.get("offset"), field.get("size"))
        for field in value
        if isinstance(field, dict)
    )


def _issue(reason: str, field: str, detail: str) -> FixedUserRequestContractIssue:
    return FixedUserRequestContractIssue(reason, field, detail)


def _failure(issue: FixedUserRequestContractIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=FIXED_USER_REQUEST_BOUNDARY_CONTRACT_INVALID,
        detail=issue.detail,
        action="Align the fixed user request contract with the one-shot Ring3 request boundary",
        meta={"reason": issue.reason, "contract_field": issue.contract_field},
    )
