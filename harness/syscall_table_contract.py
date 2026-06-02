from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.abi_manifest import ROOT
from harness.validators_impl.schema import validate_named_document

CONTRACT_PATH = ROOT / "contracts" / "syscall_table_contract.v0.json"


@dataclass(frozen=True)
class TableDispatcher:
    symbol: str
    source_path: str
    syscall_id_type: str
    return_type: str


@dataclass(frozen=True)
class PayloadSyscall:
    name: str
    syscall_class: str
    constant: str
    payload_layout: str
    branch_selector: str
    boundary_contract: str


@dataclass(frozen=True)
class NoPayloadSyscall:
    name: str
    syscall_class: str
    constant: str
    branch_selector: str
    return_status: str
    must_not_mutate_payload: bool
    prohibited_fields: tuple[str, ...]


@dataclass(frozen=True)
class UnknownSyscallBehavior:
    return_status: str
    must_not_mutate_payload: bool


@dataclass(frozen=True)
class TableRelationships:
    abi_manifest: str
    syscall_boundary_contract: str


@dataclass(frozen=True)
class SyscallTableContract:
    version: int
    architecture: str
    dispatcher: TableDispatcher
    valid_syscalls: tuple[PayloadSyscall | NoPayloadSyscall, ...]
    unknown_syscall_behavior: UnknownSyscallBehavior
    relationships: TableRelationships


def load_syscall_table_contract(path: Path = CONTRACT_PATH) -> SyscallTableContract:
    data = load_contract_json(path)
    validate_contract_shape(data)
    return parse_syscall_table_contract(data)


def load_contract_json(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    return json.loads(path.read_text())


def validate_contract_shape(data: dict[str, Any]) -> None:
    validate_named_document("syscall_table_contract", data)


def parse_syscall_table_contract(data: dict[str, Any]) -> SyscallTableContract:
    return SyscallTableContract(
        version=data["version"],
        architecture=data["architecture"],
        dispatcher=_dispatcher(data),
        valid_syscalls=_valid_syscalls(data),
        unknown_syscall_behavior=_unknown_syscall_behavior(data),
        relationships=_relationships(data),
    )


def contract_repo_path(contract_path: str) -> Path:
    path = Path(contract_path)
    if path.is_absolute():
        return path
    return ROOT / path


def _dispatcher(data: dict[str, Any]) -> TableDispatcher:
    dispatcher = data["dispatcher"]
    return TableDispatcher(
        dispatcher["symbol"],
        dispatcher["source_path"],
        dispatcher["syscall_id_type"],
        dispatcher["return_type"],
    )


def _valid_syscalls(data: dict[str, Any]) -> tuple[PayloadSyscall | NoPayloadSyscall, ...]:
    syscalls = data["valid_syscalls"]
    return tuple(
        _valid_syscall(name, syscall)
        for name, syscall in syscalls.items()
        if isinstance(name, str) and isinstance(syscall, dict)
    )


def _valid_syscall(name: str, syscall: dict[str, Any]) -> PayloadSyscall | NoPayloadSyscall:
    if syscall["kind"] == "no_payload":
        return NoPayloadSyscall(
            name,
            syscall["class"],
            syscall["constant"],
            syscall["branch_selector"],
            syscall["return_status"],
            syscall["must_not_mutate_payload"],
            _prohibited_no_payload_fields(syscall),
        )
    return PayloadSyscall(
        name,
        syscall["class"],
        syscall["constant"],
        syscall["payload_layout"],
        syscall["branch_selector"],
        syscall["boundary_contract"],
    )


def _prohibited_no_payload_fields(syscall: dict[str, Any]) -> tuple[str, ...]:
    return tuple(field for field in ("payload_layout", "boundary_contract") if field in syscall)


def _unknown_syscall_behavior(data: dict[str, Any]) -> UnknownSyscallBehavior:
    behavior = data["unknown_syscall_behavior"]
    return UnknownSyscallBehavior(
        behavior["return_status"],
        behavior["must_not_mutate_payload"],
    )


def _relationships(data: dict[str, Any]) -> TableRelationships:
    relationships = data["relationships"]
    return TableRelationships(
        relationships["abi_manifest"],
        relationships["syscall_boundary_contract"],
    )
