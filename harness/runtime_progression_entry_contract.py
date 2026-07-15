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
    source_file: str
    assembly_entry_symbol: str
    target_symbol: str


@dataclass(frozen=True)
class CallingConvention:
    name: str
    argument_registers: tuple[str, ...]
    return_register: str
    caller_saved_registers: tuple[str, ...]
    callee_saved_registers: tuple[str, ...]
    call_site_stack_alignment_bytes: int
    callee_entry_stack_modulo_bytes: int
    red_zone_policy: str


@dataclass(frozen=True)
class ContextField:
    name: str
    offset_bytes: int
    width_bytes: int


@dataclass(frozen=True)
class BootstrapContext:
    version: int
    size_bytes: int
    symbol: str
    fields: tuple[ContextField, ...]
    required_zero_fields: tuple[str, ...]
    ownership: str
    lifetime: str


@dataclass(frozen=True)
class RuntimeInitialization:
    source_file: str
    entry_symbol: str
    marker: str
    marker_emission_owner: str
    serial_bridge_symbol: str
    state_symbol: str
    state_sentinel: str
    operation: str
    success_status: int


@dataclass(frozen=True)
class ReturnBoundary:
    marker: str
    status: str
    emitted: bool
    required_status: int
    terminal_behavior: str


@dataclass(frozen=True)
class RuntimeProgressionEntryContract:
    version: int
    architecture: str
    current_state: CurrentRuntimeState
    progression_entry: ProgressionEntry
    calling_convention: CallingConvention
    bootstrap_context: BootstrapContext
    runtime_initialization: RuntimeInitialization
    return_boundary: ReturnBoundary
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
        _calling_convention(data),
        _bootstrap_context(data),
        _runtime_initialization(data),
        _return_boundary(data),
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
        entry["source_file"],
        entry["assembly_entry_symbol"],
        entry["target_symbol"],
    )


def _calling_convention(data: dict[str, Any]) -> CallingConvention:
    convention = data["calling_convention"]
    return CallingConvention(
        convention["name"], tuple(convention["argument_registers"]), convention["return_register"],
        tuple(convention["caller_saved_registers"]), tuple(convention["callee_saved_registers"]),
        convention["call_site_stack_alignment_bytes"], convention["callee_entry_stack_modulo_bytes"],
        convention["red_zone_policy"],
    )


def _bootstrap_context(data: dict[str, Any]) -> BootstrapContext:
    context = data["bootstrap_context"]
    fields = tuple(ContextField(field["name"], field["offset_bytes"], field["width_bytes"]) for field in context["fields"])
    return BootstrapContext(
        context["version"], context["size_bytes"], context["symbol"], fields,
        tuple(context["required_zero_fields"]), context["ownership"], context["lifetime"],
    )


def _runtime_initialization(data: dict[str, Any]) -> RuntimeInitialization:
    runtime = data["runtime_initialization"]
    return RuntimeInitialization(
        runtime["source_file"], runtime["entry_symbol"], runtime["marker"], runtime["marker_emission_owner"],
        runtime["serial_bridge_symbol"], runtime["state_symbol"], runtime["state_sentinel"],
        runtime["operation"], runtime["success_status"],
    )


def _return_boundary(data: dict[str, Any]) -> ReturnBoundary:
    boundary = data["return_boundary"]
    return ReturnBoundary(
        boundary["marker"], boundary["status"], boundary["emitted"],
        boundary["required_status"], boundary["terminal_behavior"],
    )
