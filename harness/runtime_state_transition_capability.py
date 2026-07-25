from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.abi_manifest import ROOT
from harness.validators_impl.schema import validate_named_document

CONTRACT_PATH = ROOT / "contracts" / "runtime_state_transition_capability.v0.json"


@dataclass(frozen=True)
class LayoutField:
    name: str
    offset_bytes: int
    width_bytes: int


@dataclass(frozen=True)
class CapabilityDefinition:
    canonical_name: str
    canonical_identifier: str
    numeric_identifier: int
    stage_id: int
    status: str
    source_file: str
    entry_symbol: str
    dispatcher_symbol: str
    handler_symbol: str


@dataclass(frozen=True)
class StateDefinition:
    symbol: str
    size_bytes: int
    alignment_bytes: int
    ownership: str
    lifetime: str
    fields: tuple[LayoutField, ...]
    initial_values: dict[str, int]
    terminal_values: dict[str, int]
    volatile_access_required: bool
    concurrency_safe: bool
    persistent: bool


@dataclass(frozen=True)
class BoundaryDefinition:
    version: int
    size_bytes: int
    alignment_bytes: int
    fields: tuple[LayoutField, ...]
    values: dict[str, int]
    required_zero_fields: tuple[str, ...]
    supported_flags: int | None = None
    aliasing_policy: str | None = None


@dataclass(frozen=True)
class MarkerDefinition:
    required_after: str
    required_before: str
    emission_owner: str
    ordered_sequence: tuple[str, ...]
    generic_dispatch_marker_repeated: bool


@dataclass(frozen=True)
class RuntimeStateTransitionCapabilityContract:
    version: int
    architecture: str
    capability: CapabilityDefinition
    state: StateDefinition
    request: BoundaryDefinition
    response: BoundaryDefinition
    transition: dict[str, Any]
    statuses: dict[str, int]
    markers: MarkerDefinition
    execution_order: tuple[str, ...]
    failure_behavior: dict[str, Any]
    required_evidence: tuple[str, ...]
    claim_boundary: dict[str, tuple[str, ...]]
    non_goals: tuple[str, ...]


def load_runtime_state_transition_capability(
    path: Path = CONTRACT_PATH,
) -> RuntimeStateTransitionCapabilityContract:
    data = json.loads(path.read_text())
    validate_named_document("runtime_state_transition_capability", data)
    return _parse_contract(data)


def _parse_contract(data: dict[str, Any]) -> RuntimeStateTransitionCapabilityContract:
    return RuntimeStateTransitionCapabilityContract(
        version=data["version"],
        architecture=data["architecture"],
        capability=CapabilityDefinition(**data["capability"]),
        state=_parse_state(data["state"]),
        request=_parse_request(data["request"]),
        response=_parse_response(data["response"]),
        transition=dict(data["transition"]),
        statuses=dict(data["statuses"]),
        markers=MarkerDefinition(**{
            **data["markers"],
            "ordered_sequence": tuple(data["markers"]["ordered_sequence"]),
        }),
        execution_order=tuple(data["execution_order"]),
        failure_behavior=dict(data["failure_behavior"]),
        required_evidence=tuple(data["required_evidence"]),
        claim_boundary={
            key: tuple(values)
            for key, values in data["claim_boundary"].items()
        },
        non_goals=tuple(data["non_goals"]),
    )


def _parse_state(data: dict[str, Any]) -> StateDefinition:
    return StateDefinition(
        **{
            **data,
            "fields": _parse_fields(data["fields"]),
            "initial_values": dict(data["initial_values"]),
            "terminal_values": dict(data["terminal_values"]),
        }
    )


def _parse_request(data: dict[str, Any]) -> BoundaryDefinition:
    return BoundaryDefinition(
        version=data["version"],
        size_bytes=data["size_bytes"],
        alignment_bytes=data["alignment_bytes"],
        fields=_parse_fields(data["fields"]),
        values=dict(data["required_values"]),
        required_zero_fields=tuple(data["required_zero_fields"]),
        supported_flags=data["supported_flags"],
        aliasing_policy=data["aliasing_policy"],
    )


def _parse_response(data: dict[str, Any]) -> BoundaryDefinition:
    return BoundaryDefinition(
        version=data["version"],
        size_bytes=data["size_bytes"],
        alignment_bytes=data["alignment_bytes"],
        fields=_parse_fields(data["fields"]),
        values=dict(data["expected_values"]),
        required_zero_fields=tuple(data["required_zero_fields"]),
    )


def _parse_fields(fields: list[dict[str, Any]]) -> tuple[LayoutField, ...]:
    return tuple(LayoutField(**field) for field in fields)
