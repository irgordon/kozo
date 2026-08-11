from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness import fixed_user_execution_context_contract as contract_module
from harness.abi_manifest import ROOT
from harness.codes import FIXED_USER_EXECUTION_CONTEXT_CONTRACT_INVALID, OK
from harness.validator import BaseValidator, ValidationResult

_CONTRACT_PATH = contract_module.CONTRACT_PATH
_CONTRACT_REFERENCE = "contracts/fixed_user_execution_context_contract.v0.json"
_ADR_PATH = ROOT / "docs" / "adr" / "0018-fixed-user-execution-context-ownership.md"
_PROGRESSION_PATH = ROOT / "contracts" / "runtime_progression_stages.v0.json"
_CONTEXT_FIELDS = (
    ("format_version", 0, 4, "u32"),
    ("structure_size", 4, 4, "u32"),
    ("opaque_identity", 8, 8, "u64"),
    ("lifecycle", 16, 4, "u32"),
    ("reserved_0", 20, 4, "u32"),
    ("user_code_start", 24, 8, "u64"),
    ("user_code_size", 32, 8, "u64"),
    ("user_data_start", 40, 8, "u64"),
    ("user_data_size", 48, 8, "u64"),
    ("user_stack_start", 56, 8, "u64"),
    ("user_stack_size", 64, 8, "u64"),
    ("user_stack_top", 72, 8, "u64"),
    ("entry_rip", 80, 8, "u64"),
    ("initial_rsp", 88, 8, "u64"),
    ("user_code_selector", 96, 4, "u32"),
    ("user_data_selector", 100, 4, "u32"),
    ("return_vector", 104, 4, "u32"),
    ("authorized_transition_budget", 108, 4, "u32"),
    ("observed_transition_count", 112, 4, "u32"),
    ("transaction_phase", 116, 4, "u32"),
    ("request_identifier", 120, 4, "u32"),
    ("reserved_1", 124, 4, "u32"),
)
_RESULT_FIELDS = (
    ("format_version", 0, 4, "u32"),
    ("structure_size", 4, 4, "u32"),
    ("outcome", 8, 4, "u32"),
    ("failure_code", 12, 4, "u32"),
    ("observed_transition_count", 16, 4, "u32"),
    ("terminal_lifecycle", 20, 4, "u32"),
    ("reserved_0", 24, 8, "u64"),
)
_LIFECYCLE_ENCODINGS = {
    "UNINITIALIZED": 0,
    "READY": 1,
    "ACTIVE": 2,
    "RETURNED": 3,
    "CLEARED": 4,
}
_SUCCESS_EDGES = (
    ("UNINITIALIZED", "READY"),
    ("READY", "ACTIVE"),
    ("ACTIVE", "RETURNED"),
    ("RETURNED", "CLEARED"),
)
_FAILURE_EDGES = (
    ("READY", "CLEARED"),
    ("ACTIVE", "CLEARED"),
    ("RETURNED", "CLEARED"),
)
_FORBIDDEN_EDGES = (
    ("UNINITIALIZED", "ACTIVE"),
    ("UNINITIALIZED", "RETURNED"),
    ("READY", "RETURNED"),
    ("ACTIVE", "READY"),
    ("RETURNED", "ACTIVE"),
    ("CLEARED", "ACTIVE"),
    ("CLEARED", "READY"),
)
_FORBIDDEN_RESULT_FIELDS = frozenset(
    {"opaque_identity", "kernel_pointer", "user_pointer", "selector", "mapping", "reusable_handle"}
)


@dataclass(frozen=True)
class FixedUserExecutionContextIssue:
    reason: str
    contract_field: str
    detail: str


class FixedUserExecutionContextContractValidator(BaseValidator):
    name = "fixed_user_execution_context_contract"
    subsystem = "generic"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _contract_issue(_CONTRACT_PATH)
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Fixed user execution context governance is exact, bounded, and unimplemented",
        )


def _contract_issue(path: Path) -> FixedUserExecutionContextIssue | None:
    contract = _load_contract(path)
    if isinstance(contract, FixedUserExecutionContextIssue):
        return contract
    checks = (
        _authority_issue,
        _context_layout_issue,
        _lifecycle_issue,
        _clear_state_issue,
        _result_issue,
        _binding_issue,
        _source_consistency_issue,
        _transition_budget_issue,
        _progression_issue,
        _evidence_claim_issue,
        _governance_alignment_issue,
    )
    return _first_issue(check(contract) for check in checks)


def _load_contract(path: Path):
    if not path.is_file():
        return _issue("missing_contract_file", "contract", f"Fixed user execution context contract is missing: {path}")
    try:
        return contract_module.load_fixed_user_execution_context_contract(path)
    except json.JSONDecodeError as exc:
        return _issue("invalid_contract_json", "contract", f"Fixed user execution context contract is invalid JSON: {exc}")
    except (KeyError, TypeError, ValueError) as exc:
        return _issue("contract_schema_violation", "contract", f"Fixed user execution context schema violation: {exc}")


def _authority_issue(contract) -> FixedUserExecutionContextIssue | None:
    expected = {
        "owner": "ring0",
        "context_count": 1,
        "allocation": "fixed_static",
        "user_accessible": False,
        "user_selectable_identity": False,
        "user_mutable_authority": False,
        "public_abi": False,
        "implementation_authorized": False,
    }
    if contract.authority != expected:
        return _issue("invalid_authority", "authority", "Exactly one static Ring0-owned internal context is required")
    return None


def _context_layout_issue(contract) -> FixedUserExecutionContextIssue | None:
    context = contract.context
    if (context.get("format_version"), context.get("size_bytes"), context.get("alignment_bytes")) != (1, 128, 16):
        return _issue("invalid_context_geometry", "context", "Context geometry must be version 1, 128 bytes, aligned to 16")
    if _field_layout(context.get("fields")) != _CONTEXT_FIELDS:
        return _issue("invalid_context_geometry", "context.fields", "Context fields must occupy the exact 128-byte layout")
    identity = _named_field(context["fields"], "opaque_identity")
    identity_rule = identity.get("invalid", "")
    identity_valid = identity.get("initial") == 0 and identity.get("cleared") == 0
    identity_valid &= "nonzero" in identity.get("allowed", "")
    identity_valid &= all(term in identity_rule for term in ("pointer", "PID", "user-selected"))
    if not identity_valid:
        return _issue("invalid_identity", "context.fields.opaque_identity", "Identity must be nonzero while live and zero, non-pointer, and non-PID otherwise")
    reserved_issue = _reserved_field_issue(context["fields"])
    if reserved_issue is not None:
        return reserved_issue
    return None


def _lifecycle_issue(contract) -> FixedUserExecutionContextIssue | None:
    lifecycle = contract.lifecycle
    if lifecycle.get("encodings") != _LIFECYCLE_ENCODINGS:
        return _issue("invalid_lifecycle", "lifecycle.encodings", "Lifecycle encodings must remain exact")
    if _edges(lifecycle.get("successful_transitions")) != _SUCCESS_EDGES:
        return _issue("invalid_lifecycle", "lifecycle.successful_transitions", "Successful lifecycle must advance without skips")
    if _edges(lifecycle.get("failure_cleanup_transitions")) != _FAILURE_EDGES:
        return _issue("invalid_cleanup_edge", "lifecycle.failure_cleanup_transitions", "Every live lifecycle state must fail closed to CLEARED")
    if _edges(lifecycle.get("forbidden_transitions")) != _FORBIDDEN_EDGES:
        return _issue("invalid_lifecycle", "lifecycle.forbidden_transitions", "Skipped, backward, and cleared-context reuse transitions must remain forbidden")
    if lifecycle.get("pre_ready_failure") != "remain_UNINITIALIZED_commit_failure_result_and_do_not_enter_ring3":
        return _issue("invalid_cleanup_edge", "lifecycle.pre_ready_failure", "Failure before READY must establish no authority and cannot enter Ring3")
    if lifecycle.get("reuse_allowed") is not False:
        return _issue("invalid_lifecycle", "lifecycle.reuse_allowed", "CLEARED context reuse is outside this phase")
    return None


def _clear_state_issue(contract) -> FixedUserExecutionContextIssue | None:
    clear = contract.clear_state
    fields = {field[0] for field in _CONTEXT_FIELDS}
    retained = set(clear.get("retained_structural_fields", {})) | {"lifecycle"}
    expected_zero = fields - retained - {"format_version", "structure_size"}
    if set(clear.get("zeroized_fields", ())) != expected_zero:
        return _issue("invalid_clear_state", "clear_state.zeroized_fields", "Every authority field must be zeroized exactly once")
    required = (clear.get("lifecycle") == "CLEARED" and clear.get("zero_readback_required") is True and clear.get("lifecycle_readback_required") is True)
    if not required or clear.get("normal_continuation_requires_valid_clear_state") is not True:
        return _issue("invalid_clear_state", "clear_state", "CLEARED and zero readback must dominate normal continuation")
    return None


def _result_issue(contract) -> FixedUserExecutionContextIssue | None:
    result = contract.result
    if (result.get("format_version"), result.get("size_bytes"), result.get("alignment_bytes")) != (1, 32, 8):
        return _issue("invalid_result_geometry", "result", "Result geometry must be version 1, 32 bytes, aligned to 8")
    if _field_layout(result.get("fields")) != _RESULT_FIELDS:
        return _issue("invalid_result_geometry", "result.fields", "Result fields must occupy the exact 32-byte layout")
    if set(result.get("authority_fields_forbidden", ())) != _FORBIDDEN_RESULT_FIELDS:
        return _issue("result_retains_authority", "result.authority_fields_forbidden", "Result authority exclusions must remain complete")
    if contract_module.result_field_names(contract) & _FORBIDDEN_RESULT_FIELDS:
        return _issue("result_retains_authority", "result.fields", "Result must not retain identity, pointers, selectors, mappings, or handles")
    lifetime = contract.result_lifetime
    if lifetime.get("commit_count") != 1 or lifetime.get("can_authorize_execution") is not False or lifetime.get("identity_retained") is not False:
        return _issue("invalid_result_lifetime", "result_lifetime", "Result must be committed once and remain non-authoritative")
    if lifetime.get("reset_before_future_initialization") is not True or lifetime.get("history_supported") is not False:
        return _issue("invalid_result_lifetime", "result_lifetime", "Stale result reuse and result history are forbidden")
    return None


def _binding_issue(contract) -> FixedUserExecutionContextIssue | None:
    bindings = contract.fixed_bindings
    expected_regions = (
        ("user_code", "0x0000400000000000", 4096, "user_rx", "user_probe_code"),
        ("user_data", "0x0000400000001000", 4096, "user_rw_nx", "user_probe_data"),
        ("user_stack", "0x0000400000002000", 4096, "user_rw_nx", "user_probe_stack"),
    )
    for name, start, size, permissions, source in expected_regions:
        binding = bindings.get(name, {})
        actual = (binding.get("virtual_start"), binding.get("size_bytes"), binding.get("permissions"), binding.get("source_region"))
        if actual != (start, size, permissions, source):
            return _issue("invalid_binding", f"fixed_bindings.{name}", f"{name} must match the accepted fixed mapping")
    return _fixed_policy_issue(bindings)


def _source_consistency_issue(contract) -> FixedUserExecutionContextIssue | None:
    sources = contract.authoritative_sources
    try:
        mapping = _load_json_source(sources["mapping"])
        privilege = _load_json_source(sources["privilege_transition"])
        request = _load_json_source(sources["request_boundary"])
        response = _load_json_source(sources["response_consumption"])
    except (KeyError, OSError, json.JSONDecodeError) as exc:
        return _issue("source_contract_invalid", "authoritative_sources", f"Referenced authority is unreadable: {exc}")
    checks = (
        _mapping_source_issue(contract.fixed_bindings, mapping),
        _privilege_source_issue(contract.fixed_bindings, privilege),
        _transaction_source_issue(contract.fixed_bindings, request, response),
    )
    return _first_issue(checks)


def _mapping_source_issue(bindings, mapping) -> FixedUserExecutionContextIssue | None:
    regions = {region["name"]: region for region in mapping.get("user_regions", ())}
    for binding_name, region_name in (("user_code", "user_probe_code"), ("user_data", "user_probe_data"), ("user_stack", "user_probe_stack")):
        binding = bindings[binding_name]
        region = regions.get(region_name, {})
        if (binding.get("virtual_start"), binding.get("size_bytes")) != (region.get("virtual_start"), region.get("size_bytes")):
            return _issue("binding_source_mismatch", f"fixed_bindings.{binding_name}", f"{binding_name} must match fixed mapping authority")
    return None


def _privilege_source_issue(bindings, privilege) -> FixedUserExecutionContextIssue | None:
    entry = bindings["entry"]
    stack = bindings["user_stack"]
    expected_entry = (privilege["entry"]["fixed_code_symbol"], privilege["entry"]["fixed_virtual_rip"], privilege["selectors"]["user_code"], privilege["selectors"]["user_data"], privilege["idt"]["return_vector"])
    actual_entry = (entry["symbol"], entry["virtual_address"], entry["user_code_selector"], entry["user_data_selector"], entry["return_vector"])
    if actual_entry != expected_entry or stack["initial_rsp"] != privilege["stacks"]["user"]["initial_rsp"]:
        return _issue("binding_source_mismatch", "fixed_bindings.entry", "Entry, stack, selectors, and return vector must match privilege authority")
    return None


def _transaction_source_issue(bindings, request, response) -> FixedUserExecutionContextIssue | None:
    transaction = bindings["transaction"]
    phases = response.get("transaction_phases", {})
    expected = (request["request"]["identifier"], phases.get("storage_symbol"), "REQUEST_PENDING", "RESPONSE_READY", "CONSUMED", 0, 1, 2)
    actual = (transaction["request_identifier"], transaction["phase_storage_symbol"], transaction["request_phase"], transaction["response_phase"], transaction["completed_phase"], phases.get("request_pending"), phases.get("response_ready"), phases.get("consumed"))
    if actual != expected:
        return _issue("transaction_source_mismatch", "fixed_bindings.transaction", "Transaction identity and phases must match accepted contracts")
    return None


def _fixed_policy_issue(bindings) -> FixedUserExecutionContextIssue | None:
    stack = bindings["user_stack"]
    if (stack.get("virtual_top"), stack.get("initial_rsp")) != ("0x0000400000003000", "0x0000400000002ff0"):
        return _issue("invalid_binding", "fixed_bindings.user_stack", "Stack top and initial RSP must remain fixed")
    entry = bindings["entry"]
    expected_entry = ("user_privilege_probe_start", "0x0000400000000000", "0x23", "0x1b", "0x81")
    actual_entry = (entry.get("symbol"), entry.get("virtual_address"), entry.get("user_code_selector"), entry.get("user_data_selector"), entry.get("return_vector"))
    if actual_entry != expected_entry:
        return _issue("invalid_binding", "fixed_bindings.entry", "Entry, selectors, and return vector must match accepted policy")
    return None


def _transition_budget_issue(contract) -> FixedUserExecutionContextIssue | None:
    budget = contract.transition_budget
    if budget.get("authorized_count") != len(budget.get("derivation", ())) or budget.get("authorized_count") != 2:
        return _issue("invalid_transition_budget", "transition_budget.authorized_count", "Budget must be derived from exactly two existing returns")
    first, second = budget["derivation"]
    first_pair = (first.get("required_phase_before"), first.get("required_count_before"), first.get("count_after_entry"), first.get("phase_after_handler"))
    second_pair = (second.get("required_phase_before"), second.get("required_count_before"), second.get("count_after_entry"), second.get("phase_after_handler"))
    if first_pair != ("REQUEST_PENDING", 0, 1, "RESPONSE_READY") or second_pair != ("RESPONSE_READY", 1, 2, "CONSUMED"):
        return _issue("invalid_phase_count_coupling", "transition_budget.derivation", "Both existing returns require exact phase/count pairs")
    if budget.get("third_transition") != "fail_closed_budget_exceeded" or budget.get("phase_and_count_both_required") is not True:
        return _issue("third_transition_allowed", "transition_budget", "A third return must fail closed and phase cannot substitute for count")
    return None


def _progression_issue(contract) -> FixedUserExecutionContextIssue | None:
    placement = contract.runtime_progression.get("placement", ())
    required_order = ("KOZO_RUNTIME_LOOP_EXIT_OK", "READY", "ACTIVE", "RETURNED", "commit_lifecycle_result", "validate_CLEARED", "KOZO_RING0_RETURN_OK", "existing_internal_capability_continuation")
    if not _is_ordered_subsequence(required_order, placement):
        return _issue("invalid_progression", "runtime_progression.placement", "Context lifecycle must wrap the existing transaction before Odin continuation")
    if contract.runtime_progression.get("implementation_authorized") is not False or contract.runtime_progression.get("repeated_session") is not False:
        return _issue("implementation_overclaim", "runtime_progression", "Governance cannot authorize implementation or repeated sessions")
    return None


def _evidence_claim_issue(contract) -> FixedUserExecutionContextIssue | None:
    evidence = contract.evidence_policy
    expected_hosts = ["ubuntu-24.04", "windows-2025", "macos-15"]
    if evidence.get("governed_check_count") != 67 or evidence.get("marker_count") != 41:
        return _issue("evidence_count_changed", "evidence_policy", "Governed checks and marker counts must remain 67 and 41")
    if evidence.get("marker_change_required") is not False or evidence.get("runtime_evidence_claimed") is not False:
        return _issue("runtime_evidence_overclaim", "evidence_policy", "No marker or runtime implementation evidence is authorized")
    if evidence.get("required_build_hosts") != expected_hosts or evidence.get("required_runtime_host") != "ubuntu-24.04":
        return _issue("portability_weakened", "evidence_policy", "ADR 0017 host and runtime authority must remain unchanged")
    return None


def _governance_alignment_issue(contract) -> FixedUserExecutionContextIssue | None:
    if not _ADR_PATH.is_file() or "## Status\n\nAccepted" not in _ADR_PATH.read_text():
        return _issue("adr_not_accepted", "authoritative_sources.decision", "ADR 0018 must exist and be accepted")
    try:
        progression = json.loads(_PROGRESSION_PATH.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return _issue("progression_invalid", "authoritative_sources.runtime_progression", f"Runtime progression authority is unreadable: {exc}")
    stage = next((item for item in progression.get("stages", ()) if item.get("stage_name") == "USERSPACE_PLANNING"), None)
    if stage is None or _CONTRACT_REFERENCE not in stage.get("required_contracts", ()):
        return _issue("progression_not_aligned", "runtime_progression", "USERSPACE_PLANNING must require the fixed context contract")
    return None


def _field_layout(fields) -> tuple[tuple[str, int, int, str], ...]:
    if not isinstance(fields, list):
        return ()
    return tuple((field.get("name"), field.get("offset"), field.get("size"), field.get("type")) for field in fields if isinstance(field, dict))


def _reserved_field_issue(fields) -> FixedUserExecutionContextIssue | None:
    for name in ("reserved_0", "reserved_1"):
        field = _named_field(fields, name)
        if field.get("authority") != "reserved" or field.get("allowed") != "zero" or field.get("initial") != 0 or field.get("cleared") != 0:
            return _issue("invalid_reserved_state", f"context.fields.{name}", "Reserved fields must remain zero in every state")
    return None


def _load_json_source(reference: str) -> dict:
    return json.loads((ROOT / reference).read_text())


def _named_field(fields, name: str) -> dict:
    return next((field for field in fields if field.get("name") == name), {})


def _edges(transitions) -> tuple[tuple[str, str], ...]:
    if not isinstance(transitions, list):
        return ()
    return tuple((edge.get("from"), edge.get("to")) for edge in transitions if isinstance(edge, dict))


def _is_ordered_subsequence(required, actual) -> bool:
    positions = iter(actual)
    return all(any(candidate == expected for candidate in positions) for expected in required)


def _first_issue(issues) -> FixedUserExecutionContextIssue | None:
    return next((issue for issue in issues if issue is not None), None)


def _issue(reason: str, field: str, detail: str) -> FixedUserExecutionContextIssue:
    return FixedUserExecutionContextIssue(reason, field, detail)


def _failure(issue: FixedUserExecutionContextIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=FIXED_USER_EXECUTION_CONTEXT_CONTRACT_INVALID,
        detail=issue.detail,
        action="Align the fixed user execution context governance contract with ADR 0018",
        meta={"reason": issue.reason, "contract_field": issue.contract_field},
    )
