from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness import runtime_progression_entry_contract
from harness.codes import OK, RUNTIME_PROGRESSION_ENTRY_CONTRACT_INVALID
from harness.validator import BaseValidator, ValidationResult

_CONTRACT_PATH = runtime_progression_entry_contract.CONTRACT_PATH
_EXPECTED_ARCHITECTURE = "x86_64"
_EXPECTED_HALT_CONTRACT = "contracts/runtime_halt_contract.v0.json"
_EXPECTED_PROGRESSION_CONTRACT = "contracts/runtime_progression_contract.v0.json"
_EXPECTED_FINAL_MARKER = "KOZO_BOOT_SMOKE_OK"
_EXPECTED_TERMINAL_BEHAVIOR = "halt_loop"
_EXPECTED_PROGRESSION_MARKER = "KOZO_RUNTIME_PROGRESS_ENTRY"
_EXPECTED_ENTRY_STATUS = "reserved"
_REQUIRED_PREREQUISITES = (
    "stack initialization evidence",
    "stack initialization evidence contract",
    "memory initialization evidence",
    "runtime initialization evidence",
    "progression path evidence",
)
_REQUIRED_EVIDENCE = (
    "runtime progression entry contract",
    "QEMU evidence for KOZO_RUNTIME_PROGRESS_ENTRY",
    "stack initialization evidence",
    "stack initialization evidence contract",
    "memory initialization evidence",
    "runtime initialization evidence",
    "release evidence update",
)
_REQUIRED_TRANSITION_REQUIREMENTS = (
    "runtime_halt_contract remains authoritative until runtime progression evidence exists",
    "runtime_progression_contract remains the parent transition governance contract",
    "KOZO_RUNTIME_PROGRESS_ENTRY must not be claimed until emitted by runtime code and captured in evidence",
    "halt replacement requires contract-backed progression evidence",
)
_REQUIRED_FORBIDDEN_SHORTCUTS = (
    "delete halt loop",
    "replace halt loop",
    "bypass halt loop",
    "jump around halt loop",
)
_REQUIRED_OWNERSHIP = (
    "runtime_halt_contract owns current terminal behavior",
    "runtime_progression_contract owns halt-to-runtime transition governance",
    "runtime_progression_entry_contract owns future progression entry marker reservation and readiness requirements",
)
_REQUIRED_NON_GOALS = (
    "runtime progression execution",
    "stack initialization",
    "memory initialization",
    "Odin runtime execution",
    "userspace execution",
    "interrupt handling",
    "scheduler behavior",
    "VFS behavior",
    "process model behavior",
    "device driver behavior",
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
            detail="Runtime progression entry contract reserves the future entry marker without changing the halt baseline",
        )


def _runtime_progression_entry_issue(contract_path: Path) -> RuntimeProgressionEntryIssue | None:
    contract = _load_contract(contract_path)
    if isinstance(contract, RuntimeProgressionEntryIssue):
        return contract
    return _first_issue(
        _current_state_issue(contract),
        _contract_reference_issue(contract.current_state.halt_contract, "current_state.halt_contract"),
        _contract_reference_issue(contract.current_state.progression_contract, "current_state.progression_contract"),
        _progression_marker_issue(contract),
        _required_value_issue(contract.required_prerequisites, _REQUIRED_PREREQUISITES, "missing_prerequisite", "required_prerequisites"),
        _required_value_issue(contract.required_evidence, _REQUIRED_EVIDENCE, "missing_required_evidence", "required_evidence"),
        _required_value_issue(contract.transition_requirements, _REQUIRED_TRANSITION_REQUIREMENTS, "missing_transition_requirement", "transition_requirements"),
        _required_value_issue(contract.forbidden_shortcuts, _REQUIRED_FORBIDDEN_SHORTCUTS, "missing_forbidden_shortcut", "forbidden_shortcuts"),
        _required_value_issue(contract.transition_ownership, _REQUIRED_OWNERSHIP, "missing_transition_ownership", "transition_ownership"),
        _stage_issue(contract),
        _required_value_issue(contract.non_goals, _REQUIRED_NON_GOALS, "missing_non_goal", "non_goals"),
    )


def _load_contract(
    path: Path,
) -> runtime_progression_entry_contract.RuntimeProgressionEntryContract | RuntimeProgressionEntryIssue:
    if not path.is_file():
        return _issue("missing_contract_file", "contract", f"Runtime progression entry contract is missing: {path}")
    try:
        return runtime_progression_entry_contract.load_runtime_progression_entry_contract(path)
    except json.JSONDecodeError as exc:
        return _issue("invalid_contract_json", "contract", f"Runtime progression entry contract is invalid JSON: {exc}")
    except (KeyError, TypeError, ValueError) as exc:
        return _issue("contract_schema_violation", "contract", f"Runtime progression entry contract schema violation: {exc}")


def _current_state_issue(
    contract: runtime_progression_entry_contract.RuntimeProgressionEntryContract,
) -> RuntimeProgressionEntryIssue | None:
    state = contract.current_state
    return _first_issue(
        _expected_value_issue(contract.architecture, _EXPECTED_ARCHITECTURE, "wrong_architecture", "architecture"),
        _expected_value_issue(state.halt_contract, _EXPECTED_HALT_CONTRACT, "missing_halt_reference", "current_state.halt_contract"),
        _expected_value_issue(state.progression_contract, _EXPECTED_PROGRESSION_CONTRACT, "missing_progression_reference", "current_state.progression_contract"),
        _expected_value_issue(state.final_smoke_marker, _EXPECTED_FINAL_MARKER, "wrong_final_marker", "current_state.final_smoke_marker"),
        _expected_value_issue(state.terminal_behavior, _EXPECTED_TERMINAL_BEHAVIOR, "wrong_terminal_behavior", "current_state.terminal_behavior"),
    )


def _contract_reference_issue(contract_path: str, field: str) -> RuntimeProgressionEntryIssue | None:
    path = runtime_progression_entry_contract.contract_repo_path(contract_path)
    if path.is_file():
        return None
    return _issue("missing_contract_reference", field, f"Referenced contract is missing: {contract_path}")


def _progression_marker_issue(
    contract: runtime_progression_entry_contract.RuntimeProgressionEntryContract,
) -> RuntimeProgressionEntryIssue | None:
    entry = contract.progression_entry
    return _first_issue(
        _expected_value_issue(entry.marker, _EXPECTED_PROGRESSION_MARKER, "missing_progression_marker", "progression_entry.marker"),
        _expected_value_issue(entry.status, _EXPECTED_ENTRY_STATUS, "wrong_progression_marker_status", "progression_entry.status"),
        _marker_emission_issue(entry.emitted),
    )


def _marker_emission_issue(emitted: bool) -> RuntimeProgressionEntryIssue | None:
    if emitted is False:
        return None
    return _issue(
        "progression_marker_claimed",
        "progression_entry.emitted",
        "Runtime progression marker must stay reserved and not emitted in this planning phase",
    )


def _required_value_issue(
    actual_values: tuple[str, ...],
    expected_values: tuple[str, ...],
    reason: str,
    field: str,
) -> RuntimeProgressionEntryIssue | None:
    for expected in expected_values:
        if expected not in actual_values:
            return _issue(reason, f"{field}.{expected}", f"Runtime progression entry contract must declare: {expected}")
    return None


def _stage_issue(
    contract: runtime_progression_entry_contract.RuntimeProgressionEntryContract,
) -> RuntimeProgressionEntryIssue | None:
    expected = (
        (0, "Boot smoke", "proven"),
        (1, "Runtime progression entry", "planned"),
        (2, "Stack initialization evidence", "planned"),
        (3, "Memory initialization evidence", "planned"),
        (4, "Runtime initialization evidence", "planned"),
        (5, "Controlled runtime loop", "planned"),
        (6, "First governed runtime capability", "planned"),
    )
    actual = tuple((stage.stage, stage.name, stage.status) for stage in contract.future_progression_stages)
    if actual == expected:
        return None
    return _issue("missing_progression_stage", "future_progression_stages", "Runtime progression stages must preserve the governed planning sequence")


def _expected_value_issue(
    actual: str,
    expected: str,
    reason: str,
    contract_field: str,
) -> RuntimeProgressionEntryIssue | None:
    if actual == expected:
        return None
    return _issue(reason, contract_field, f"Expected {contract_field} to be {expected}, got {actual}")


def _first_issue(*issues: RuntimeProgressionEntryIssue | None) -> RuntimeProgressionEntryIssue | None:
    for issue in issues:
        if issue is not None:
            return issue
    return None


def _issue(reason: str, contract_field: str, detail: str) -> RuntimeProgressionEntryIssue:
    return RuntimeProgressionEntryIssue(reason=reason, contract_field=contract_field, detail=detail)


def _failure(issue: RuntimeProgressionEntryIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=RUNTIME_PROGRESSION_ENTRY_CONTRACT_INVALID,
        detail=issue.detail,
        action="Keep runtime progression entry planning subordinate to halt and progression contracts until entry evidence exists",
        meta={
            "reason": issue.reason,
            "contract_field": issue.contract_field,
        },
    )
