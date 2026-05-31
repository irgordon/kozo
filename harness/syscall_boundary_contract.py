from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.abi_manifest import ROOT
from harness.validators_impl.schema import validate_named_document

CONTRACT_PATH = ROOT / "contracts" / "syscall_boundary_contract.v0.json"


@dataclass(frozen=True)
class BoundaryEntry:
    symbol: str
    assembly_path: str
    dispatcher_symbol: str


@dataclass(frozen=True)
class CallingConventionValue:
    source: str
    register: str
    value_type: str
    nullable: bool | None = None


@dataclass(frozen=True)
class CallingConvention:
    syscall_id: CallingConventionValue
    payload: CallingConventionValue
    return_value: CallingConventionValue


@dataclass(frozen=True)
class BoundarySentinels:
    sequence: str | int
    timestamp: str | int
    status_bits: str


@dataclass(frozen=True)
class InvalidBehavior:
    null_payload: str
    bad_sequence: str


@dataclass(frozen=True)
class SuccessBehavior:
    return_status: str
    mutates_payload: tuple[str, ...]


@dataclass(frozen=True)
class DebugHeartbeatBoundary:
    constant: str
    payload_layout: str
    request: BoundarySentinels
    response: BoundarySentinels
    invalid_behavior: InvalidBehavior
    success_behavior: SuccessBehavior


@dataclass(frozen=True)
class BoundaryOwnership:
    payload_owner: str
    kernel_may_mutate: tuple[str, ...]
    kernel_may_retain_payload: bool


@dataclass(frozen=True)
class ProofOwnershipEntry:
    validator_name: str
    fields: tuple[str, ...]


@dataclass(frozen=True)
class SyscallBoundaryContract:
    version: int
    architecture: str
    entry: BoundaryEntry
    calling_convention: CallingConvention
    debug_heartbeat: DebugHeartbeatBoundary
    ownership: BoundaryOwnership
    proof_ownership: tuple[ProofOwnershipEntry, ...]


def load_syscall_boundary_contract(path: Path = CONTRACT_PATH) -> SyscallBoundaryContract:
    data = load_contract_json(path)
    validate_contract_shape(data)
    return parse_syscall_boundary_contract(data)


def load_contract_json(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    return json.loads(path.read_text())


def validate_contract_shape(data: dict[str, Any]) -> None:
    validate_named_document("syscall_boundary_contract", data)


def parse_syscall_boundary_contract(data: dict[str, Any]) -> SyscallBoundaryContract:
    return SyscallBoundaryContract(
        version=data["version"],
        architecture=data["architecture"],
        entry=_boundary_entry(data),
        calling_convention=_calling_convention(data),
        debug_heartbeat=_debug_heartbeat(data),
        ownership=_ownership(data),
        proof_ownership=_proof_ownership(data),
    )


def contract_repo_path(contract_path: str) -> Path:
    path = Path(contract_path)
    if path.is_absolute():
        return path
    return ROOT / path


def _boundary_entry(data: dict[str, Any]) -> BoundaryEntry:
    entry = data["entry"]
    return BoundaryEntry(
        entry["symbol"],
        entry["assembly_path"],
        entry["dispatcher_symbol"],
    )


def _calling_convention(data: dict[str, Any]) -> CallingConvention:
    calling_convention = data["calling_convention"]
    return CallingConvention(
        syscall_id=_calling_value(calling_convention["syscall_id"]),
        payload=_calling_value(calling_convention["payload"]),
        return_value=_calling_value(calling_convention["return"]),
    )


def _calling_value(data: dict[str, Any]) -> CallingConventionValue:
    return CallingConventionValue(
        source=data.get("source", ""),
        register=data["register"],
        value_type=data["type"],
        nullable=data.get("nullable"),
    )


def _debug_heartbeat(data: dict[str, Any]) -> DebugHeartbeatBoundary:
    syscall = data["syscalls"]["debug_heartbeat"]
    return DebugHeartbeatBoundary(
        constant=syscall["constant"],
        payload_layout=syscall["payload_layout"],
        request=_sentinels(syscall["request"]),
        response=_sentinels(syscall["response"]),
        invalid_behavior=_invalid_behavior(syscall["invalid_behavior"]),
        success_behavior=_success_behavior(syscall["success_behavior"]),
    )


def _sentinels(data: dict[str, Any]) -> BoundarySentinels:
    return BoundarySentinels(
        sequence=data["sequence"],
        timestamp=data["timestamp"],
        status_bits=data["status_bits"],
    )


def _invalid_behavior(data: dict[str, Any]) -> InvalidBehavior:
    return InvalidBehavior(
        null_payload=data["null_payload"],
        bad_sequence=data["bad_sequence"],
    )


def _success_behavior(data: dict[str, Any]) -> SuccessBehavior:
    return SuccessBehavior(
        return_status=data["return_status"],
        mutates_payload=tuple(data["mutates_payload"]),
    )


def _ownership(data: dict[str, Any]) -> BoundaryOwnership:
    ownership = data["ownership"]
    return BoundaryOwnership(
        payload_owner=ownership["payload_owner"],
        kernel_may_mutate=tuple(ownership["kernel_may_mutate"]),
        kernel_may_retain_payload=ownership["kernel_may_retain_payload"],
    )


def _proof_ownership(data: dict[str, Any]) -> tuple[ProofOwnershipEntry, ...]:
    proof_ownership = data["proof_ownership"]
    return tuple(
        ProofOwnershipEntry(validator_name, tuple(fields))
        for validator_name, fields in proof_ownership.items()
        if isinstance(validator_name, str) and isinstance(fields, list)
    )
