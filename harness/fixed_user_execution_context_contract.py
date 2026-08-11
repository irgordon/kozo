from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.abi_manifest import ROOT
from harness.validators_impl.schema import validate_named_document

CONTRACT_PATH = ROOT / "contracts" / "fixed_user_execution_context_contract.v0.json"


@dataclass(frozen=True)
class FixedUserExecutionContextContract:
    version: int
    architecture: str
    status: str
    authoritative_sources: dict[str, str]
    authority: dict[str, Any]
    context: dict[str, Any]
    lifecycle: dict[str, Any]
    clear_state: dict[str, Any]
    result: dict[str, Any]
    result_lifetime: dict[str, Any]
    fixed_bindings: dict[str, Any]
    transition_budget: dict[str, Any]
    runtime_progression: dict[str, Any]
    evidence_policy: dict[str, Any]
    claim_boundary: dict[str, tuple[str, ...]]
    non_goals: tuple[str, ...]


def load_fixed_user_execution_context_contract(
    path: Path = CONTRACT_PATH,
) -> FixedUserExecutionContextContract:
    data = json.loads(path.read_text())
    validate_named_document("fixed_user_execution_context_contract", data)
    return _parse_contract(data)


def transition_is_allowed(
    contract: FixedUserExecutionContextContract,
    from_state: str,
    to_state: str,
    *,
    failure: bool = False,
) -> bool:
    transition_key = "failure_cleanup_transitions" if failure else "successful_transitions"
    edge = {"from": from_state, "to": to_state}
    return edge in contract.lifecycle[transition_key]


def transition_phase_matches(
    contract: FixedUserExecutionContextContract,
    phase: str,
    observed_count: int,
) -> bool:
    valid_pairs = _transition_phase_pairs(contract)
    return (phase, observed_count) in valid_pairs


def result_field_names(
    contract: FixedUserExecutionContextContract,
) -> frozenset[str]:
    return frozenset(field["name"] for field in contract.result["fields"])


def _parse_contract(data: dict[str, Any]) -> FixedUserExecutionContextContract:
    return FixedUserExecutionContextContract(
        version=data["version"],
        architecture=data["architecture"],
        status=data["status"],
        authoritative_sources=dict(data["authoritative_sources"]),
        authority=dict(data["authority"]),
        context=dict(data["context"]),
        lifecycle=dict(data["lifecycle"]),
        clear_state=dict(data["clear_state"]),
        result=dict(data["result"]),
        result_lifetime=dict(data["result_lifetime"]),
        fixed_bindings=dict(data["fixed_bindings"]),
        transition_budget=dict(data["transition_budget"]),
        runtime_progression=dict(data["runtime_progression"]),
        evidence_policy=dict(data["evidence_policy"]),
        claim_boundary={key: tuple(values) for key, values in data["claim_boundary"].items()},
        non_goals=tuple(data["non_goals"]),
    )


def _transition_phase_pairs(
    contract: FixedUserExecutionContextContract,
) -> frozenset[tuple[str, int]]:
    pairs = {("REQUEST_PENDING", contract.transition_budget["initial_observed_count"])}
    for transition in contract.transition_budget["derivation"]:
        pairs.add((transition["phase_after_handler"], transition["count_after_entry"]))
    return frozenset(pairs)
