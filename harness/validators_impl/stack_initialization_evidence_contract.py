from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness import stack_initialization_evidence_contract
from harness.codes import OK, STACK_INITIALIZATION_EVIDENCE_CONTRACT_INVALID
from harness.validator import BaseValidator, ValidationResult

_CONTRACT_PATH = stack_initialization_evidence_contract.CONTRACT_PATH
_EXPECTED_ARCHITECTURE = "x86_64"
_EXPECTED_RUNTIME_PATH = "boot_smoke_to_halt"
_EXPECTED_STAGE = "STACK_INITIALIZATION_EVIDENCE"
_EXPECTED_MARKER = "KOZO_STACK_INIT_OK"
_EXPECTED_MARKER_STATUS = "reserved"
_EXPECTED_FUTURE_VALIDATOR = "stack_initialization_evidence"
_REQUIRED_PREREQUISITES = (
    "QEMU serial smoke evidence",
    "runtime halt contract",
    "runtime progression contract",
    "runtime progression entry contract",
    "runtime progression stages contract",
)
_REQUIRED_EVIDENCE = (
    "stack pointer initialized",
    "stack pointer remains valid",
    "controlled stack location",
    "documented stack ownership",
    "KOZO_STACK_INIT_OK marker captured from runtime code",
    "stack initialization validator proof",
)
_REQUIRED_ASSUMPTIONS_ENABLED = (
    "safe call instruction usage after the proven stack marker",
    "safe function nesting after the proven stack marker",
    "safe runtime progression entry after the proven stack marker",
    "safe progression beyond halt only after separate progression evidence permits halt replacement",
)
_REQUIRED_ASSUMPTIONS_NOT_ENABLED = (
    "memory initialization",
    "Odin runtime execution",
    "interrupt handling",
    "scheduler behavior",
    "userspace execution",
    "process model behavior",
    "VFS behavior",
    "device driver behavior",
    "syscall dispatch during boot",
    "production readiness",
)
_REQUIRED_NON_GOALS = (
    "stack initialization implementation",
    "stack allocation",
    "memory initialization",
    "Odin runtime execution",
    "runtime progression execution",
    "halt loop replacement",
    "interrupt handling",
    "scheduler behavior",
    "userspace execution",
    "process model behavior",
    "VFS behavior",
    "device driver behavior",
    "Linux compatibility",
    "POSIX compatibility",
    "production readiness",
)


@dataclass(frozen=True)
class StackEvidenceIssue:
    reason: str
    contract_field: str
    detail: str


class StackInitializationEvidenceContractValidator(BaseValidator):
    name = "stack_initialization_evidence_contract"
    subsystem = "stack_initialization_evidence_contract"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _stack_evidence_issue(_CONTRACT_PATH)
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Stack initialization evidence contract reserves the future stack proof boundary without implementing stack setup",
        )


def _stack_evidence_issue(contract_path: Path) -> StackEvidenceIssue | None:
    contract = _load_contract(contract_path)
    if isinstance(contract, StackEvidenceIssue):
        return contract
    return _first_issue(
        _current_state_issue(contract),
        _contract_reference_issue(contract.current_state.halt_contract, "current_state.halt_contract"),
        _contract_reference_issue(contract.current_state.progression_stages_contract, "current_state.progression_stages_contract"),
        _stack_marker_issue(contract),
        _required_value_issue(contract.prerequisites, _REQUIRED_PREREQUISITES, "missing_prerequisite", "prerequisites"),
        _required_value_issue(contract.evidence_requirements, _REQUIRED_EVIDENCE, "missing_evidence_requirement", "evidence_requirements"),
        _required_value_issue(contract.assumptions_enabled, _REQUIRED_ASSUMPTIONS_ENABLED, "missing_assumption_mapping", "assumptions_enabled"),
        _required_value_issue(contract.assumptions_not_enabled, _REQUIRED_ASSUMPTIONS_NOT_ENABLED, "missing_assumption_boundary", "assumptions_not_enabled"),
        _required_value_issue(contract.future_validators, (_EXPECTED_FUTURE_VALIDATOR,), "missing_future_validator", "future_validators"),
        _required_value_issue(contract.non_goals, _REQUIRED_NON_GOALS, "missing_non_goal", "non_goals"),
    )


def _load_contract(
    path: Path,
) -> stack_initialization_evidence_contract.StackInitializationEvidenceContract | StackEvidenceIssue:
    if not path.is_file():
        return _issue("missing_contract_file", "contract", f"Stack initialization evidence contract is missing: {path}")
    try:
        return stack_initialization_evidence_contract.load_stack_initialization_evidence_contract(path)
    except json.JSONDecodeError as exc:
        return _issue("invalid_contract_json", "contract", f"Stack initialization evidence contract is invalid JSON: {exc}")
    except (KeyError, TypeError, ValueError) as exc:
        return _issue("contract_schema_violation", "contract", f"Stack initialization evidence contract schema violation: {exc}")


def _current_state_issue(
    contract: stack_initialization_evidence_contract.StackInitializationEvidenceContract,
) -> StackEvidenceIssue | None:
    state = contract.current_state
    return _first_issue(
        _expected_value_issue(contract.architecture, _EXPECTED_ARCHITECTURE, "wrong_architecture", "architecture"),
        _expected_value_issue(state.runtime_path, _EXPECTED_RUNTIME_PATH, "wrong_runtime_path", "current_state.runtime_path"),
        _expected_value_issue(state.stage, _EXPECTED_STAGE, "wrong_stage", "current_state.stage"),
        _implemented_issue(state.implemented),
    )


def _implemented_issue(implemented: bool) -> StackEvidenceIssue | None:
    if implemented is False:
        return None
    return _issue("stack_implementation_claimed", "current_state.implemented", "Stack evidence planning must not claim stack setup is implemented")


def _contract_reference_issue(contract_path: str, field: str) -> StackEvidenceIssue | None:
    path = stack_initialization_evidence_contract.contract_repo_path(contract_path)
    if path.is_file():
        return None
    return _issue("missing_contract_reference", field, f"Referenced contract is missing: {contract_path}")


def _stack_marker_issue(
    contract: stack_initialization_evidence_contract.StackInitializationEvidenceContract,
) -> StackEvidenceIssue | None:
    definition = contract.stack_definition
    return _first_issue(
        _expected_value_issue(definition.reserved_marker, _EXPECTED_MARKER, "missing_marker", "stack_definition.reserved_marker"),
        _expected_value_issue(definition.marker_status, _EXPECTED_MARKER_STATUS, "wrong_marker_status", "stack_definition.marker_status"),
        _marker_emission_issue(definition.marker_emitted),
    )


def _marker_emission_issue(emitted: bool) -> StackEvidenceIssue | None:
    if emitted is False:
        return None
    return _issue("marker_claimed", "stack_definition.marker_emitted", "KOZO_STACK_INIT_OK must stay reserved and not emitted in this planning phase")


def _required_value_issue(
    actual_values: tuple[str, ...],
    expected_values: tuple[str, ...],
    reason: str,
    field: str,
) -> StackEvidenceIssue | None:
    for expected in expected_values:
        if expected not in actual_values:
            return _issue(reason, f"{field}.{expected}", f"Stack initialization evidence contract must declare: {expected}")
    return None


def _expected_value_issue(
    actual: str,
    expected: str,
    reason: str,
    contract_field: str,
) -> StackEvidenceIssue | None:
    if actual == expected:
        return None
    return _issue(reason, contract_field, f"Expected {contract_field} to be {expected}, got {actual}")


def _first_issue(*issues: StackEvidenceIssue | None) -> StackEvidenceIssue | None:
    for issue in issues:
        if issue is not None:
            return issue
    return None


def _issue(reason: str, contract_field: str, detail: str) -> StackEvidenceIssue:
    return StackEvidenceIssue(reason=reason, contract_field=contract_field, detail=detail)


def _failure(issue: StackEvidenceIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=STACK_INITIALIZATION_EVIDENCE_CONTRACT_INVALID,
        detail=issue.detail,
        action="Keep stack initialization evidence planning separate from stack setup implementation until runtime evidence exists",
        meta={
            "reason": issue.reason,
            "contract_field": issue.contract_field,
        },
    )
