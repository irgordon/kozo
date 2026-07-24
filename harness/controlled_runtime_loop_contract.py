from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.abi_manifest import ROOT
from harness.validators_impl.schema import validate_named_document

CONTRACT_PATH = ROOT / "contracts" / "controlled_runtime_loop_contract.v0.json"


@dataclass(frozen=True)
class CurrentState:
    stage: str
    status: str
    source_file: str
    entry_symbol: str
    predecessor_stage: str
    successor_stage: str
    halt_contract: str
    progression_stages_contract: str


@dataclass(frozen=True)
class LoopDefinition:
    iteration_limit: int
    iteration_index_origin: int
    completion_condition: str
    backward_edge_required: bool
    binary_evidence: str


@dataclass(frozen=True)
class StateField:
    name: str
    width_bits: int
    initial_value: int
    final_value: int


@dataclass(frozen=True)
class StateDefinition:
    symbol: str
    storage: str
    owner: str
    volatile_access_required: bool
    fields: tuple[StateField, ...]


@dataclass(frozen=True)
class MarkerDefinition:
    required_after: str
    required_before: str
    emission_owner: str
    ordered_sequence: tuple[str, ...]


@dataclass(frozen=True)
class ControlledRuntimeLoopContract:
    version: int
    architecture: str
    current_state: CurrentState
    loop: LoopDefinition
    state: StateDefinition
    accumulator: dict[str, Any]
    markers: MarkerDefinition
    statuses: dict[str, int]
    terminal_behavior: dict[str, Any]
    required_evidence: tuple[str, ...]
    transition_ownership: tuple[str, ...]
    non_goals: tuple[str, ...]


def load_controlled_runtime_loop_contract(
    path: Path = CONTRACT_PATH,
) -> ControlledRuntimeLoopContract:
    data = json.loads(path.read_text())
    validate_named_document("controlled_runtime_loop_contract", data)
    return _parse_contract(data)


def contract_repo_path(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


def _parse_contract(data: dict[str, Any]) -> ControlledRuntimeLoopContract:
    return ControlledRuntimeLoopContract(
        version=data["version"],
        architecture=data["architecture"],
        current_state=_parse_current_state(data["current_state"]),
        loop=_parse_loop(data["loop"]),
        state=_parse_state(data["state"]),
        accumulator=dict(data["accumulator"]),
        markers=_parse_markers(data["markers"]),
        statuses=dict(data["statuses"]),
        terminal_behavior=dict(data["terminal_behavior"]),
        required_evidence=tuple(data["required_evidence"]),
        transition_ownership=tuple(data["transition_ownership"]),
        non_goals=tuple(data["non_goals"]),
    )


def _parse_current_state(data: dict[str, Any]) -> CurrentState:
    return CurrentState(**data)


def _parse_loop(data: dict[str, Any]) -> LoopDefinition:
    return LoopDefinition(**data)


def _parse_state(data: dict[str, Any]) -> StateDefinition:
    fields = tuple(StateField(**field) for field in data["fields"])
    return StateDefinition(
        symbol=data["symbol"],
        storage=data["storage"],
        owner=data["owner"],
        volatile_access_required=data["volatile_access_required"],
        fields=fields,
    )


def _parse_markers(data: dict[str, Any]) -> MarkerDefinition:
    return MarkerDefinition(
        required_after=data["required_after"],
        required_before=data["required_before"],
        emission_owner=data["emission_owner"],
        ordered_sequence=tuple(data["ordered_sequence"]),
    )
