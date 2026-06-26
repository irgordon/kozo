from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.abi_manifest import ROOT
from harness.validators_impl.schema import validate_named_document

CONTRACT_PATH = ROOT / "contracts" / "memory_initialization_evidence_contract.v0.json"


@dataclass(frozen=True)
class MemoryEvidenceState:
    runtime_path: str
    halt_contract: str
    progression_stages_contract: str
    stack_initialization_evidence_contract: str
    stage: str
    implemented: bool


@dataclass(frozen=True)
class MemoryDefinition:
    description: str
    reserved_marker: str
    marker_status: str
    marker_emitted: bool


@dataclass(frozen=True)
class MemoryInitializationEvidenceContract:
    version: int
    architecture: str
    current_state: MemoryEvidenceState
    memory_definition: MemoryDefinition
    prerequisites: tuple[str, ...]
    evidence_requirements: tuple[str, ...]
    proof_boundary: tuple[str, ...]
    assumptions_enabled: tuple[str, ...]
    assumptions_not_enabled: tuple[str, ...]
    future_validators: tuple[str, ...]
    non_goals: tuple[str, ...]


def load_memory_initialization_evidence_contract(path: Path = CONTRACT_PATH) -> MemoryInitializationEvidenceContract:
    data = load_contract_json(path)
    validate_contract_shape(data)
    return parse_memory_initialization_evidence_contract(data)


def load_contract_json(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    return json.loads(path.read_text())


def validate_contract_shape(data: dict[str, Any]) -> None:
    validate_named_document("memory_initialization_evidence_contract", data)


def parse_memory_initialization_evidence_contract(data: dict[str, Any]) -> MemoryInitializationEvidenceContract:
    return MemoryInitializationEvidenceContract(
        data["version"],
        data["architecture"],
        _current_state(data),
        _memory_definition(data),
        tuple(data["prerequisites"]),
        tuple(data["evidence_requirements"]),
        tuple(data["proof_boundary"]),
        tuple(data["assumptions_enabled"]),
        tuple(data["assumptions_not_enabled"]),
        tuple(data["future_validators"]),
        tuple(data["non_goals"]),
    )


def contract_repo_path(contract_path: str) -> Path:
    path = Path(contract_path)
    if path.is_absolute():
        return path
    return ROOT / path


def _current_state(data: dict[str, Any]) -> MemoryEvidenceState:
    state = data["current_state"]
    return MemoryEvidenceState(
        state["runtime_path"],
        state["halt_contract"],
        state["progression_stages_contract"],
        state["stack_initialization_evidence_contract"],
        state["stage"],
        state["implemented"],
    )


def _memory_definition(data: dict[str, Any]) -> MemoryDefinition:
    definition = data["memory_definition"]
    return MemoryDefinition(
        definition["description"],
        definition["reserved_marker"],
        definition["marker_status"],
        definition["marker_emitted"],
    )
