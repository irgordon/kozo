from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness import runtime_progression_entry_contract as contract_module
from harness.codes import OK, RUNTIME_PROGRESSION_ENTRY_CONTRACT_INVALID
from harness.validator import BaseValidator, ValidationResult

_CONTRACT_PATH = contract_module.CONTRACT_PATH
_EXPECTED_PATH = "boot_smoke_to_stack_memory_and_runtime_progression_to_halt"
_EXPECTED_CONTEXT_FIELDS = (
    ("version", 0),
    ("structure_size", 8),
    ("stack_base", 16),
    ("stack_top", 24),
    ("memory_region_start", 32),
    ("memory_region_end", 40),
    ("flags", 48),
    ("reserved", 56),
)
_REQUIRED_PREREQUISITES = (
    "stack initialization evidence",
    "memory initialization evidence",
    "memory initialization evidence contract",
)
_REQUIRED_TRANSITIONS = (
    "runtime_halt_contract remains authoritative after bounded runtime progression",
    "KOZO_RUNTIME_INIT_OK must originate from executed Odin code",
    "KOZO_RUNTIME_RETURN_OK requires the exact success status",
    "CI QEMU evidence is required before progression stages are proven",
)
_REQUIRED_NON_GOALS = (
    "complete Odin runtime readiness",
    "allocator behavior",
    "userspace execution",
    "interrupt handling",
    "scheduler behavior",
    "hardware syscall boundary",
    "Linux compatibility",
    "POSIX compatibility",
    "production readiness",
)


@dataclass(frozen=True)
class RuntimeProgressionEntryIssue:
    reason: str
    contract_field: str
    detail: str


class RuntimeProgressionEntryContractValidator(BaseValidator):
    name = "runtime_progression_entry_contract"
    subsystem = "runtime_progression_entry_contract"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _runtime_progression_entry_issue(_CONTRACT_PATH)
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Runtime progression entry contract governs the assembly-to-Odin call and terminal return boundary",
        )


def _runtime_progression_entry_issue(path: Path) -> RuntimeProgressionEntryIssue | None:
    contract = _load_contract(path)
    if isinstance(contract, RuntimeProgressionEntryIssue):
        return contract
    return _first_issue(
        _current_state_issue(contract),
        _reference_issue(contract),
        _progression_entry_issue(contract),
        _calling_convention_issue(contract),
        _bootstrap_context_issue(contract),
        _runtime_initialization_issue(contract),
        _return_boundary_issue(contract),
        _required_values_issue(contract.required_prerequisites, _REQUIRED_PREREQUISITES, "missing_prerequisite", "required_prerequisites"),
        _required_values_issue(contract.transition_requirements, _REQUIRED_TRANSITIONS, "missing_transition_requirement", "transition_requirements"),
        _required_values_issue(contract.non_goals, _REQUIRED_NON_GOALS, "missing_non_goal", "non_goals"),
    )


def _load_contract(path: Path):
    if not path.is_file():
        return _issue("missing_contract_file", "contract", f"Runtime progression entry contract is missing: {path}")
    try:
        return contract_module.load_runtime_progression_entry_contract(path)
    except json.JSONDecodeError as exc:
        return _issue("invalid_contract_json", "contract", f"Runtime progression entry contract is invalid JSON: {exc}")
    except (KeyError, TypeError, ValueError) as exc:
        return _issue("contract_schema_violation", "contract", f"Runtime progression entry contract schema violation: {exc}")


def _current_state_issue(contract) -> RuntimeProgressionEntryIssue | None:
    state = contract.current_state
    expected = (
        (contract.architecture, "x86_64", "architecture"),
        (state.path, _EXPECTED_PATH, "current_state.path"),
        (state.final_smoke_marker, "KOZO_RUNTIME_RETURN_OK", "current_state.final_smoke_marker"),
        (state.terminal_behavior, "halt_loop", "current_state.terminal_behavior"),
    )
    return _expected_values_issue(expected, "wrong_current_state")


def _reference_issue(contract) -> RuntimeProgressionEntryIssue | None:
    references = (
        (contract.current_state.halt_contract, "current_state.halt_contract"),
        (contract.current_state.progression_contract, "current_state.progression_contract"),
        (contract.current_state.progression_stages_contract, "current_state.progression_stages_contract"),
    )
    for value, field in references:
        if not contract_module.contract_repo_path(value).is_file():
            return _issue("missing_contract_reference", field, f"Referenced contract is missing: {value}")
    return None


def _progression_entry_issue(contract) -> RuntimeProgressionEntryIssue | None:
    entry = contract.progression_entry
    expected = (
        (entry.marker, "KOZO_RUNTIME_PROGRESS_ENTRY", "progression_entry.marker"),
        (entry.status, "implemented", "progression_entry.status"),
        (entry.emitted, True, "progression_entry.emitted"),
        (entry.source_file, "kernel/arch/x86_64/boot.asm", "progression_entry.source_file"),
        (entry.assembly_entry_symbol, "_start", "progression_entry.assembly_entry_symbol"),
        (entry.target_symbol, "runtime_progression_entry", "progression_entry.target_symbol"),
    )
    return _expected_values_issue(expected, "progression_entry_mismatch")


def _calling_convention_issue(contract) -> RuntimeProgressionEntryIssue | None:
    convention = contract.calling_convention
    expected = (
        (convention.name, "System V AMD64 C", "calling_convention.name"),
        (convention.argument_registers, ("rdi",), "calling_convention.argument_registers"),
        (convention.return_register, "eax", "calling_convention.return_register"),
        (convention.call_site_stack_alignment_bytes, 16, "calling_convention.call_site_stack_alignment_bytes"),
        (convention.callee_entry_stack_modulo_bytes, 8, "calling_convention.callee_entry_stack_modulo_bytes"),
        (convention.red_zone_policy, "disabled_by_freestanding_build", "calling_convention.red_zone_policy"),
    )
    return _expected_values_issue(expected, "calling_convention_mismatch")


def _bootstrap_context_issue(contract) -> RuntimeProgressionEntryIssue | None:
    context = contract.bootstrap_context
    fields = tuple((field.name, field.offset_bytes) for field in context.fields)
    expected = (
        (context.version, 1, "bootstrap_context.version"),
        (context.size_bytes, 64, "bootstrap_context.size_bytes"),
        (context.symbol, "runtime_bootstrap_context", "bootstrap_context.symbol"),
        (fields, _EXPECTED_CONTEXT_FIELDS, "bootstrap_context.fields"),
        (context.required_zero_fields, ("flags", "reserved"), "bootstrap_context.required_zero_fields"),
    )
    return _expected_values_issue(expected, "bootstrap_context_mismatch")


def _runtime_initialization_issue(contract) -> RuntimeProgressionEntryIssue | None:
    runtime = contract.runtime_initialization
    expected = (
        (runtime.source_file, "kernel/runtime_progression.odin", "runtime_initialization.source_file"),
        (runtime.entry_symbol, "runtime_progression_entry", "runtime_initialization.entry_symbol"),
        (runtime.marker, "KOZO_RUNTIME_INIT_OK", "runtime_initialization.marker"),
        (runtime.serial_bridge_symbol, "runtime_serial_write_init_marker", "runtime_initialization.serial_bridge_symbol"),
        (runtime.state_symbol, "runtime_progression_state", "runtime_initialization.state_symbol"),
        (runtime.operation, "bounded_write_read_restore", "runtime_initialization.operation"),
        (runtime.success_status, 0, "runtime_initialization.success_status"),
    )
    return _expected_values_issue(expected, "runtime_initialization_mismatch")


def _return_boundary_issue(contract) -> RuntimeProgressionEntryIssue | None:
    boundary = contract.return_boundary
    expected = (
        (boundary.marker, "KOZO_RUNTIME_RETURN_OK", "return_boundary.marker"),
        (boundary.status, "implemented", "return_boundary.status"),
        (boundary.emitted, True, "return_boundary.emitted"),
        (boundary.required_status, 0, "return_boundary.required_status"),
        (boundary.terminal_behavior, "halt_loop", "return_boundary.terminal_behavior"),
    )
    return _expected_values_issue(expected, "return_boundary_mismatch")


def _expected_values_issue(expected_values, reason: str) -> RuntimeProgressionEntryIssue | None:
    for actual, expected, field in expected_values:
        if actual != expected:
            return _issue(reason, field, f"Expected {field} to be {expected}, got {actual}")
    return None


def _required_values_issue(actual, required, reason: str, field: str) -> RuntimeProgressionEntryIssue | None:
    for value in required:
        if value not in actual:
            return _issue(reason, f"{field}.{value}", f"Runtime progression entry contract must declare: {value}")
    return None


def _first_issue(*issues: RuntimeProgressionEntryIssue | None) -> RuntimeProgressionEntryIssue | None:
    return next((issue for issue in issues if issue is not None), None)


def _issue(reason: str, field: str, detail: str) -> RuntimeProgressionEntryIssue:
    return RuntimeProgressionEntryIssue(reason, field, detail)


def _failure(issue: RuntimeProgressionEntryIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=RUNTIME_PROGRESSION_ENTRY_CONTRACT_INVALID,
        detail=issue.detail,
        action="Keep the assembly-to-Odin boundary aligned with the governed progression contract",
        meta={"reason": issue.reason, "contract_field": issue.contract_field},
    )
