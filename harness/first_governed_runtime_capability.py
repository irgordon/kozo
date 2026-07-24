from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.abi_manifest import ROOT
from harness.validators_impl.schema import validate_named_document

CONTRACT_PATH = ROOT / "contracts" / "first_governed_runtime_capability.v0.json"


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
class LayoutField:
    name: str
    offset_bytes: int
    width_bytes: int


@dataclass(frozen=True)
class RequestDefinition:
    version: int
    size_bytes: int
    alignment_bytes: int
    supported_flags: int
    aliasing_policy: str
    fields: tuple[LayoutField, ...]
    required_zero_fields: tuple[str, ...]


@dataclass(frozen=True)
class ResponseDefinition:
    version: int
    size_bytes: int
    alignment_bytes: int
    reported_progression_stage: int
    proven_stage_mask: int
    fields: tuple[LayoutField, ...]
    expected_values: dict[str, int]


@dataclass(frozen=True)
class MarkerDefinition:
    required_after: str
    required_before: str
    emission_owner: str
    ordered_sequence: tuple[str, ...]


@dataclass(frozen=True)
class FirstGovernedRuntimeCapabilityContract:
    version: int
    architecture: str
    capability: CapabilityDefinition
    request: RequestDefinition
    response: ResponseDefinition
    statuses: dict[str, int]
    markers: MarkerDefinition
    execution_order: tuple[str, ...]
    terminal_behavior: dict[str, Any]
    required_evidence: tuple[str, ...]
    transition_ownership: tuple[str, ...]
    claim_boundary: dict[str, tuple[str, ...]]
    non_goals: tuple[str, ...]


def load_first_governed_runtime_capability(
    path: Path = CONTRACT_PATH,
) -> FirstGovernedRuntimeCapabilityContract:
    data = json.loads(path.read_text())
    validate_named_document("first_governed_runtime_capability", data)
    return _parse_contract(data)


def _parse_contract(data: dict[str, Any]) -> FirstGovernedRuntimeCapabilityContract:
    return FirstGovernedRuntimeCapabilityContract(
        version=data["version"],
        architecture=data["architecture"],
        capability=CapabilityDefinition(**data["capability"]),
        request=_parse_request(data["request"]),
        response=_parse_response(data["response"]),
        statuses=dict(data["statuses"]),
        markers=_parse_markers(data["markers"]),
        execution_order=tuple(data["execution_order"]),
        terminal_behavior=dict(data["terminal_behavior"]),
        required_evidence=tuple(data["required_evidence"]),
        transition_ownership=tuple(data["transition_ownership"]),
        claim_boundary={
            key: tuple(values)
            for key, values in data["claim_boundary"].items()
        },
        non_goals=tuple(data["non_goals"]),
    )


def _parse_request(data: dict[str, Any]) -> RequestDefinition:
    return RequestDefinition(
        version=data["version"],
        size_bytes=data["size_bytes"],
        alignment_bytes=data["alignment_bytes"],
        supported_flags=data["supported_flags"],
        aliasing_policy=data["aliasing_policy"],
        fields=_parse_fields(data["fields"]),
        required_zero_fields=tuple(data["required_zero_fields"]),
    )


def _parse_response(data: dict[str, Any]) -> ResponseDefinition:
    return ResponseDefinition(
        version=data["version"],
        size_bytes=data["size_bytes"],
        alignment_bytes=data["alignment_bytes"],
        reported_progression_stage=data["reported_progression_stage"],
        proven_stage_mask=data["proven_stage_mask"],
        fields=_parse_fields(data["fields"]),
        expected_values=dict(data["expected_values"]),
    )


def _parse_fields(fields: list[dict[str, Any]]) -> tuple[LayoutField, ...]:
    return tuple(LayoutField(**field) for field in fields)


def _parse_markers(data: dict[str, Any]) -> MarkerDefinition:
    return MarkerDefinition(
        required_after=data["required_after"],
        required_before=data["required_before"],
        emission_owner=data["emission_owner"],
        ordered_sequence=tuple(data["ordered_sequence"]),
    )
