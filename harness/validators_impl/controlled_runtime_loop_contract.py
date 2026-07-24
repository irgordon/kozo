from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness import controlled_runtime_loop_contract as contract_module
from harness.codes import CONTROLLED_RUNTIME_LOOP_CONTRACT_INVALID, OK
from harness.validator import BaseValidator, ValidationResult

_CONTRACT_PATH = contract_module.CONTRACT_PATH
_EXPECTED_MARKERS = (
    "KOZO_RUNTIME_LOOP_ENTER",
    "KOZO_RUNTIME_LOOP_ITER_1",
    "KOZO_RUNTIME_LOOP_ITER_2",
    "KOZO_RUNTIME_LOOP_ITER_3",
    "KOZO_RUNTIME_LOOP_EXIT_OK",
)
_EXPECTED_FIELDS = (
    ("iteration_limit", 64, 3, 3),
    ("iteration_count", 64, 0, 3),
    ("accumulator", 64, 0, 6),
    ("status", 32, 0, 2),
    ("reserved", 32, 0, 0),
)
_EXPECTED_STATUSES = {
    "success": 0,
    "invalid_limit": 3,
    "invalid_initial_state": 4,
    "iteration_state_mismatch": 5,
    "accumulator_mismatch": 6,
    "terminal_count_mismatch": 7,
    "terminal_status_mismatch": 8,
}
_REQUIRED_NON_GOALS = (
    "first governed runtime capability",
    "userspace execution",
    "scheduler behavior",
    "interrupt handling",
    "allocator behavior",
    "Linux compatibility",
    "POSIX compatibility",
    "production readiness",
)


@dataclass(frozen=True)
class ControlledRuntimeLoopContractIssue:
    reason: str
    contract_field: str
    detail: str


class ControlledRuntimeLoopContractValidator(BaseValidator):
    name = "controlled_runtime_loop_contract"
    subsystem = "controlled_runtime_loop_contract"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _contract_issue(_CONTRACT_PATH)
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Controlled runtime loop contract governs bounded state, markers, status, and halt continuation",
        )


def _contract_issue(path: Path) -> ControlledRuntimeLoopContractIssue | None:
    contract = _load_contract(path)
    if isinstance(contract, ControlledRuntimeLoopContractIssue):
        return contract
    return _first_issue(
        _loop_issue(contract),
        _state_issue(contract),
        _marker_issue(contract),
        _status_issue(contract),
        _terminal_issue(contract),
        _authority_issue(contract),
        _non_goal_issue(contract),
    )


def _load_contract(path: Path):
    if not path.is_file():
        return _issue("missing_contract_file", "contract", f"Controlled runtime loop contract is missing: {path}")
    try:
        return contract_module.load_controlled_runtime_loop_contract(path)
    except json.JSONDecodeError as exc:
        return _issue("invalid_contract_json", "contract", f"Controlled runtime loop contract is invalid JSON: {exc}")
    except (KeyError, TypeError, ValueError) as exc:
        return _issue("contract_schema_violation", "contract", f"Controlled runtime loop contract schema violation: {exc}")


def _loop_issue(contract) -> ControlledRuntimeLoopContractIssue | None:
    if contract.current_state.status != "implemented_pending_ci":
        return _issue("wrong_stage_status", "current_state.status", "Controlled runtime loop must remain implemented_pending_ci before hosted acceptance")
    if contract.loop.iteration_limit != 3:
        return _issue("wrong_iteration_limit", "loop.iteration_limit", "Controlled runtime loop must execute exactly three iterations")
    if not contract.loop.backward_edge_required:
        return _issue("missing_backward_edge_requirement", "loop.backward_edge_required", "Controlled runtime loop must require a binary backward edge")
    return None


def _state_issue(contract) -> ControlledRuntimeLoopContractIssue | None:
    actual = tuple(
        (field.name, field.width_bits, field.initial_value, field.final_value)
        for field in contract.state.fields
    )
    if actual != _EXPECTED_FIELDS:
        return _issue("invalid_state_definition", "state.fields", "Controlled runtime loop state fields or values do not match the governed layout")
    if not contract.state.volatile_access_required:
        return _issue("volatile_access_not_required", "state.volatile_access_required", "Controlled runtime loop state must require volatile accesses")
    return None


def _marker_issue(contract) -> ControlledRuntimeLoopContractIssue | None:
    if contract.markers.ordered_sequence != _EXPECTED_MARKERS:
        return _issue("wrong_marker_order", "markers.ordered_sequence", "Controlled runtime loop markers must use the governed order")
    if contract.markers.required_after != "KOZO_RUNTIME_INIT_OK":
        return _issue("wrong_marker_predecessor", "markers.required_after", "Loop entry evidence must follow runtime initialization evidence")
    if contract.markers.required_before != "KOZO_RUNTIME_RETURN_OK":
        return _issue("wrong_marker_successor", "markers.required_before", "Loop exit evidence must precede runtime return evidence")
    return None


def _status_issue(contract) -> ControlledRuntimeLoopContractIssue | None:
    if contract.statuses != _EXPECTED_STATUSES:
        return _issue("invalid_status_map", "statuses", "Controlled runtime loop status map must preserve exact deterministic outcomes")
    if len(set(contract.statuses.values())) != len(contract.statuses):
        return _issue("duplicate_status_value", "statuses", "Controlled runtime loop status values must be unique")
    return None


def _terminal_issue(contract) -> ControlledRuntimeLoopContractIssue | None:
    terminal = contract.terminal_behavior
    if terminal.get("required_return_status") != 0:
        return _issue("wrong_return_status", "terminal_behavior.required_return_status", "Runtime return evidence requires exact status zero")
    if terminal.get("fallthrough_forbidden") is not True:
        return _issue("fallthrough_allowed", "terminal_behavior.fallthrough_forbidden", "Controlled runtime loop continuation must forbid fallthrough")
    return None


def _authority_issue(contract) -> ControlledRuntimeLoopContractIssue | None:
    owner = "controlled_runtime_loop_contract owns the RUNTIME_INITIALIZATION_EVIDENCE to CONTROLLED_RUNTIME_LOOP proof boundary"
    if owner not in contract.transition_ownership:
        return _issue("missing_transition_owner", "transition_ownership", "Controlled runtime loop proof boundary requires one explicit owner")
    if len(contract.required_evidence) < 6:
        return _issue("missing_evidence_requirement", "required_evidence", "Controlled runtime loop contract must define all required evidence categories")
    return None


def _non_goal_issue(contract) -> ControlledRuntimeLoopContractIssue | None:
    for non_goal in _REQUIRED_NON_GOALS:
        if non_goal not in contract.non_goals:
            return _issue("missing_non_goal", f"non_goals.{non_goal}", f"Controlled runtime loop must preserve non-goal: {non_goal}")
    return None


def _first_issue(*issues):
    return next((issue for issue in issues if issue is not None), None)


def _issue(reason: str, field: str, detail: str) -> ControlledRuntimeLoopContractIssue:
    return ControlledRuntimeLoopContractIssue(reason, field, detail)


def _failure(issue: ControlledRuntimeLoopContractIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=CONTROLLED_RUNTIME_LOOP_CONTRACT_INVALID,
        detail=issue.detail,
        action="Align the controlled runtime loop contract with bounded loop governance",
        meta={"reason": issue.reason, "contract_field": issue.contract_field},
    )
