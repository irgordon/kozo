from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.abi_manifest import ROOT
from harness.validators_impl.schema import validate_named_document

CONTRACT_PATH = ROOT / "contracts" / "runtime_progression_entry_contract.v0.json"


@dataclass(frozen=True)
class CurrentRuntimeState:
    path: str
    halt_contract: str
    progression_contract: str
    progression_stages_contract: str
    final_smoke_marker: str
    terminal_behavior: str


@dataclass(frozen=True)
class ProgressionEntry:
    marker: str
    status: str
    emitted: bool
    entry_boundary: str


@dataclass(frozen=True)
class RuntimeProgressionEntryContract:
    version: int
    architecture: str
    current_state: CurrentRuntimeState
    progression_entry: ProgressionEntry
    required_prerequisites: tuple[str, ...]
    required_evidence: tuple[str, ...]
    transition_requirements: tuple[str, ...]
    forbidden_shortcuts: tuple[str, ...]
    transition_ownership: tuple[str, ...]
    non_goals: tuple[str, ...]


def load_runtime_progression_entry_contract(path: Path = CONTRACT_PATH) -> RuntimeProgressionEntryContract:
    data = load_contract_json(path)
    validate_contract_shape(data)
    return parse_runtime_progression_entry_contract(data)


def load_contract_json(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    return json.loads(path.read_text())


def validate_contract_shape(data: dict[str, Any]) -> None:
    validate_named_document("runtime_progression_entry_contract", data)


def parse_runtime_progression_entry_contract(data: dict[str, Any]) -> RuntimeProgressionEntryContract:
    return RuntimeProgressionEntryContract(
        data["version"],
        data["architecture"],
        _current_state(data),
        _progression_entry(data),
        tuple(data["required_prerequisites"]),
        tuple(data["required_evidence"]),
        tuple(data["transition_requirements"]),
        tuple(data["forbidden_shortcuts"]),
        tuple(data["transition_ownership"]),
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
        state["progression_contract"],
        state["progression_stages_contract"],
        state["final_smoke_marker"],
        state["terminal_behavior"],
    )


def _progression_entry(data: dict[str, Any]) -> ProgressionEntry:
    entry = data["progression_entry"]
    return ProgressionEntry(
        entry["marker"],
        entry["status"],
        entry["emitted"],
        entry["entry_boundary"],
    )
