from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.abi_manifest import ROOT
from harness.validators_impl.schema import validate_named_document

CONTRACT_PATH = ROOT / "contracts" / "fixed_user_runtime_status_service_contract.v0.json"


@dataclass(frozen=True)
class FixedUserRuntimeStatusServiceContract:
    version: int
    architecture: str
    runtime_ordering: dict[str, Any]
    shared_status: dict[str, Any]
    request: dict[str, Any]
    response: dict[str, Any]
    feature_mask_bits: tuple[dict[str, Any], ...]
    ring3_validation: dict[str, Any]
    ring0_revalidation: dict[str, Any]
    cleanup: dict[str, Any]
    marker_order: tuple[str, ...]
    failure_behavior: dict[str, Any]
    claim_boundary: dict[str, tuple[str, ...]]
    non_goals: tuple[str, ...]


def load_fixed_user_runtime_status_service_contract(
    path: Path = CONTRACT_PATH,
) -> FixedUserRuntimeStatusServiceContract:
    data = json.loads(path.read_text())
    validate_named_document("fixed_user_runtime_status_service_contract", data)
    return FixedUserRuntimeStatusServiceContract(
        version=data["version"],
        architecture=data["architecture"],
        runtime_ordering=dict(data["runtime_ordering"]),
        shared_status=dict(data["shared_status"]),
        request=dict(data["request"]),
        response=dict(data["response"]),
        feature_mask_bits=tuple(dict(item) for item in data["feature_mask_bits"]),
        ring3_validation=dict(data["ring3_validation"]),
        ring0_revalidation=dict(data["ring0_revalidation"]),
        cleanup=dict(data["cleanup"]),
        marker_order=tuple(data["marker_order"]),
        failure_behavior=dict(data["failure_behavior"]),
        claim_boundary={
            name: tuple(values)
            for name, values in data["claim_boundary"].items()
        },
        non_goals=tuple(data["non_goals"]),
    )


def response_digest(qwords: list[int] | tuple[int, ...]) -> int:
    if not isinstance(qwords, (list, tuple)) or len(qwords) != 11:
        raise ValueError("response digest requires exactly eleven qwords")
    digest = 0
    for value in qwords:
        if not isinstance(value, int) or value < 0 or value > 0xFFFFFFFFFFFFFFFF:
            raise ValueError("response qwords must be unsigned 64-bit integers")
        digest ^= value
    return digest
