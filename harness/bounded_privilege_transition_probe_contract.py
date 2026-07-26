from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.abi_manifest import ROOT
from harness.validators_impl.schema import validate_named_document

CONTRACT_PATH = ROOT / "contracts" / "bounded_privilege_transition_probe_contract.v0.json"


@dataclass(frozen=True)
class BoundedPrivilegeTransitionProbeContract:
    version: int
    architecture: str
    source_files: dict[str, str]
    transition: dict[str, Any]
    selectors: dict[str, str]
    gdt: dict[str, Any]
    tss: dict[str, Any]
    idt: dict[str, Any]
    stacks: dict[str, dict[str, Any]]
    entry: dict[str, Any]
    probe: dict[str, Any]
    return_boundary: dict[str, Any]
    success_markers: tuple[str, ...]
    failure_statuses: dict[str, int]
    claim_boundary: dict[str, tuple[str, ...]]
    non_goals: tuple[str, ...]


def load_bounded_privilege_transition_probe_contract(
    path: Path = CONTRACT_PATH,
) -> BoundedPrivilegeTransitionProbeContract:
    data = json.loads(path.read_text())
    validate_named_document("bounded_privilege_transition_probe_contract", data)
    return _parse_contract(data)


def _parse_contract(data: dict[str, Any]) -> BoundedPrivilegeTransitionProbeContract:
    return BoundedPrivilegeTransitionProbeContract(
        version=data["version"],
        architecture=data["architecture"],
        source_files=dict(data["source_files"]),
        transition=dict(data["transition"]),
        selectors=dict(data["selectors"]),
        gdt=dict(data["gdt"]),
        tss=dict(data["tss"]),
        idt=dict(data["idt"]),
        stacks={name: dict(value) for name, value in data["stacks"].items()},
        entry=dict(data["entry"]),
        probe=dict(data["probe"]),
        return_boundary=dict(data["return_boundary"]),
        success_markers=tuple(data["success_markers"]),
        failure_statuses=dict(data["failure_statuses"]),
        claim_boundary={
            key: tuple(values)
            for key, values in data["claim_boundary"].items()
        },
        non_goals=tuple(data["non_goals"]),
    )
