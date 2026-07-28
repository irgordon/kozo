from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness import bounded_user_response_consumption_contract as contract_module
from harness.codes import BOUNDED_USER_RESPONSE_CONSUMPTION_CONTRACT_INVALID, OK
from harness.validator import BaseValidator, ValidationResult

_CONTRACT_PATH = contract_module.CONTRACT_PATH
_MARKERS = (
    "KOZO_RUNTIME_LOOP_EXIT_OK",
    "KOZO_USER_RESPONSE_COPY_OUT_OK",
    "KOZO_RING3_RESPONSE_RESUME",
    "KOZO_USER_RESPONSE_CONSUMED_OK",
    "KOZO_FIXED_USER_RESPONSE_OK",
    "KOZO_FIXED_USER_REQUEST_OK",
    "KOZO_RING3_PROBE_OK",
    "KOZO_RING0_RETURN_OK",
    "KOZO_CAPABILITY_DISPATCH_ENTER",
)
_RECORD_FIELDS = (
    ("version", 0, 4),
    ("record_id", 4, 4),
    ("record_size", 8, 4),
    ("validation_status", 12, 4),
    ("sequence", 16, 8),
    ("selected_status_value", 24, 8),
    ("response_digest", 32, 8),
    ("reserved", 40, 8),
)
_STATUSES = {
    "success": 0,
    "phase_invalid": 18,
    "resume_frame_invalid": 19,
    "span_invalid": 20,
    "content_invalid": 21,
    "record_copy_failed": 22,
    "record_invalid": 23,
    "clear_failed": 24,
    "continuation_invalid": 25,
}
_NON_GOALS = (
    "persistent Ring3 execution",
    "multiple request transactions",
    "general syscall ABI",
    "user-provided pointers",
    "user-provided lengths",
    "general copy_from_user",
    "general copy_to_user",
    "process model behavior",
    "scheduler behavior",
    "Linux compatibility",
    "POSIX compatibility",
    "production readiness",
)


@dataclass(frozen=True)
class BoundedUserResponseContractIssue:
    reason: str
    contract_field: str
    detail: str


class BoundedUserResponseConsumptionContractValidator(BaseValidator):
    name = "bounded_user_response_consumption_contract"
    subsystem = "bounded_user_response_consumption_contract"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _contract_issue(_CONTRACT_PATH)
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Bounded user response consumption contract governs one fixed resume and second gate",
        )


def _contract_issue(path: Path) -> BoundedUserResponseContractIssue | None:
    contract = _load_contract(path)
    if isinstance(contract, BoundedUserResponseContractIssue):
        return contract
    for check in (
        _execution_issue,
        _phase_issue,
        _consumer_issue,
        _geometry_issue,
        _shadow_issue,
        _validation_issue,
        _copy_clear_issue,
        _marker_status_issue,
        _halt_claim_issue,
    ):
        issue = check(contract)
        if issue is not None:
            return issue
    return None


def _load_contract(path: Path):
    if not path.is_file():
        return _issue("missing_contract_file", "contract", f"Response consumption contract is missing: {path}")
    try:
        return contract_module.load_bounded_user_response_consumption_contract(path)
    except json.JSONDecodeError as exc:
        return _issue("invalid_contract_json", "contract", f"Response consumption contract is invalid JSON: {exc}")
    except (KeyError, TypeError, ValueError) as exc:
        return _issue("contract_schema_violation", "contract", f"Response consumption schema violation: {exc}")


def _execution_issue(contract) -> BoundedUserResponseContractIssue | None:
    expected = {
        "after_marker": "KOZO_USER_RESPONSE_COPY_OUT_OK",
        "before_marker": "KOZO_FIXED_USER_REQUEST_OK",
        "return_vector": "0x81",
        "ring3_resume_count": 1,
        "second_gate_count": 1,
        "terminal_continuation": "privilege_ring0_continuation",
        "continuation_owner": "active_odin_call_frame",
    }
    if contract.execution_point != expected:
        return _issue("invalid_execution_point", "execution_point", "Consumption must use one fixed resume, second int 0x81, and fixed continuation")
    return None


def _phase_issue(contract) -> BoundedUserResponseContractIssue | None:
    expected = {
        "owner": "kernel",
        "storage_symbol": "fixed_user_transaction_phase",
        "storage_end_symbol": "fixed_user_transaction_phase_end",
        "size_bytes": 8,
        "alignment_bytes": 8,
        "request_pending": 0,
        "response_ready": 1,
        "consumed": 2,
        "user_accessible": False,
    }
    if contract.transaction_phases != expected:
        return _issue("invalid_phase_values", "transaction_phases", "Kernel phase must be the fixed 0 to 1 to 2 transaction")
    return None


def _consumer_issue(contract) -> BoundedUserResponseContractIssue | None:
    consumer = contract.response_consumer
    expected = {
        "start_symbol": "user_response_consumer_start",
        "interrupt_return_symbol": "user_response_consumer_interrupt_return",
        "end_symbol": "user_response_consumer_end",
        "virtual_address_rule": "USER_PROBE_CODE_VA + linked_symbol_offset",
        "fixed_user_rsp": "0x0000400000002ff0",
        "user_code_selector": "0x23",
        "user_data_selector": "0x1b",
        "sanitized_rflags": "0x2",
        "resume_instruction": "iretq",
        "gate_instruction": "int 0x81",
        "unexpected_return_instruction": "ud2",
    }
    if consumer != expected:
        return _issue("invalid_response_consumer", "response_consumer", "Response consumer RIP, RSP, selectors, flags, and instructions must remain fixed")
    return None


def _geometry_issue(contract) -> BoundedUserResponseContractIssue | None:
    response = contract.response
    record = contract.consumption_record
    response_values = (
        response.get("virtual_address"),
        response.get("size_bytes"),
        response.get("alignment_bytes"),
        response.get("physical_backing_symbol"),
    )
    if response_values != ("0x0000400000001080", 88, 8, "user_probe_data_start"):
        return _issue("invalid_response_geometry", "response", "Accepted response geometry must remain fixed")
    record_values = (
        record.get("page_offset"),
        record.get("size_bytes"),
        record.get("alignment_bytes"),
        record.get("physical_backing_symbol"),
    )
    if record_values != (256, 48, 8, "user_probe_data_start"):
        return _issue("invalid_record_geometry", "consumption_record", "Consumption record must be the fixed 48-byte span at page offset 0x100")
    if _field_layout(record.get("fields")) != _RECORD_FIELDS:
        return _issue("invalid_record_geometry", "consumption_record.fields", "Consumption record fields must occupy the exact 48-byte layout")
    if not _spans_are_valid(contract):
        return _issue("record_overlap", "consumption_record.virtual_address", "Request, response, and record spans must be disjoint inside the fixed user-data page")
    if record.get("virtual_address") != "0x0000400000001100":
        return _issue("invalid_record_geometry", "consumption_record.virtual_address", "Consumption record address must remain fixed")
    return None


def _shadow_issue(contract) -> BoundedUserResponseContractIssue | None:
    shadow = contract.kernel_shadow
    geometry = (
        shadow.get("start_symbol"),
        shadow.get("end_symbol"),
        shadow.get("size_bytes"),
        shadow.get("alignment_bytes"),
    )
    if geometry != ("fixed_user_consumption_shadow", "fixed_user_consumption_shadow_end", 48, 8):
        return _issue("invalid_shadow_geometry", "kernel_shadow", "Consumption shadow must remain fixed at 48 aligned bytes")
    if shadow.get("user_accessible") is not False or shadow.get("writable") is not True or shadow.get("executable") is not False:
        return _issue("invalid_shadow_policy", "kernel_shadow", "Consumption shadow must remain supervisor RW-NX")
    return None


def _validation_issue(contract) -> BoundedUserResponseContractIssue | None:
    required_checks = {
        "CPL equals 3",
        "fixed user RSP matches",
        "bounded stack sentinel survives",
        "version matches",
        "request ID matches",
        "status matches",
        "response size matches",
        "sequence matches",
        "current runtime stage matches",
        "proven stage mask matches",
        "boot memory region size matches",
        "controlled loop iteration limit matches",
        "controlled loop final count matches",
        "controlled loop final accumulator matches",
        "feature mask matches",
        "reserved fields are zero",
    }
    if set(contract.ring3_response_checks) != required_checks:
        return _issue("missing_ring3_response_check", "ring3_response_checks", "Ring3 must validate CPL, stack, and every response field")
    if not _all_true(contract.second_frame_validation):
        return _issue("missing_second_frame_validation", "second_frame_validation", "Second saved CPL3 frame validation is mandatory")
    if not _all_true(contract.response_revalidation):
        return _issue("missing_response_revalidation", "response_revalidation", "Ring0 must revalidate span, mapping, backing, qwords, and response semantics")
    return None


def _copy_clear_issue(contract) -> BoundedUserResponseContractIssue | None:
    copy = contract.record_copy
    required_copy = (
        copy.get("source_fixed") is True
        and copy.get("destination_fixed") is True
        and copy.get("user_supplied_pointer") is False
        and copy.get("user_supplied_length") is False
        and copy.get("copy_size_bytes") == 48
        and copy.get("complete_copy_before_validation") is True
    )
    if not required_copy:
        return _issue("invalid_record_copy", "record_copy", "Record copy must move exactly 48 bytes between fixed spans before validation")
    clear_sizes = (
        contract.clearing.get("user_response_bytes"),
        contract.clearing.get("user_record_bytes"),
        contract.clearing.get("kernel_response_shadow_bytes"),
        contract.clearing.get("kernel_consumption_shadow_bytes"),
        contract.clearing.get("kernel_verify_bytes"),
    )
    if clear_sizes != (88, 48, 88, 48, 88) or contract.clearing.get("zero_readback_required") is not True:
        return _issue("missing_clearing_policy", "clearing", "Every response-stage buffer requires exact clearing and zero readback")
    expected_reset = {
        "required_before_odin": False,
        "required_before_return_to_odin": True,
        "reset_value": 0,
        "readback_required": True,
    }
    if contract.phase_reset != expected_reset:
        return _issue("missing_phase_reset", "phase_reset", "Phase must reset before returning to active Odin")
    return None


def _marker_status_issue(contract) -> BoundedUserResponseContractIssue | None:
    if contract.marker_order != _MARKERS:
        return _issue("invalid_marker_order", "marker_order", "Response-consumption markers must match the governed order")
    expected_owners = {
        "KOZO_RING3_RESPONSE_RESUME",
        "KOZO_USER_RESPONSE_CONSUMED_OK",
        "KOZO_FIXED_USER_RESPONSE_OK",
    }
    if set(contract.marker_ownership) != expected_owners:
        return _issue("invalid_marker_ownership", "marker_ownership", "Each new success marker must have one Ring0 owner")
    if contract.failure_statuses != _STATUSES:
        return _issue("invalid_failure_status", "failure_statuses", "Response-consumption statuses must use the exact 18 through 25 range")
    return None


def _halt_claim_issue(contract) -> BoundedUserResponseContractIssue | None:
    halt = contract.halt_behavior
    if halt.get("failure_target") != "boot_terminal_halt" or halt.get("terminal_halt_remains_authoritative") is not True:
        return _issue("invalid_halt_behavior", "halt_behavior", "All failures must converge on the existing terminal halt")
    for value in _NON_GOALS:
        if value not in contract.non_goals:
            return _issue("missing_non_goal", f"non_goals.{value}", f"Response contract must retain non-goal: {value}")
    if "safe execution of arbitrary hostile user code" not in contract.claim_boundary.get("does_not_prove", ()):
        return _issue("claim_boundary_too_broad", "claim_boundary.does_not_prove", "The contract must exclude arbitrary hostile user-code safety")
    return None


def _spans_are_valid(contract) -> bool:
    request_start, request_size = 0x0000400000001000, 40
    response_start = int(contract.response["virtual_address"], 16)
    response_end = response_start + contract.response["size_bytes"]
    record_start = int(contract.consumption_record["virtual_address"], 16)
    record_end = record_start + contract.consumption_record["size_bytes"]
    return (
        request_start + request_size <= response_start
        and response_end <= record_start
        and record_end <= 0x0000400000002000
    )


def _field_layout(value) -> tuple[tuple[str, int, int], ...]:
    if not isinstance(value, list):
        return ()
    return tuple(
        (field.get("name"), field.get("offset"), field.get("size"))
        for field in value
        if isinstance(field, dict)
    )


def _all_true(value) -> bool:
    return isinstance(value, dict) and value and all(item is True for item in value.values())


def _issue(reason: str, field: str, detail: str) -> BoundedUserResponseContractIssue:
    return BoundedUserResponseContractIssue(reason, field, detail)


def _failure(issue: BoundedUserResponseContractIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=BOUNDED_USER_RESPONSE_CONSUMPTION_CONTRACT_INVALID,
        detail=issue.detail,
        action="Align the bounded response-consumption contract with the fixed two-stage transaction",
        meta={"reason": issue.reason, "contract_field": issue.contract_field},
    )
