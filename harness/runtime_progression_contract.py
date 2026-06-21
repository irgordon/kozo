from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.abi_manifest import ROOT
from harness.validators_impl.schema import validate_named_document

CONTRACT_PATH = ROOT / "contracts" / "runtime_progression_contract.v0.json"


@dataclass(frozen=True)
class CurrentRuntimeState:
    path: str
    halt_contract: str
    final_smoke_marker: str
    terminal_behavior: str


@dataclass(frozen=True)
class RuntimeMilestone:
    stage: int
    name: str
    status: str


@dataclass(frozen=True)
class RuntimeProgressionContract:
    version: int
    architecture: str
    current_state: CurrentRuntimeState
    progression_prerequisites: tuple[str, ...]
    transition_requirements: tuple[str, ...]
    forbidden_shortcuts: tuple[str, ...]
    future_runtime_milestones: tuple[RuntimeMilestone, ...]
    evidence_requirements: tuple[str, ...]
    non_goals: tuple[str, ...]


def load_runtime_progression_contract(path: Path = CONTRACT_PATH) -> RuntimeProgressionContract:
    data = load_contract_json(path)
    validate_contract_shape(data)
    return parse_runtime_progression_contract(data)


def load_contract_json(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    return json.loads(path.read_text())


def validate_contract_shape(data: dict[str, Any]) -> None:
    validate_named_document("runtime_progression_contract", data)


def parse_runtime_progression_contract(data: dict[str, Any]) -> RuntimeProgressionContract:
    return RuntimeProgressionContract(
        data["version"],
        data["architecture"],
        _current_state(data),
        tuple(data["progression_prerequisites"]),
        tuple(data["transition_requirements"]),
        tuple(data["forbidden_shortcuts"]),
        _runtime_milestones(data),
        tuple(data["evidence_requirements"]),
        tuple(data["non_goals"]),
    )


def contract_repo_path(contract_path: str) -> Path:
    path = Path(contract_path)
    if path.is_absolute():
        return path
    return ROOT / path


def _current_state(data: dict[str, Any]) -> CurrentRuntimeState:
    state = data["current_state"]
    return CurrentRuntimeState(
        state["path"],
        state["halt_contract"],
        state["final_smoke_marker"],
        state["terminal_behavior"],
    )


def _runtime_milestones(data: dict[str, Any]) -> tuple[RuntimeMilestone, ...]:
    return tuple(
        RuntimeMilestone(milestone["stage"], milestone["name"], milestone["status"])
        for milestone in data["future_runtime_milestones"]
    )
