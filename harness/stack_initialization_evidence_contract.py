from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.abi_manifest import ROOT
from harness.validators_impl.schema import validate_named_document

CONTRACT_PATH = ROOT / "contracts" / "stack_initialization_evidence_contract.v0.json"


@dataclass(frozen=True)
class StackEvidenceState:
    runtime_path: str
    halt_contract: str
    progression_stages_contract: str
    stage: str
    implemented: bool


@dataclass(frozen=True)
class StackDefinition:
    description: str
    reserved_marker: str
    marker_status: str
    marker_emitted: bool
    source_file: str
    stack_symbol: str
    stack_top_symbol: str
    stack_size_bytes: int
    stack_pointer_register: str


@dataclass(frozen=True)
class StackInitializationEvidenceContract:
    version: int
    architecture: str
    current_state: StackEvidenceState
    stack_definition: StackDefinition
    prerequisites: tuple[str, ...]
    evidence_requirements: tuple[str, ...]
    proof_boundary: tuple[str, ...]
    assumptions_enabled: tuple[str, ...]
    assumptions_not_enabled: tuple[str, ...]
    future_validators: tuple[str, ...]
    non_goals: tuple[str, ...]


def load_stack_initialization_evidence_contract(path: Path = CONTRACT_PATH) -> StackInitializationEvidenceContract:
    data = load_contract_json(path)
    validate_contract_shape(data)
    return parse_stack_initialization_evidence_contract(data)


def load_contract_json(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    return json.loads(path.read_text())


def validate_contract_shape(data: dict[str, Any]) -> None:
    validate_named_document("stack_initialization_evidence_contract", data)


def parse_stack_initialization_evidence_contract(data: dict[str, Any]) -> StackInitializationEvidenceContract:
    return StackInitializationEvidenceContract(
        data["version"],
        data["architecture"],
        _current_state(data),
        _stack_definition(data),
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


def _current_state(data: dict[str, Any]) -> StackEvidenceState:
    state = data["current_state"]
    return StackEvidenceState(
        state["runtime_path"],
        state["halt_contract"],
        state["progression_stages_contract"],
        state["stage"],
        state["implemented"],
    )


def _stack_definition(data: dict[str, Any]) -> StackDefinition:
    definition = data["stack_definition"]
    return StackDefinition(
        definition["description"],
        definition["reserved_marker"],
        definition["marker_status"],
        definition["marker_emitted"],
        definition["source_file"],
        definition["stack_symbol"],
        definition["stack_top_symbol"],
        definition["stack_size_bytes"],
        definition["stack_pointer_register"],
    )
