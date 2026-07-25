from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.abi_manifest import ROOT
from harness.validators_impl.schema import validate_named_document

CONTRACT_PATH = ROOT / "contracts" / "cpu_extended_state_initialization_contract.v0.json"


@dataclass(frozen=True)
class CpuExtendedStateInitializationContract:
    version: int
    architecture: str
    execution_point: dict[str, Any]
    required_cpu_features: dict[str, Any]
    cr0_policy: dict[str, Any]
    cr4_policy: dict[str, Any]
    x87_initialization: dict[str, Any]
    sse_initialization: dict[str, Any]
    simd_probe: dict[str, Any]
    success_markers: tuple[str, ...]
    failure_statuses: dict[str, int]
    runtime_continuation: dict[str, Any]
    avx_prohibition: dict[str, Any]
    claim_boundary: dict[str, tuple[str, ...]]
    non_goals: tuple[str, ...]


def load_cpu_extended_state_initialization_contract(
    path: Path = CONTRACT_PATH,
) -> CpuExtendedStateInitializationContract:
    data = json.loads(path.read_text())
    validate_named_document("cpu_extended_state_initialization_contract", data)
    return _parse_contract(data)


def contract_repo_path(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


def _parse_contract(data: dict[str, Any]) -> CpuExtendedStateInitializationContract:
    return CpuExtendedStateInitializationContract(
        version=data["version"],
        architecture=data["architecture"],
        execution_point=dict(data["execution_point"]),
        required_cpu_features=dict(data["required_cpu_features"]),
        cr0_policy=dict(data["cr0_policy"]),
        cr4_policy=dict(data["cr4_policy"]),
        x87_initialization=dict(data["x87_initialization"]),
        sse_initialization=dict(data["sse_initialization"]),
        simd_probe=dict(data["simd_probe"]),
        success_markers=tuple(data["success_markers"]),
        failure_statuses=dict(data["failure_statuses"]),
        runtime_continuation=dict(data["runtime_continuation"]),
        avx_prohibition=dict(data["avx_prohibition"]),
        claim_boundary={
            key: tuple(values)
            for key, values in data["claim_boundary"].items()
        },
        non_goals=tuple(data["non_goals"]),
    )
