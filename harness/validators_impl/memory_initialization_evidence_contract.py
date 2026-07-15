from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness import memory_initialization_evidence_contract
from harness.codes import MEMORY_INITIALIZATION_EVIDENCE_CONTRACT_INVALID, OK
from harness.validator import BaseValidator, ValidationResult

_CONTRACT_PATH = memory_initialization_evidence_contract.CONTRACT_PATH
_EXPECTED_ARCHITECTURE = "x86_64"
_EXPECTED_RUNTIME_PATH = "boot_smoke_to_stack_evidence_to_halt"
_EXPECTED_STAGE = "MEMORY_INITIALIZATION_EVIDENCE"
_EXPECTED_MARKER = "KOZO_MEMORY_INIT_OK"
_EXPECTED_MARKER_STATUS = "reserved"
_EXPECTED_FUTURE_VALIDATOR = "memory_initialization_evidence"
_REQUIRED_PREREQUISITES = (
    "QEMU serial smoke evidence",
    "runtime halt contract",
    "runtime progression contract",
    "runtime progression stages contract",
    "stack initialization evidence",
    "stack initialization evidence contract",
)
_REQUIRED_EVIDENCE = (
    "memory structures initialized",
    "ownership documented",
    "controlled memory region",
    "KOZO_MEMORY_INIT_OK marker captured from runtime code",
    "memory initialization validator proof",
)
_REQUIRED_ASSUMPTIONS_ENABLED = (
    "controlled memory access after the proven memory marker",
    "eligibility for runtime progression entry after memory and progression path evidence",
    "safe memory-dependent preparation for later runtime initialization evidence",
)
_REQUIRED_ASSUMPTIONS_NOT_ENABLED = (
    "paging enabled",
    "allocator behavior",
    "heap allocation",
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
    "memory initialization implementation",
    "paging implementation",
    "allocator behavior",
    "heap allocation",
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
class MemoryEvidenceIssue:
    reason: str
    contract_field: str
    detail: str


class MemoryInitializationEvidenceContractValidator(BaseValidator):
    name = "memory_initialization_evidence_contract"
    subsystem = "memory_initialization_evidence_contract"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _memory_evidence_issue(_CONTRACT_PATH)
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Memory initialization evidence contract governs the future memory proof boundary",
        )


def _memory_evidence_issue(contract_path: Path) -> MemoryEvidenceIssue | None:
    contract = _load_contract(contract_path)
    if isinstance(contract, MemoryEvidenceIssue):
        return contract
    return _first_issue(
        _current_state_issue(contract),
        _contract_reference_issue(contract.current_state.halt_contract, "current_state.halt_contract"),
        _contract_reference_issue(contract.current_state.progression_stages_contract, "current_state.progression_stages_contract"),
        _contract_reference_issue(contract.current_state.stack_initialization_evidence_contract, "current_state.stack_initialization_evidence_contract"),
        _memory_marker_issue(contract),
        _required_value_issue(contract.prerequisites, _REQUIRED_PREREQUISITES, "missing_prerequisite", "prerequisites"),
        _required_value_issue(contract.evidence_requirements, _REQUIRED_EVIDENCE, "missing_evidence_requirement", "evidence_requirements"),
        _required_value_issue(contract.assumptions_enabled, _REQUIRED_ASSUMPTIONS_ENABLED, "missing_assumption_mapping", "assumptions_enabled"),
        _required_value_issue(contract.assumptions_not_enabled, _REQUIRED_ASSUMPTIONS_NOT_ENABLED, "missing_assumption_boundary", "assumptions_not_enabled"),
        _required_value_issue(contract.future_validators, (_EXPECTED_FUTURE_VALIDATOR,), "missing_future_validator", "future_validators"),
        _required_value_issue(contract.non_goals, _REQUIRED_NON_GOALS, "missing_non_goal", "non_goals"),
    )


def _load_contract(
    path: Path,
) -> memory_initialization_evidence_contract.MemoryInitializationEvidenceContract | MemoryEvidenceIssue:
    if not path.is_file():
        return _issue("missing_contract_file", "contract", f"Memory initialization evidence contract is missing: {path}")
    try:
        return memory_initialization_evidence_contract.load_memory_initialization_evidence_contract(path)
    except json.JSONDecodeError as exc:
        return _issue("invalid_contract_json", "contract", f"Memory initialization evidence contract is invalid JSON: {exc}")
    except (KeyError, TypeError, ValueError) as exc:
        return _issue("contract_schema_violation", "contract", f"Memory initialization evidence contract schema violation: {exc}")


def _current_state_issue(
    contract: memory_initialization_evidence_contract.MemoryInitializationEvidenceContract,
) -> MemoryEvidenceIssue | None:
    state = contract.current_state
    return _first_issue(
        _expected_value_issue(contract.architecture, _EXPECTED_ARCHITECTURE, "wrong_architecture", "architecture"),
        _expected_value_issue(state.runtime_path, _EXPECTED_RUNTIME_PATH, "wrong_runtime_path", "current_state.runtime_path"),
        _expected_value_issue(state.stage, _EXPECTED_STAGE, "wrong_stage", "current_state.stage"),
        _implemented_issue(state.implemented),
    )


def _implemented_issue(implemented: bool) -> MemoryEvidenceIssue | None:
    if implemented is False:
        return None
    return _issue("memory_implementation_claimed", "current_state.implemented", "Memory evidence planning must not claim memory initialization is implemented")


def _contract_reference_issue(contract_path: str, field: str) -> MemoryEvidenceIssue | None:
    path = memory_initialization_evidence_contract.contract_repo_path(contract_path)
    if path.is_file():
        return None
    return _issue("missing_contract_reference", field, f"Referenced contract is missing: {contract_path}")


def _memory_marker_issue(
    contract: memory_initialization_evidence_contract.MemoryInitializationEvidenceContract,
) -> MemoryEvidenceIssue | None:
    definition = contract.memory_definition
    return _first_issue(
        _expected_value_issue(definition.reserved_marker, _EXPECTED_MARKER, "missing_marker", "memory_definition.reserved_marker"),
        _expected_value_issue(definition.marker_status, _EXPECTED_MARKER_STATUS, "wrong_marker_status", "memory_definition.marker_status"),
        _marker_emission_issue(definition.marker_emitted),
    )


def _marker_emission_issue(emitted: bool) -> MemoryEvidenceIssue | None:
    if emitted is False:
        return None
    return _issue("marker_claimed", "memory_definition.marker_emitted", "KOZO_MEMORY_INIT_OK must remain reserved and not emitted in the planning phase")


def _required_value_issue(
    actual_values: tuple[str, ...],
    expected_values: tuple[str, ...],
    reason: str,
    field: str,
) -> MemoryEvidenceIssue | None:
    for expected in expected_values:
        if expected not in actual_values:
            return _issue(reason, f"{field}.{expected}", f"Memory initialization evidence contract must declare: {expected}")
    return None


def _expected_value_issue(
    actual: str,
    expected: str,
    reason: str,
    contract_field: str,
) -> MemoryEvidenceIssue | None:
    if actual == expected:
        return None
    return _issue(reason, contract_field, f"Expected {contract_field} to be {expected}, got {actual}")


def _first_issue(*issues: MemoryEvidenceIssue | None) -> MemoryEvidenceIssue | None:
    for issue in issues:
        if issue is not None:
            return issue
    return None


def _issue(reason: str, contract_field: str, detail: str) -> MemoryEvidenceIssue:
    return MemoryEvidenceIssue(reason=reason, contract_field=contract_field, detail=detail)


def _failure(issue: MemoryEvidenceIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=MEMORY_INITIALIZATION_EVIDENCE_CONTRACT_INVALID,
        detail=issue.detail,
        action="Keep memory initialization evidence as a planning contract until runtime evidence exists",
        meta={
            "reason": issue.reason,
            "contract_field": issue.contract_field,
        },
    )
