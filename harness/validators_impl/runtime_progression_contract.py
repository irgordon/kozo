from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness import runtime_progression_contract
from harness.codes import OK, RUNTIME_PROGRESSION_CONTRACT_INVALID
from harness.validator import BaseValidator, ValidationResult

_CONTRACT_PATH = runtime_progression_contract.CONTRACT_PATH
_EXPECTED_ARCHITECTURE = "x86_64"
_EXPECTED_HALT_CONTRACT = "contracts/runtime_halt_contract.v0.json"
_EXPECTED_FINAL_MARKER = "KOZO_BOOT_SMOKE_OK"
_EXPECTED_TERMINAL_BEHAVIOR = "halt_loop"
_REQUIRED_PREREQUISITES = (
    "stack initialization evidence",
    "stack initialization evidence contract",
    "memory initialization evidence contract",
    "runtime initialization evidence",
    "memory initialization evidence",
    "progression path evidence",
)
_REQUIRED_TRANSITION_REQUIREMENTS = (
    "halt loop remains authoritative until runtime progression is separately proven",
    "runtime progression must have contract-backed evidence before halt behavior changes",
    "runtime progression must preserve the existing QEMU smoke marker sequence until a successor evidence path is accepted",
    "runtime progression must update release evidence and validation before claims expand",
)
_REQUIRED_FORBIDDEN_SHORTCUTS = (
    "delete halt loop",
    "replace halt loop",
    "bypass halt loop",
    "jump around halt loop",
)
_REQUIRED_EVIDENCE_REQUIREMENTS = (
    "runtime progression contract",
    "stack initialization evidence contract",
    "memory initialization evidence contract",
    "focused validator coverage",
    "QEMU evidence for progression entry",
    "release evidence update",
    "planning document update",
)
_REQUIRED_NON_GOALS = (
    "Odin runtime execution",
    "userspace execution",
    "interrupt handling",
    "scheduler behavior",
    "VFS behavior",
    "process model behavior",
    "syscall dispatch during boot",
    "memory manager behavior",
    "hardware trap handling",
    "device driver behavior",
    "Linux compatibility",
    "POSIX compatibility",
    "production readiness",
)


@dataclass(frozen=True)
class RuntimeProgressionIssue:
    reason: str
    contract_field: str
    detail: str


class RuntimeProgressionContractValidator(BaseValidator):
    name = "runtime_progression_contract"
    subsystem = "runtime_progression_contract"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _runtime_progression_issue(_CONTRACT_PATH)
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Runtime progression contract preserves the halt baseline until future progression evidence exists",
        )


def _runtime_progression_issue(contract_path: Path) -> RuntimeProgressionIssue | None:
    contract = _load_contract(contract_path)
    if isinstance(contract, RuntimeProgressionIssue):
        return contract
    return _first_issue(
        _current_state_issue(contract),
        _halt_reference_issue(contract),
        _required_value_issue(contract.progression_prerequisites, _REQUIRED_PREREQUISITES, "missing_prerequisite", "progression_prerequisites"),
        _required_value_issue(contract.transition_requirements, _REQUIRED_TRANSITION_REQUIREMENTS, "missing_transition_requirement", "transition_requirements"),
        _required_value_issue(contract.forbidden_shortcuts, _REQUIRED_FORBIDDEN_SHORTCUTS, "missing_forbidden_shortcut", "forbidden_shortcuts"),
        _milestone_issue(contract),
        _required_value_issue(contract.evidence_requirements, _REQUIRED_EVIDENCE_REQUIREMENTS, "missing_evidence_requirement", "evidence_requirements"),
        _required_value_issue(contract.non_goals, _REQUIRED_NON_GOALS, "missing_non_goal", "non_goals"),
    )


def _load_contract(path: Path) -> runtime_progression_contract.RuntimeProgressionContract | RuntimeProgressionIssue:
    if not path.is_file():
        return _issue("missing_contract_file", "contract", f"Runtime progression contract is missing: {path}")
    try:
        return runtime_progression_contract.load_runtime_progression_contract(path)
    except json.JSONDecodeError as exc:
        return _issue("invalid_contract_json", "contract", f"Runtime progression contract is invalid JSON: {exc}")
    except (KeyError, TypeError, ValueError) as exc:
        return _issue("contract_schema_violation", "contract", f"Runtime progression contract schema violation: {exc}")


def _current_state_issue(contract: runtime_progression_contract.RuntimeProgressionContract) -> RuntimeProgressionIssue | None:
    state = contract.current_state
    return _first_issue(
        _expected_value_issue(contract.architecture, _EXPECTED_ARCHITECTURE, "wrong_architecture", "architecture"),
        _expected_value_issue(state.halt_contract, _EXPECTED_HALT_CONTRACT, "missing_halt_reference", "current_state.halt_contract"),
        _expected_value_issue(state.final_smoke_marker, _EXPECTED_FINAL_MARKER, "wrong_final_marker", "current_state.final_smoke_marker"),
        _expected_value_issue(state.terminal_behavior, _EXPECTED_TERMINAL_BEHAVIOR, "wrong_terminal_behavior", "current_state.terminal_behavior"),
    )


def _halt_reference_issue(contract: runtime_progression_contract.RuntimeProgressionContract) -> RuntimeProgressionIssue | None:
    path = runtime_progression_contract.contract_repo_path(contract.current_state.halt_contract)
    if path.is_file():
        return None
    return _issue("missing_halt_reference", "current_state.halt_contract", f"Referenced halt contract is missing: {contract.current_state.halt_contract}")


def _required_value_issue(
    actual_values: tuple[str, ...],
    expected_values: tuple[str, ...],
    reason: str,
    field: str,
) -> RuntimeProgressionIssue | None:
    for expected in expected_values:
        if expected not in actual_values:
            return _issue(reason, f"{field}.{expected}", f"Runtime progression contract must declare: {expected}")
    return None


def _milestone_issue(contract: runtime_progression_contract.RuntimeProgressionContract) -> RuntimeProgressionIssue | None:
    expected = (
        (0, "Boot smoke", "proven"),
        (1, "Runtime progression entry", "planned"),
        (2, "Stack initialization evidence", "proven"),
        (3, "Runtime initialization evidence", "planned"),
        (4, "Controlled runtime loop", "planned"),
        (5, "First governed runtime capability", "planned"),
        (6, "Userspace planning", "planned"),
    )
    actual = tuple(
        (milestone.stage, milestone.name, milestone.status)
        for milestone in contract.future_runtime_milestones
    )
    if actual == expected:
        return None
    return _issue("missing_runtime_milestone", "future_runtime_milestones", "Runtime progression milestones must preserve the governed planning sequence")


def _expected_value_issue(
    actual: str,
    expected: str,
    reason: str,
    contract_field: str,
) -> RuntimeProgressionIssue | None:
    if actual == expected:
        return None
    return _issue(reason, contract_field, f"Expected {contract_field} to be {expected}, got {actual}")


def _first_issue(*issues: RuntimeProgressionIssue | None) -> RuntimeProgressionIssue | None:
    for issue in issues:
        if issue is not None:
            return issue
    return None


def _issue(reason: str, contract_field: str, detail: str) -> RuntimeProgressionIssue:
    return RuntimeProgressionIssue(reason=reason, contract_field=contract_field, detail=detail)


def _failure(issue: RuntimeProgressionIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=RUNTIME_PROGRESSION_CONTRACT_INVALID,
        detail=issue.detail,
        action="Keep runtime progression planning subordinate to the runtime halt contract until progression evidence exists",
        meta={
            "reason": issue.reason,
            "contract_field": issue.contract_field,
        },
    )
