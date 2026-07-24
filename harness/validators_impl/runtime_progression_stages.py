from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from harness import runtime_progression_stages
from harness.codes import OK, RUNTIME_PROGRESSION_STAGES_INVALID
from harness.registry import CHECKS
from harness.validator import BaseValidator, ValidationResult

_CONTRACT_PATH = runtime_progression_stages.CONTRACT_PATH
_EXPECTED_ARCHITECTURE = "x86_64"
_EXPECTED_RUNTIME_PATH = "boot_smoke_to_stack_memory_and_runtime_progression_to_halt"
_EXPECTED_TERMINAL_BEHAVIOR = "halt_loop"
_REQUIRED_STAGE_NAMES = frozenset(
    {
        "BOOT_SMOKE",
        "STACK_INITIALIZATION_EVIDENCE",
        "MEMORY_INITIALIZATION_EVIDENCE",
        "RUNTIME_PROGRESSION_ENTRY",
        "RUNTIME_INITIALIZATION_EVIDENCE",
        "CONTROLLED_RUNTIME_LOOP",
        "FIRST_GOVERNED_RUNTIME_CAPABILITY",
        "USERSPACE_PLANNING",
    }
)
_REQUIRED_STAGE_EVIDENCE = {
    "BOOT_SMOKE": "artifacts/runtime/qemu_smoke.metadata.json",
    "STACK_INITIALIZATION_EVIDENCE": "QEMU evidence for KOZO_STACK_INIT_OK",
    "MEMORY_INITIALIZATION_EVIDENCE": "QEMU evidence for KOZO_MEMORY_INIT_OK",
    "RUNTIME_PROGRESSION_ENTRY": "QEMU evidence for KOZO_RUNTIME_PROGRESS_ENTRY",
    "RUNTIME_INITIALIZATION_EVIDENCE": "QEMU evidence for KOZO_RUNTIME_INIT_OK",
    "CONTROLLED_RUNTIME_LOOP": "QEMU evidence through KOZO_RUNTIME_LOOP_EXIT_OK",
    "FIRST_GOVERNED_RUNTIME_CAPABILITY": "QEMU evidence for first governed runtime capability",
    "USERSPACE_PLANNING": "userspace planning evidence",
}
_REQUIRED_TRANSITION_REQUIREMENTS = (
    "runtime_halt_contract remains authoritative after bounded runtime progression",
    "runtime_progression_stages contract owns canonical stage order and allowed transitions",
    "transition owner contracts own destination-stage proof boundaries",
    "evidence contracts must not redefine canonical stage order",
    "stages must advance in declared order unless a later contract explicitly supersedes this stage model",
    "halt replacement requires a separately governed controlled runtime loop",
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
    "runtime progression beyond the bounded entry call",
    "halt loop replacement",
    "general stack readiness",
    "general memory management",
    "complete Odin runtime readiness",
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
class RuntimeProgressionStagesIssue:
    reason: str
    contract_field: str
    detail: str


@dataclass(frozen=True)
class RuntimeProgressionGraph:
    stages: tuple[runtime_progression_stages.RuntimeProgressionStage, ...]
    stages_by_name: dict[str, runtime_progression_stages.RuntimeProgressionStage]
    order_by_name: dict[str, int]


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
            detail="Runtime progression stages form an acyclic, monotonic, authority-backed graph",
        )


def _runtime_progression_stages_issue(
    contract_path: Path,
) -> RuntimeProgressionStagesIssue | None:
    contract = _load_contract(contract_path)
    if isinstance(contract, RuntimeProgressionStagesIssue):
        return contract
    structural_issue = _structural_issue(contract)
    if structural_issue is not None:
        return structural_issue
    return _graph_issue(contract, _build_graph(contract))


def _structural_issue(
    contract: runtime_progression_stages.RuntimeProgressionStagesContract,
) -> RuntimeProgressionStagesIssue | None:
    checks = (
        lambda: _current_state_issue(contract),
        lambda: _current_contract_reference_issue(contract),
        lambda: _duplicate_stage_issue(contract),
        lambda: _required_stage_issue(contract),
        lambda: _stage_id_issue(contract),
        lambda: _stage_content_issue(contract),
        lambda: _required_value_issue(contract.transition_requirements, _REQUIRED_TRANSITION_REQUIREMENTS, "missing_transition_requirement", "transition_requirements"),
        lambda: _required_value_issue(contract.forbidden_global_shortcuts, _REQUIRED_FORBIDDEN_SHORTCUTS, "missing_forbidden_shortcut", "forbidden_global_shortcuts"),
        lambda: _required_value_issue(contract.non_goals, _REQUIRED_NON_GOALS, "missing_non_goal", "non_goals"),
    )
    return _first_check_issue(checks)


def _graph_issue(
    contract: runtime_progression_stages.RuntimeProgressionStagesContract,
    graph: RuntimeProgressionGraph,
) -> RuntimeProgressionStagesIssue | None:
    checks = (
        lambda: _prerequisite_reference_issue(graph),
        lambda: _mandatory_prerequisite_issue(graph),
        lambda: _direct_cycle_issue(graph),
        lambda: _indirect_cycle_issue(graph),
        lambda: _prerequisite_order_issue(graph),
        lambda: _stage_status_issue(graph),
        lambda: _allowed_transition_issue(graph),
        lambda: _transition_authority_issue(contract, graph),
    )
    return _first_check_issue(checks)


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


def _build_graph(
    contract: runtime_progression_stages.RuntimeProgressionStagesContract,
) -> RuntimeProgressionGraph:
    stages = contract.stages
    return RuntimeProgressionGraph(
        stages=stages,
        stages_by_name=runtime_progression_stages.stage_by_name(contract),
        order_by_name={stage.stage_name: index for index, stage in enumerate(stages)},
    )


def _current_state_issue(
    contract: runtime_progression_stages.RuntimeProgressionStagesContract,
) -> RuntimeProgressionStagesIssue | None:
    state = contract.current_state
    return _first_issue(
        _expected_value_issue(contract.architecture, _EXPECTED_ARCHITECTURE, "wrong_architecture", "architecture"),
        _expected_value_issue(state.path, _EXPECTED_RUNTIME_PATH, "wrong_runtime_path", "current_state.path"),
        _expected_value_issue(state.terminal_behavior, _EXPECTED_TERMINAL_BEHAVIOR, "wrong_terminal_behavior", "current_state.terminal_behavior"),
    )


def _current_contract_reference_issue(
    contract: runtime_progression_stages.RuntimeProgressionStagesContract,
) -> RuntimeProgressionStagesIssue | None:
    state = contract.current_state
    return _first_issue(
        _contract_reference_issue(state.halt_contract, "current_state.halt_contract"),
        _contract_reference_issue(state.progression_contract, "current_state.progression_contract"),
        _contract_reference_issue(state.progression_entry_contract, "current_state.progression_entry_contract"),
    )


def _duplicate_stage_issue(
    contract: runtime_progression_stages.RuntimeProgressionStagesContract,
) -> RuntimeProgressionStagesIssue | None:
    stage_ids = tuple(stage.stage_id for stage in contract.stages)
    stage_names = runtime_progression_stages.stage_names(contract)
    if len(stage_ids) != len(set(stage_ids)):
        return _issue("duplicate_stage_id", "stages.stage_id", "Runtime progression stage identifiers must be unique")
    if len(stage_names) != len(set(stage_names)):
        return _issue("duplicate_stage_name", "stages.stage_name", "Runtime progression stage names must be unique")
    return None


def _required_stage_issue(
    contract: runtime_progression_stages.RuntimeProgressionStagesContract,
) -> RuntimeProgressionStagesIssue | None:
    actual = set(runtime_progression_stages.stage_names(contract))
    missing = sorted(_REQUIRED_STAGE_NAMES - actual)
    if missing:
        return _issue("missing_stage", "stages", f"Required runtime progression stage is missing: {missing[0]}")
    unexpected = sorted(actual - _REQUIRED_STAGE_NAMES)
    if unexpected:
        field = f"stages.{unexpected[0]}"
        return _issue("unknown_stage_reference", field, f"Unknown runtime progression stage: {unexpected[0]}")
    return None


def _stage_id_issue(
    contract: runtime_progression_stages.RuntimeProgressionStagesContract,
) -> RuntimeProgressionStagesIssue | None:
    actual = tuple(stage.stage_id for stage in contract.stages)
    expected = tuple(range(len(contract.stages)))
    if actual == expected:
        return None
    return _issue("non_monotonic_stage_id", "stages.stage_id", "Stage identifiers must be contiguous and follow contract order")


def _stage_content_issue(
    contract: runtime_progression_stages.RuntimeProgressionStagesContract,
) -> RuntimeProgressionStagesIssue | None:
    for stage in contract.stages:
        issue = _first_issue(
            _non_empty_issue(stage.required_evidence, "missing_evidence_requirement", f"stages.{stage.stage_name}.required_evidence"),
            _non_empty_issue(stage.required_contracts, "missing_contract_requirement", f"stages.{stage.stage_name}.required_contracts"),
            _non_empty_issue(stage.required_validators, "missing_validator_requirement", f"stages.{stage.stage_name}.required_validators"),
            _non_empty_issue(stage.forbidden_shortcuts, "missing_forbidden_shortcut", f"stages.{stage.stage_name}.forbidden_shortcuts"),
            _required_stage_evidence_issue(stage),
            _required_contract_issue(stage),
            _required_validator_issue(stage),
        )
        if issue is not None:
            return issue
    return None


def _required_stage_evidence_issue(
    stage: runtime_progression_stages.RuntimeProgressionStage,
) -> RuntimeProgressionStagesIssue | None:
    expected = _REQUIRED_STAGE_EVIDENCE[stage.stage_name]
    if expected in stage.required_evidence:
        return None
    field = f"stages.{stage.stage_name}.required_evidence.{expected}"
    return _issue("missing_evidence_requirement", field, f"Stage must declare required evidence: {expected}")


def _required_contract_issue(
    stage: runtime_progression_stages.RuntimeProgressionStage,
) -> RuntimeProgressionStagesIssue | None:
    for reference in stage.required_contracts:
        issue = _authority_contract_issue(reference, f"stages.{stage.stage_name}.required_contracts")
        if issue is not None:
            return issue
    return None


def _required_validator_issue(
    stage: runtime_progression_stages.RuntimeProgressionStage,
) -> RuntimeProgressionStagesIssue | None:
    for reference in stage.required_validators:
        if reference in CHECKS or _is_planned_reference(reference):
            continue
        return _issue("unknown_required_validator", f"stages.{stage.stage_name}.required_validators.{reference}", f"Unknown required validator: {reference}")
    return None


def _prerequisite_reference_issue(
    graph: RuntimeProgressionGraph,
) -> RuntimeProgressionStagesIssue | None:
    known = set(graph.stages_by_name)
    for stage in graph.stages:
        for prerequisite in stage.required_prerequisites:
            if prerequisite not in known:
                field = f"stages.{stage.stage_name}.required_prerequisites.{prerequisite}"
                return _issue("unknown_stage_reference", field, f"Unknown prerequisite stage: {prerequisite}")
    return None


def _mandatory_prerequisite_issue(
    graph: RuntimeProgressionGraph,
) -> RuntimeProgressionStagesIssue | None:
    for index, stage in enumerate(graph.stages):
        if index == 0 or stage.required_prerequisites:
            continue
        field = f"stages.{stage.stage_name}.required_prerequisites"
        return _issue("missing_prerequisite", field, "Every stage after the initial stage must declare a prerequisite")
    return None


def _direct_cycle_issue(
    graph: RuntimeProgressionGraph,
) -> RuntimeProgressionStagesIssue | None:
    for stage in graph.stages:
        if stage.stage_name in stage.required_prerequisites:
            field = f"stages.{stage.stage_name}.required_prerequisites.{stage.stage_name}"
            return _issue("direct_cycle", field, f"Stage cannot require itself: {stage.stage_name}")
    return None


def _indirect_cycle_issue(
    graph: RuntimeProgressionGraph,
) -> RuntimeProgressionStagesIssue | None:
    remaining = {stage.stage_name: set(stage.required_prerequisites) for stage in graph.stages}
    while remaining:
        ready = sorted(name for name, prerequisites in remaining.items() if not prerequisites)
        if not ready:
            stage_name = min(remaining, key=graph.order_by_name.get)
            field = f"stages.{stage_name}.required_prerequisites"
            return _issue("indirect_cycle", field, "Runtime progression prerequisites contain an indirect cycle")
        _remove_ready_stages(remaining, ready)
    return None


def _remove_ready_stages(
    remaining: dict[str, set[str]],
    ready: list[str],
) -> None:
    for stage_name in ready:
        remaining.pop(stage_name)
    for prerequisites in remaining.values():
        prerequisites.difference_update(ready)


def _prerequisite_order_issue(
    graph: RuntimeProgressionGraph,
) -> RuntimeProgressionStagesIssue | None:
    for stage in graph.stages:
        for prerequisite in stage.required_prerequisites:
            if graph.order_by_name[prerequisite] < graph.order_by_name[stage.stage_name]:
                continue
            field = f"stages.{stage.stage_name}.required_prerequisites.{prerequisite}"
            return _issue("forward_prerequisite", field, f"Prerequisite must reference an earlier stage: {prerequisite}")
    return None


def _stage_status_issue(
    graph: RuntimeProgressionGraph,
) -> RuntimeProgressionStagesIssue | None:
    for stage in graph.stages:
        if stage.status != "proven":
            continue
        for prerequisite in stage.required_prerequisites:
            if graph.stages_by_name[prerequisite].status == "proven":
                continue
            field = f"stages.{stage.stage_name}.status"
            return _issue("unproven_prerequisite", field, f"Proven stage requires unproven stage: {prerequisite}")
    return None


def _allowed_transition_issue(
    graph: RuntimeProgressionGraph,
) -> RuntimeProgressionStagesIssue | None:
    for index, stage in enumerate(graph.stages):
        issue = _stage_transition_issue(graph, index, stage)
        if issue is not None:
            return issue
    return None


def _stage_transition_issue(
    graph: RuntimeProgressionGraph,
    index: int,
    stage: runtime_progression_stages.RuntimeProgressionStage,
) -> RuntimeProgressionStagesIssue | None:
    expected = graph.stages[index + 1].stage_name if index + 1 < len(graph.stages) else None
    actual = stage.allowed_next_stages[0] if stage.allowed_next_stages else None
    field = f"stages.{stage.stage_name}.allowed_next_stages"
    if actual is not None and actual not in graph.stages_by_name:
        return _issue("unknown_stage_reference", field, f"Allowed transition references unknown stage: {actual}")
    if actual is not None and graph.order_by_name[actual] <= index:
        return _issue("backward_transition", field, f"Allowed transition moves backward to: {actual}")
    if actual != expected:
        return _issue("skipped_mandatory_stage", field, f"Allowed transition must advance to: {expected}")
    return None


def _transition_authority_issue(
    contract: runtime_progression_stages.RuntimeProgressionStagesContract,
    graph: RuntimeProgressionGraph,
) -> RuntimeProgressionStagesIssue | None:
    transition_map: dict[tuple[str, str], list[str]] = {}
    for transition in contract.transitions:
        edge = (transition.from_stage, transition.to_stage)
        transition_map.setdefault(edge, []).append(transition.owner_contract)
    checks = (
        lambda: _transition_reference_issue(transition_map, graph),
        lambda: _duplicate_transition_owner_issue(transition_map),
        lambda: _transition_alignment_issue(transition_map, graph),
        lambda: _transition_owner_reference_issue(transition_map),
    )
    return _first_check_issue(checks)


def _transition_reference_issue(
    transition_map: dict[tuple[str, str], list[str]],
    graph: RuntimeProgressionGraph,
) -> RuntimeProgressionStagesIssue | None:
    for from_stage, to_stage in transition_map:
        if from_stage not in graph.stages_by_name or to_stage not in graph.stages_by_name:
            field = f"transitions.{from_stage}.{to_stage}"
            return _issue("unknown_stage_reference", field, "Transition ownership references an unknown stage")
    return None


def _duplicate_transition_owner_issue(
    transition_map: dict[tuple[str, str], list[str]],
) -> RuntimeProgressionStagesIssue | None:
    for edge, owners in transition_map.items():
        if len(owners) > 1:
            field = f"transitions.{edge[0]}.{edge[1]}.owner_contract"
            return _issue("duplicate_transition_ownership", field, "A transition must have exactly one owner contract")
    return None


def _transition_alignment_issue(
    transition_map: dict[tuple[str, str], list[str]],
    graph: RuntimeProgressionGraph,
) -> RuntimeProgressionStagesIssue | None:
    expected = _expected_transition_edges(graph)
    actual = set(transition_map)
    if actual == expected:
        return None
    return _issue("transition_ownership_mismatch", "transitions", "Transition ownership must match every allowed stage transition exactly")


def _expected_transition_edges(graph: RuntimeProgressionGraph) -> set[tuple[str, str]]:
    return {
        (stage.stage_name, stage.allowed_next_stages[0])
        for stage in graph.stages
        if stage.allowed_next_stages
    }


def _transition_owner_reference_issue(
    transition_map: dict[tuple[str, str], list[str]],
) -> RuntimeProgressionStagesIssue | None:
    for edge, owners in transition_map.items():
        field = f"transitions.{edge[0]}.{edge[1]}.owner_contract"
        issue = _authority_contract_issue(owners[0], field)
        if issue is not None:
            return issue
    return None


def _authority_contract_issue(
    reference: str,
    field: str,
) -> RuntimeProgressionStagesIssue | None:
    if _is_planned_reference(reference):
        return None
    if reference.startswith("contracts/") and runtime_progression_stages.contract_repo_path(reference).is_file():
        return None
    return _issue("unknown_required_contract", f"{field}.{reference}", f"Unknown required contract: {reference}")


def _contract_reference_issue(
    reference: str,
    field: str,
) -> RuntimeProgressionStagesIssue | None:
    if runtime_progression_stages.contract_repo_path(reference).is_file():
        return None
    return _issue("missing_contract_reference", field, f"Referenced contract is missing: {reference}")


def _is_planned_reference(reference: str) -> bool:
    return reference.startswith("planned:") and bool(reference.removeprefix("planned:"))


def _non_empty_issue(
    values: tuple[str, ...],
    reason: str,
    field: str,
) -> RuntimeProgressionStagesIssue | None:
    if values:
        return None
    return _issue(reason, field, f"Runtime progression stage must declare {field}")


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


def _expected_value_issue(
    actual: str,
    expected: str,
    reason: str,
    contract_field: str,
) -> RuntimeProgressionStagesIssue | None:
    if actual == expected:
        return None
    return _issue(reason, contract_field, f"Expected {contract_field} to be {expected}, got {actual}")


def _first_issue(
    *issues: RuntimeProgressionStagesIssue | None,
) -> RuntimeProgressionStagesIssue | None:
    for issue in issues:
        if issue is not None:
            return issue
    return None


def _first_check_issue(
    checks: tuple[Callable[[], RuntimeProgressionStagesIssue | None], ...],
) -> RuntimeProgressionStagesIssue | None:
    for check in checks:
        issue = check()
        if issue is not None:
            return issue
    return None


def _issue(reason: str, contract_field: str, detail: str) -> RuntimeProgressionStagesIssue:
    return RuntimeProgressionStagesIssue(reason=reason, contract_field=contract_field, detail=detail)


def _failure(issue: RuntimeProgressionStagesIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=RUNTIME_PROGRESSION_STAGES_INVALID,
        detail=issue.detail,
        action="Keep runtime progression acyclic, monotonic, and subordinate to the halt contract",
        meta={
            "reason": issue.reason,
            "contract_field": issue.contract_field,
        },
    )
