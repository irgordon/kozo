from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness import bounded_privilege_transition_probe_contract as contract_module
from harness.codes import BOUNDED_PRIVILEGE_TRANSITION_PROBE_CONTRACT_INVALID, OK
from harness.validator import BaseValidator, ValidationResult

_CONTRACT_PATH = contract_module.CONTRACT_PATH
_SELECTORS = {
    "kernel_code": "0x08",
    "kernel_data": "0x10",
    "user_data": "0x1b",
    "user_code": "0x23",
    "tss": "0x28",
}
_MARKERS = (
    "KOZO_PRIVILEGE_TRANSITION_INIT_START",
    "KOZO_PRIVILEGE_TABLES_OK",
    "KOZO_RUNTIME_LOOP_EXIT_OK",
    "KOZO_RING3_ENTER",
    "KOZO_RING3_PROBE_OK",
    "KOZO_RING0_RETURN_OK",
    "KOZO_CAPABILITY_DISPATCH_ENTER",
)
_STATUSES = {
    "success": 0,
    "gdt_invalid": 1,
    "tss_invalid": 2,
    "idt_invalid": 3,
    "user_entry_invalid": 4,
    "user_stack_invalid": 5,
    "return_frame_invalid": 6,
    "user_probe_failed": 7,
    "ring0_continuation_failed": 8,
}
_NON_GOALS = (
    "general userspace execution",
    "process isolation",
    "scheduler behavior",
    "return to Ring 3",
    "public syscall ABI",
    "system-call dispatch",
    "exception recovery",
    "general virtual memory management",
    "interrupt subsystem",
    "Linux compatibility",
    "POSIX compatibility",
    "production readiness",
)


@dataclass(frozen=True)
class BoundedPrivilegeTransitionContractIssue:
    reason: str
    contract_field: str
    detail: str


class BoundedPrivilegeTransitionProbeContractValidator(BaseValidator):
    name = "bounded_privilege_transition_probe_contract"
    subsystem = "bounded_privilege_transition_probe_contract"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _contract_issue(_CONTRACT_PATH)
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Bounded privilege-transition contract governs one fixed CPL3 excursion",
        )


def _contract_issue(path: Path) -> BoundedPrivilegeTransitionContractIssue | None:
    contract = _load_contract(path)
    if isinstance(contract, BoundedPrivilegeTransitionContractIssue):
        return contract
    checks = (
        _transition_issue,
        _selector_issue,
        _table_issue,
        _stack_issue,
        _entry_issue,
        _probe_issue,
        _return_issue,
        _marker_status_issue,
        _claim_issue,
    )
    for check in checks:
        issue = check(contract)
        if issue is not None:
            return issue
    return None


def _load_contract(path: Path):
    if not path.is_file():
        return _issue("missing_contract_file", "contract", f"Privilege-transition contract is missing: {path}")
    try:
        return contract_module.load_bounded_privilege_transition_probe_contract(path)
    except json.JSONDecodeError as exc:
        return _issue("invalid_contract_json", "contract", f"Privilege-transition contract is invalid JSON: {exc}")
    except (KeyError, TypeError, ValueError) as exc:
        return _issue("contract_schema_violation", "contract", f"Privilege-transition schema violation: {exc}")


def _transition_issue(contract) -> BoundedPrivilegeTransitionContractIssue | None:
    expected = {
        "entry_privilege": 0,
        "target_privilege": 3,
        "entry_mechanism": "iretq",
        "return_mechanism": "int_0x81_interrupt_gate",
        "returns_to_user": False,
        "interrupts_enabled": False,
    }
    if contract.transition != expected:
        return _issue("invalid_transition_mechanism", "transition", "Transition must use one iretq entry and int 0x81 return with interrupts disabled")
    return None


def _selector_issue(contract) -> BoundedPrivilegeTransitionContractIssue | None:
    if contract.selectors != _SELECTORS:
        return _issue("invalid_selector", "selectors", "Fixed selectors must match the governed seven-entry GDT")
    return None


def _table_issue(contract) -> BoundedPrivilegeTransitionContractIssue | None:
    if contract.gdt.get("size_bytes") != 56 or contract.gdt.get("entry_count") != 7:
        return _issue("invalid_gdt_geometry", "gdt", "GDT must contain seven fixed entries in 56 bytes")
    if contract.tss.get("size_bytes") != 104 or contract.tss.get("iopb_offset") != 104:
        return _issue("invalid_tss_geometry", "tss", "TSS must be 104 bytes with a disabled I/O bitmap")
    if contract.tss.get("rsp0_symbol") != "privilege_return_stack_top":
        return _issue("invalid_tss_rsp0", "tss.rsp0_symbol", "TSS.RSP0 must own the fixed privilege return stack")
    if contract.idt.get("return_vector") != "0x81" or contract.idt.get("return_gate_dpl") != 3:
        return _issue("invalid_return_gate", "idt", "IDT vector 0x81 must be a fixed DPL3 return gate")
    return None


def _stack_issue(contract) -> BoundedPrivilegeTransitionContractIssue | None:
    for name in ("return", "double_fault", "user"):
        stack = contract.stacks.get(name, {})
        if stack.get("size_bytes") != 4096 or stack.get("alignment_bytes") != 4096:
            return _issue("invalid_stack_geometry", f"stacks.{name}", "Every privilege-transition stack must be one aligned page")
    for name in ("return", "double_fault"):
        stack = contract.stacks[name]
        if stack.get("user") is not False or stack.get("writable") is not True or stack.get("executable") is not False:
            return _issue("invalid_stack_permissions", f"stacks.{name}", "Ring0 stacks must remain supervisor RW-NX")
    if contract.stacks["user"].get("initial_rsp") != "0x0000400000002ff0":
        return _issue("invalid_user_rsp", "stacks.user.initial_rsp", "User RSP must be the fixed aligned in-page value")
    return None


def _entry_issue(contract) -> BoundedPrivilegeTransitionContractIssue | None:
    entry = contract.entry
    if entry.get("fixed_virtual_rip") != "0x0000400000000000":
        return _issue("invalid_user_rip", "entry.fixed_virtual_rip", "Ring3 RIP must be the fixed mapped probe address")
    if not entry.get("cpl_check_required") or not entry.get("mapping_validation_required"):
        return _issue("missing_cpl_validation", "entry", "Ring3 CPL and fixed mapping geometry must be validated")
    if entry.get("sanitized_rflags") != "0x2":
        return _issue("invalid_rflags_policy", "entry.sanitized_rflags", "Ring3 RFLAGS must contain only reserved bit 1")
    if entry.get("code_writable") is not False or entry.get("code_executable") is not True:
        return _issue("invalid_user_code_permissions", "entry", "Fixed user code must remain RX and not writable")
    return None


def _probe_issue(contract) -> BoundedPrivilegeTransitionContractIssue | None:
    probe = contract.probe
    if (
        probe.get("request_identifier") != 2
        or probe.get("request_size_bytes") != 40
        or probe.get("response_size_bytes") != 88
    ):
        return _issue("invalid_probe_width", "probe.response_size_bytes", "The bounded probe must use the fixed ID 2 request and 88-byte response")
    required = (
        "stack_probe_required",
        "runtime_status_response_validation_required",
        "transaction_clear_readback_required",
        "serial_io_forbidden_in_ring3",
    )
    if any(probe.get(field) is not True for field in required):
        return _issue("missing_probe_requirement", "probe", "Stack, data, clear/readback, and serial prohibition must all be governed")
    return None


def _return_issue(contract) -> BoundedPrivilegeTransitionContractIssue | None:
    boundary = contract.return_boundary
    required = (
        "saved_frame_validation_required",
        "kernel_stack_restore_required",
        "returns_to_odin",
        "user_return_forbidden",
        "halt_on_fault_required",
    )
    if any(boundary.get(field) is not True for field in required):
        return _issue("invalid_return_boundary", "return_boundary", "The fixed Ring0 return must validate, restore, and fail closed")
    if boundary.get("fixed_continuation_symbol") != "privilege_ring0_continuation":
        return _issue("invalid_return_target", "return_boundary.fixed_continuation_symbol", "Return target must be the fixed Ring0 continuation")
    if (
        boundary.get("runtime_bridge_symbol") != "execute_fixed_user_runtime_status_transaction"
        or boundary.get("invocation_owner") != "active_odin_runtime_after_controlled_loop"
    ):
        return _issue("invalid_return_target", "return_boundary.runtime_bridge_symbol", "The fixed transition must return through the active Odin bridge")
    return None


def _marker_status_issue(contract) -> BoundedPrivilegeTransitionContractIssue | None:
    if contract.success_markers != _MARKERS:
        return _issue("invalid_marker_order", "success_markers", "Privilege markers must match the governed ordered boundary")
    if contract.failure_statuses != _STATUSES:
        return _issue("invalid_failure_status", "failure_statuses", "Privilege failure statuses must remain exact and contiguous")
    return None


def _claim_issue(contract) -> BoundedPrivilegeTransitionContractIssue | None:
    for value in _NON_GOALS:
        if value not in contract.non_goals:
            return _issue("missing_non_goal", f"non_goals.{value}", f"Privilege contract must retain non-goal: {value}")
    if "general userspace execution" not in contract.claim_boundary.get("does_not_prove", ()):
        return _issue("claim_boundary_too_broad", "claim_boundary.does_not_prove", "The contract must exclude general userspace execution")
    return None


def _issue(reason: str, field: str, detail: str) -> BoundedPrivilegeTransitionContractIssue:
    return BoundedPrivilegeTransitionContractIssue(reason, field, detail)


def _failure(issue: BoundedPrivilegeTransitionContractIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=BOUNDED_PRIVILEGE_TRANSITION_PROBE_CONTRACT_INVALID,
        detail=issue.detail,
        action="Align the bounded privilege-transition contract with the fixed x86_64 round-trip boundary",
        meta={"reason": issue.reason, "contract_field": issue.contract_field},
    )
