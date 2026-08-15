from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.abi_manifest import ROOT
from harness.validators_impl.schema import validate_named_document

CONTRACT_PATH = ROOT / "contracts" / "bounded_repeated_user_session_contract.v0.json"


@dataclass(frozen=True)
class BoundedRepeatedUserSessionContract:
    version: int
    architecture: str
    status: str
    existing_context_contract: str
    authority: dict[str, Any]
    session: dict[str, Any]
    identity: dict[str, Any]
    coordinator: dict[str, Any]
    reset_boundary: dict[str, Any]
    marker_policy: dict[str, Any]
    failure_codes: dict[str, int]
    runtime_continuation: dict[str, Any]
    claim_boundary: dict[str, tuple[str, ...]]
    non_goals: tuple[str, ...]


def load_bounded_repeated_user_session_contract(
    path: Path = CONTRACT_PATH,
) -> BoundedRepeatedUserSessionContract:
    data = json.loads(path.read_text())
    validate_named_document("bounded_repeated_user_session_contract", data)
    return _parse_contract(data)


def coordinator_field_names(
    contract: BoundedRepeatedUserSessionContract,
) -> tuple[str, ...]:
    return tuple(field["name"] for field in contract.coordinator["fields"])


def session_identities(
    contract: BoundedRepeatedUserSessionContract,
) -> tuple[int, int]:
    return int(contract.identity["session_1"], 16), int(contract.identity["session_2"], 16)


def _parse_contract(data: dict[str, Any]) -> BoundedRepeatedUserSessionContract:
    return BoundedRepeatedUserSessionContract(
        version=data["version"],
        architecture=data["architecture"],
        status=data["status"],
        existing_context_contract=data["existing_context_contract"],
        authority=dict(data["authority"]),
        session=dict(data["session"]),
        identity=dict(data["identity"]),
        coordinator=dict(data["coordinator"]),
        reset_boundary=dict(data["reset_boundary"]),
        marker_policy=dict(data["marker_policy"]),
        failure_codes=dict(data["failure_codes"]),
        runtime_continuation=dict(data["runtime_continuation"]),
        claim_boundary={key: tuple(values) for key, values in data["claim_boundary"].items()},
        non_goals=tuple(data["non_goals"]),
    )
