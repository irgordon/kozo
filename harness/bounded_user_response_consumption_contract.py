from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.abi_manifest import ROOT
from harness.validators_impl.schema import validate_named_document

CONTRACT_PATH = ROOT / "contracts" / "bounded_user_response_consumption_contract.v0.json"


@dataclass(frozen=True)
class BoundedUserResponseConsumptionContract:
    version: int
    architecture: str
    source_files: dict[str, str]
    execution_point: dict[str, Any]
    transaction_phases: dict[str, Any]
    response_consumer: dict[str, Any]
    response: dict[str, Any]
    consumption_record: dict[str, Any]
    kernel_shadow: dict[str, Any]
    ring3_response_checks: tuple[str, ...]
    second_frame_validation: dict[str, Any]
    response_revalidation: dict[str, Any]
    record_copy: dict[str, Any]
    clearing: dict[str, Any]
    phase_reset: dict[str, Any]
    marker_order: tuple[str, ...]
    marker_ownership: dict[str, str]
    failure_statuses: dict[str, int]
    halt_behavior: dict[str, Any]
    claim_boundary: dict[str, tuple[str, ...]]
    non_goals: tuple[str, ...]


def load_bounded_user_response_consumption_contract(
    path: Path = CONTRACT_PATH,
) -> BoundedUserResponseConsumptionContract:
    data = json.loads(path.read_text())
    validate_named_document("bounded_user_response_consumption_contract", data)
    return _parse_contract(data)


def _parse_contract(data: dict[str, Any]) -> BoundedUserResponseConsumptionContract:
    values = dict(data)
    values["source_files"] = dict(data["source_files"])
    values["ring3_response_checks"] = tuple(data["ring3_response_checks"])
    values["marker_order"] = tuple(data["marker_order"])
    values["marker_ownership"] = dict(data["marker_ownership"])
    values["failure_statuses"] = dict(data["failure_statuses"])
    values["claim_boundary"] = {
        key: tuple(items) for key, items in data["claim_boundary"].items()
    }
    values["non_goals"] = tuple(data["non_goals"])
    return BoundedUserResponseConsumptionContract(**values)
