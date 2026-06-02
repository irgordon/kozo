from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.abi_manifest import ROOT
from harness.validators_impl.schema import validate_named_document

CATALOG_PATH = ROOT / "contracts" / "syscall_catalog.v0.json"


@dataclass(frozen=True)
class PayloadBehavior:
    argument: str
    layout: str | None
    required: bool


@dataclass(frozen=True)
class MutationBehavior:
    mutates_payload: bool
    fields: tuple[str, ...]


@dataclass(frozen=True)
class CatalogSyscall:
    name: str
    constant: str
    numeric_id: int
    kind: str
    syscall_class: str
    payload_behavior: PayloadBehavior
    return_status: str
    mutation_behavior: MutationBehavior
    source_branch_selector: str
    proof_validators: tuple[str, ...]
    runtime_probe_present: bool


@dataclass(frozen=True)
class SyscallCatalog:
    version: int
    syscalls: tuple[CatalogSyscall, ...]


def load_syscall_catalog(path: Path = CATALOG_PATH) -> SyscallCatalog:
    data = load_catalog_json(path)
    validate_catalog_shape(data)
    return parse_syscall_catalog(data)


def load_catalog_json(path: Path = CATALOG_PATH) -> dict[str, Any]:
    return json.loads(path.read_text())


def validate_catalog_shape(data: dict[str, Any]) -> None:
    validate_named_document("syscall_catalog", data)


def parse_syscall_catalog(data: dict[str, Any]) -> SyscallCatalog:
    return SyscallCatalog(
        version=data["version"],
        syscalls=_syscalls(data),
    )


def _syscalls(data: dict[str, Any]) -> tuple[CatalogSyscall, ...]:
    return tuple(
        _catalog_syscall(name, syscall)
        for name, syscall in data["syscalls"].items()
        if isinstance(name, str) and isinstance(syscall, dict)
    )


def _catalog_syscall(name: str, data: dict[str, Any]) -> CatalogSyscall:
    return CatalogSyscall(
        name=data["name"],
        constant=data["constant"],
        numeric_id=data["numeric_id"],
        kind=data["kind"],
        syscall_class=data["class"],
        payload_behavior=_payload_behavior(data["payload_behavior"]),
        return_status=data["return_status"],
        mutation_behavior=_mutation_behavior(data["mutation_behavior"]),
        source_branch_selector=data["source_branch_selector"],
        proof_validators=tuple(data["proof_validators"]),
        runtime_probe_present=data["runtime_probe_present"],
    )


def _payload_behavior(data: dict[str, Any]) -> PayloadBehavior:
    return PayloadBehavior(
        argument=data["argument"],
        layout=data["layout"],
        required=data["required"],
    )


def _mutation_behavior(data: dict[str, Any]) -> MutationBehavior:
    return MutationBehavior(
        mutates_payload=data["mutates_payload"],
        fields=tuple(data["fields"]),
    )
