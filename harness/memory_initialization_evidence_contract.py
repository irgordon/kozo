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


@dataclass(frozen=True)
class ControlledMemoryRegion:
    source_file: str
    section: str
    start_symbol: str
    end_symbol: str
    size_bytes: int
    alignment_bytes: int
    allocation_mode: str
    owner: str
    lifetime: str


@dataclass(frozen=True)
class InitializationOperation:
    operation: str
    coverage: str
    fill_value: int
    width_bytes: int
    required_before_probe: bool


@dataclass(frozen=True)
class SurvivalProbe:
    offset_bytes: int
    write_width_bytes: int
    sentinel_value: str
    comparison: str
    required_steps: tuple[str, ...]
    required_before_marker: bool


@dataclass(frozen=True)
class MarkerPlacement:
    reserved_marker: str
    marker_status: str
    marker_emitted: bool
    required_after: tuple[str, ...]
    required_before: str
    emission_owner: str


@dataclass(frozen=True)
class MemoryInitializationEvidenceContract:
    version: int
    architecture: str
    current_state: MemoryEvidenceState
    memory_definition: MemoryDefinition
    controlled_region: ControlledMemoryRegion
    initialization_operation: InitializationOperation
    survival_probe: SurvivalProbe
    marker_placement: MarkerPlacement
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
        _controlled_region(data),
        _initialization_operation(data),
        _survival_probe(data),
        _marker_placement(data),
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
    return MemoryDefinition(definition["description"])


def _controlled_region(data: dict[str, Any]) -> ControlledMemoryRegion:
    region = data["controlled_region"]
    return ControlledMemoryRegion(
        region["source_file"], region["section"], region["start_symbol"],
        region["end_symbol"], region["size_bytes"], region["alignment_bytes"],
        region["allocation_mode"], region["owner"], region["lifetime"],
    )


def _initialization_operation(data: dict[str, Any]) -> InitializationOperation:
    operation = data["initialization_operation"]
    return InitializationOperation(
        operation["operation"], operation["coverage"], operation["fill_value"],
        operation["width_bytes"], operation["required_before_probe"],
    )


def _survival_probe(data: dict[str, Any]) -> SurvivalProbe:
    probe = data["survival_probe"]
    return SurvivalProbe(
        probe["offset_bytes"], probe["write_width_bytes"], probe["sentinel_value"],
        probe["comparison"], tuple(probe["required_steps"]), probe["required_before_marker"],
    )


def _marker_placement(data: dict[str, Any]) -> MarkerPlacement:
    marker = data["marker_placement"]
    return MarkerPlacement(
        marker["reserved_marker"], marker["marker_status"], marker["marker_emitted"],
        tuple(marker["required_after"]), marker["required_before"], marker["emission_owner"],
    )
