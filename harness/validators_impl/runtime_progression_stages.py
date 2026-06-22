from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness import runtime_progression_stages
from harness.codes import OK, RUNTIME_PROGRESSION_STAGES_INVALID
from harness.validator import BaseValidator, ValidationResult

_CONTRACT_PATH = runtime_progression_stages.CONTRACT_PATH
_EXPECTED_ARCHITECTURE = "x86_64"
_EXPECTED_TERMINAL_BEHAVIOR = "halt_loop"
_EXPECTED_STAGE_SEQUENCE = (
    "BOOT_SMOKE",
    "RUNTIME_PROGRESSION_ENTRY",
    "STACK_INITIALIZATION_EVIDENCE",
    "MEMORY_INITIALIZATION_EVIDENCE",
    "RUNTIME_INITIALIZATION_EVIDENCE",
    "CONTROLLED_RUNTIME_LOOP",
    "FIRST_GOVERNED_RUNTIME_CAPABILITY",
    "USERSPACE_PLANNING",
)
_REQUIRED_TRANSITION_REQUIREMENTS = (
    "runtime_halt_contract remains authoritative until runtime progression evidence exists",
    "stages must advance in declared order unless a later contract explicitly supersedes this stage model",
    "halt replacement requires contract-backed progression evidence",
    "planning stages do not constitute runtime evidence",
)
_REQUIRED_FORBIDDEN_SHORTCUTS = (
    "delete halt loop without progression evidence",
    "replace halt loop without progression evidence",
    "bypass halt loop without progression evidence",
    "jump around halt loop without progression evidence",
    "claim userspace execution from planning evidence",
    "claim production readiness from planning evidence",
)
_REQUIRED_NON_GOALS = (
    "runtime progression execution",
    "halt loop replacement",
    "stack initialization",
    "memory initialization",
    "Odin runtime execution",
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
_REQUIRED_STAGE_PREREQUISITES = {
    "BOOT_SMOKE": ("runtime halt contract",),
    "RUNTIME_PROGRESSION_ENTRY": ("runtime progression entry contract",),
    "STACK_INITIALIZATION_EVIDENCE": ("stack initialization contract",),
    "MEMORY_INITIALIZATION_EVIDENCE": ("memory initialization contract",),
    "RUNTIME_INITIALIZATION_EVIDENCE": ("runtime initialization contract",),
    "CONTROLLED_RUNTIME_LOOP": ("halt replacement evidence",),
    "FIRST_GOVERNED_RUNTIME_CAPABILITY": ("first runtime capability contract",),
    "USERSPACE_PLANNING": ("userspace planning contract",),
}
_REQUIRED_STAGE_EVIDENCE = {
    "BOOT_SMOKE": ("artifacts/runtime/qemu_smoke.metadata.json",),
    "RUNTIME_PROGRESSION_ENTRY": ("QEMU evidence for KOZO_RUNTIME_PROGRESS_ENTRY",),
    "STACK_INITIALIZATION_EVIDENCE": ("QEMU evidence for stack initialization marker",),
    "MEMORY_INITIALIZATION_EVIDENCE": ("QEMU evidence for memory initialization marker",),
    "RUNTIME_INITIALIZATION_EVIDENCE": ("QEMU evidence for runtime initialization marker",),
    "CONTROLLED_RUNTIME_LOOP": ("QEMU evidence for controlled runtime loop",),
    "FIRST_GOVERNED_RUNTIME_CAPABILITY": ("QEMU evidence for first governed runtime capability",),
    "USERSPACE_PLANNING": ("userspace planning evidence",),
}


@dataclass(frozen=True)
class RuntimeProgressionStagesIssue:
    reason: str
    contract_field: str
    detail: str


class RuntimeProgressionStagesValidator(BaseValidator):
    name = "runtime_progression_stages"
    subsystem = "runtime_progression_stages"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _runtime_progression_stages_issue(_CONTRACT_PATH)
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Runtime progression stages contract centralizes planned runtime stage ordering and transitions",
        )


def _runtime_progression_stages_issue(contract_path: Path) -> RuntimeProgressionStagesIssue | None:
    contract = _load_contract(contract_path)
    if isinstance(contract, RuntimeProgressionStagesIssue):
        return contract
    return _first_issue(
        _current_state_issue(contract),
        _contract_reference_issue(contract.current_state.halt_contract, "current_state.halt_contract"),
        _contract_reference_issue(contract.current_state.progression_contract, "current_state.progression_contract"),
        _contract_reference_issue(contract.current_state.progression_entry_contract, "current_state.progression_entry_contract"),
        _stage_sequence_issue(contract),
        _duplicate_stage_issue(contract),
        _stage_definition_issue(contract),
        _transition_issue(contract),
        _required_value_issue(contract.transition_requirements, _REQUIRED_TRANSITION_REQUIREMENTS, "missing_transition_requirement", "transition_requirements"),
        _required_value_issue(contract.forbidden_global_shortcuts, _REQUIRED_FORBIDDEN_SHORTCUTS, "missing_forbidden_shortcut", "forbidden_global_shortcuts"),
        _required_value_issue(contract.non_goals, _REQUIRED_NON_GOALS, "missing_non_goal", "non_goals"),
    )


def _load_contract(
    path: Path,
) -> runtime_progression_stages.RuntimeProgressionStagesContract | RuntimeProgressionStagesIssue:
    if not path.is_file():
        return _issue("missing_contract_file", "contract", f"Runtime progression stages contract is missing: {path}")
    try:
        return runtime_progression_stages.load_runtime_progression_stages_contract(path)
    except json.JSONDecodeError as exc:
        return _issue("invalid_contract_json", "contract", f"Runtime progression stages contract is invalid JSON: {exc}")
    except (KeyError, TypeError, ValueError) as exc:
        return _issue("contract_schema_violation", "contract", f"Runtime progression stages contract schema violation: {exc}")


def _current_state_issue(
    contract: runtime_progression_stages.RuntimeProgressionStagesContract,
) -> RuntimeProgressionStagesIssue | None:
    return _first_issue(
        _expected_value_issue(contract.architecture, _EXPECTED_ARCHITECTURE, "wrong_architecture", "architecture"),
        _expected_value_issue(contract.current_state.terminal_behavior, _EXPECTED_TERMINAL_BEHAVIOR, "wrong_terminal_behavior", "current_state.terminal_behavior"),
    )


def _contract_reference_issue(contract_path: str, field: str) -> RuntimeProgressionStagesIssue | None:
    path = runtime_progression_stages.contract_repo_path(contract_path)
    if path.is_file():
        return None
    return _issue("missing_contract_reference", field, f"Referenced contract is missing: {contract_path}")


def _stage_sequence_issue(
    contract: runtime_progression_stages.RuntimeProgressionStagesContract,
) -> RuntimeProgressionStagesIssue | None:
    actual = runtime_progression_stages.stage_names(contract)
    if actual == _EXPECTED_STAGE_SEQUENCE:
        return None
    return _issue("missing_stage", "stages", "Runtime progression stages must preserve the canonical stage sequence")


def _duplicate_stage_issue(
    contract: runtime_progression_stages.RuntimeProgressionStagesContract,
) -> RuntimeProgressionStagesIssue | None:
    stage_ids = tuple(stage.stage_id for stage in contract.stages)
    stage_names = runtime_progression_stages.stage_names(contract)
    if len(stage_ids) != len(set(stage_ids)):
        return _issue("duplicate_stage", "stages.stage_id", "Runtime progression stage identifiers must be unique")
    if len(stage_names) != len(set(stage_names)):
        return _issue("duplicate_stage", "stages.stage_name", "Runtime progression stage names must be unique")
    return None


def _stage_definition_issue(
    contract: runtime_progression_stages.RuntimeProgressionStagesContract,
) -> RuntimeProgressionStagesIssue | None:
    for stage in contract.stages:
        issue = _first_issue(
            _non_empty_tuple_issue(stage.required_prerequisites, "missing_prerequisite", f"stages.{stage.stage_name}.required_prerequisites"),
            _non_empty_tuple_issue(stage.required_evidence, "missing_evidence_requirement", f"stages.{stage.stage_name}.required_evidence"),
            _non_empty_tuple_issue(stage.required_contracts, "missing_contract_requirement", f"stages.{stage.stage_name}.required_contracts"),
            _non_empty_tuple_issue(stage.required_validators, "missing_validator_requirement", f"stages.{stage.stage_name}.required_validators"),
            _non_empty_tuple_issue(stage.forbidden_shortcuts, "missing_forbidden_shortcut", f"stages.{stage.stage_name}.forbidden_shortcuts"),
            _stage_required_value_issue(stage.required_prerequisites, _REQUIRED_STAGE_PREREQUISITES[stage.stage_name], "missing_prerequisite", f"stages.{stage.stage_name}.required_prerequisites"),
            _stage_required_value_issue(stage.required_evidence, _REQUIRED_STAGE_EVIDENCE[stage.stage_name], "missing_evidence_requirement", f"stages.{stage.stage_name}.required_evidence"),
        )
        if issue is not None:
            return issue
    return None


def _transition_issue(
    contract: runtime_progression_stages.RuntimeProgressionStagesContract,
) -> RuntimeProgressionStagesIssue | None:
    valid_stage_names = set(runtime_progression_stages.stage_names(contract))
    for index, stage in enumerate(contract.stages):
        unknown = sorted(set(stage.allowed_next_stages) - valid_stage_names)
        if unknown:
            return _issue("invalid_transition", f"stages.{stage.stage_name}.allowed_next_stages", f"Allowed transition references unknown stage: {unknown[0]}")
        expected_next = _expected_next_stage(index)
        if tuple(stage.allowed_next_stages) != expected_next:
            return _issue("invalid_transition", f"stages.{stage.stage_name}.allowed_next_stages", "Runtime progression stages must advance only to the declared next stage")
    return None


def _expected_next_stage(index: int) -> tuple[str, ...]:
    if index + 1 >= len(_EXPECTED_STAGE_SEQUENCE):
        return ()
    return (_EXPECTED_STAGE_SEQUENCE[index + 1],)


def _required_value_issue(
    actual_values: tuple[str, ...],
    expected_values: tuple[str, ...],
    reason: str,
    field: str,
) -> RuntimeProgressionStagesIssue | None:
    for expected in expected_values:
        if expected not in actual_values:
            return _issue(reason, f"{field}.{expected}", f"Runtime progression stages contract must declare: {expected}")
    return None


def _non_empty_tuple_issue(
    values: tuple[str, ...],
    reason: str,
    field: str,
) -> RuntimeProgressionStagesIssue | None:
    if values:
        return None
    return _issue(reason, field, f"Runtime progression stage must declare {field}")


def _stage_required_value_issue(
    actual_values: tuple[str, ...],
    expected_values: tuple[str, ...],
    reason: str,
    field: str,
) -> RuntimeProgressionStagesIssue | None:
    for expected in expected_values:
        if expected not in actual_values:
            return _issue(reason, f"{field}.{expected}", f"Runtime progression stage must declare: {expected}")
    return None


def _expected_value_issue(
    actual: str,
    expected: str,
    reason: str,
    contract_field: str,
) -> RuntimeProgressionStagesIssue | None:
    if actual == expected:
        return None
    return _issue(reason, contract_field, f"Expected {contract_field} to be {expected}, got {actual}")


def _first_issue(*issues: RuntimeProgressionStagesIssue | None) -> RuntimeProgressionStagesIssue | None:
    for issue in issues:
        if issue is not None:
            return issue
    return None


def _issue(reason: str, contract_field: str, detail: str) -> RuntimeProgressionStagesIssue:
    return RuntimeProgressionStagesIssue(reason=reason, contract_field=contract_field, detail=detail)


def _failure(issue: RuntimeProgressionStagesIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=RUNTIME_PROGRESSION_STAGES_INVALID,
        detail=issue.detail,
        action="Keep runtime progression stage planning centralized and subordinate to the runtime halt contract until progression evidence exists",
        meta={
            "reason": issue.reason,
            "contract_field": issue.contract_field,
        },
    )
