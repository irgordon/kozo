from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.abi_manifest import ROOT
from harness.validators_impl.schema import validate_named_document

CONTRACT_PATH = ROOT / "contracts" / "runtime_progression_stages.v0.json"


@dataclass(frozen=True)
class RuntimeProgressionStageState:
    path: str
    halt_contract: str
    progression_contract: str
    progression_entry_contract: str
    terminal_behavior: str


@dataclass(frozen=True)
class RuntimeProgressionStage:
    stage_id: int
    stage_name: str
    description: str
    status: str
    required_prerequisites: tuple[str, ...]
    required_evidence: tuple[str, ...]
    required_contracts: tuple[str, ...]
    required_validators: tuple[str, ...]
    allowed_next_stages: tuple[str, ...]
    forbidden_shortcuts: tuple[str, ...]


@dataclass(frozen=True)
class RuntimeProgressionTransition:
    from_stage: str
    to_stage: str
    owner_contract: str


@dataclass(frozen=True)
class RuntimeProgressionStagesContract:
    version: int
    architecture: str
    current_state: RuntimeProgressionStageState
    stages: tuple[RuntimeProgressionStage, ...]
    transitions: tuple[RuntimeProgressionTransition, ...]
    transition_requirements: tuple[str, ...]
    forbidden_global_shortcuts: tuple[str, ...]
    non_goals: tuple[str, ...]


def load_runtime_progression_stages_contract(path: Path = CONTRACT_PATH) -> RuntimeProgressionStagesContract:
    data = load_contract_json(path)
    validate_contract_shape(data)
    return parse_runtime_progression_stages_contract(data)


def load_contract_json(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    return json.loads(path.read_text())


def validate_contract_shape(data: dict[str, Any]) -> None:
    validate_named_document("runtime_progression_stages", data)


def parse_runtime_progression_stages_contract(data: dict[str, Any]) -> RuntimeProgressionStagesContract:
    return RuntimeProgressionStagesContract(
        data["version"],
        data["architecture"],
        _current_state(data),
        _stages(data),
        _transitions(data),
        tuple(data["transition_requirements"]),
        tuple(data["forbidden_global_shortcuts"]),
        tuple(data["non_goals"]),
    )


def contract_repo_path(contract_path: str) -> Path:
    path = Path(contract_path)
    if path.is_absolute():
        return path
    return ROOT / path


def stage_names(contract: RuntimeProgressionStagesContract) -> tuple[str, ...]:
    return tuple(stage.stage_name for stage in contract.stages)


def stage_by_name(
    contract: RuntimeProgressionStagesContract,
) -> dict[str, RuntimeProgressionStage]:
    return {stage.stage_name: stage for stage in contract.stages}


def _current_state(data: dict[str, Any]) -> RuntimeProgressionStageState:
    state = data["current_state"]
    return RuntimeProgressionStageState(
        state["path"],
        state["halt_contract"],
        state["progression_contract"],
        state["progression_entry_contract"],
        state["terminal_behavior"],
    )


def _stages(data: dict[str, Any]) -> tuple[RuntimeProgressionStage, ...]:
    return tuple(_stage(stage) for stage in data["stages"])


def _transitions(data: dict[str, Any]) -> tuple[RuntimeProgressionTransition, ...]:
    return tuple(_transition(transition) for transition in data["transitions"])


def _stage(data: dict[str, Any]) -> RuntimeProgressionStage:
    return RuntimeProgressionStage(
        data["stage_id"],
        data["stage_name"],
        data["description"],
        data["status"],
        tuple(data["required_prerequisites"]),
        tuple(data["required_evidence"]),
        tuple(data["required_contracts"]),
        tuple(data["required_validators"]),
        tuple(data["allowed_next_stages"]),
        tuple(data["forbidden_shortcuts"]),
    )


def _transition(data: dict[str, Any]) -> RuntimeProgressionTransition:
    return RuntimeProgressionTransition(
        data["from_stage"],
        data["to_stage"],
        data["owner_contract"],
    )
